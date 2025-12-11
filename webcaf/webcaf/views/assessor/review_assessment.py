import logging
from abc import ABC, abstractmethod
from typing import final

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.transaction import atomic
from django.forms import (
    CharField,
    ChoiceField,
    ModelForm,
    RadioSelect,
    Textarea,
    formset_factory,
)
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import DetailView, UpdateView

from webcaf.webcaf.forms.factory import WordCountValidator
from webcaf.webcaf.forms.review import (
    CommentsForm,
    PreviewForm,
    RecommendationForm,
    ReviewPeriodForm,
)
from webcaf.webcaf.models import Review
from webcaf.webcaf.utils.session import SessionUtil
from webcaf.webcaf.views.assessor.util import BaseReviewMixin


class ObjectiveSummaryView(BaseReviewMixin, DetailView):
    """
    Represents the view for displaying and managing the objective summary within a review
    assessment process.

    This class is a concrete implementation of reviewed-based views which renders the
    objective summary for a specific objective code and allows navigation between objectives
    within that review. It integrates template rendering and context enrichment for
    specific use cases in the review process.

    :ivar template_name: Path to the template file used to render the objective summary page.
    :type template_name: str
    :ivar model: The model class associated with this view.
    :type model: Review
    """

    template_name = "review/assessment/objective-summary.html"
    model = Review

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        objective_code_ = self.kwargs["objective_code"]
        data["objective"] = self.object.assessment.get_caf_objective_by_id(objective_code_)
        data["objective_code"] = objective_code_
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Edit draft review",
            },
            {
                "url": None,
                "text": f"Objective {objective_code_} - {data['objective']['title']} review and confirmation",
            },
        ]
        return data

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "yes":
            return redirect(
                reverse(
                    "objective-summary",
                    kwargs={"pk": self.kwargs["pk"], "objective_code": request.POST.get("next_objective")},
                )
            )
        return redirect(reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}))


class OutcomeView(BaseReviewMixin, UpdateView):
    """
    Handles the view logic for updating the assessment outcome status in a review.
    This class enables the user to view and modify the outcome status of a specific
    objective within a review process. It generates dynamic forms tailored to the
    assessment data and provides breadcrumb navigation for ease of use.

    :ivar template_name: The path to the HTML template used for rendering the view.
    :type template_name: str
    """

    template_name = "review/assessment/outcome-status.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        answered_statements = self.object.assessment.get_section_by_outcome_id(self.kwargs["outcome_code"])
        data["answered_statements"] = answered_statements
        data["outcome"] = self.object.assessment.get_caf_outcome_by_id(
            self.kwargs["objective_code"], self.kwargs["outcome_code"]
        )
        objective = self.object.assessment.get_router().get_section(self.kwargs["objective_code"])
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Edit draft review",
            },
            {
                "url": reverse(
                    "objective-summary",
                    kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]},
                ),
                "text": f"{objective['code']} - {objective['title']}",
            },
            {
                "url": None,
                "text": f"{data['outcome']['code']} - {data['outcome']['title']}",
            },
        ]
        return data

    def get_success_url(self):
        return reverse(
            "objective-summary", kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]}
        )

    def form_valid(self, form: ModelForm):
        review: Review = form.instance
        review.set_outcome_review(self.kwargs["objective_code"], self.kwargs["outcome_code"], form.cleaned_data)
        return super().form_valid(form)

    def get_form_class(self):
        """
        Generates and returns a form class dynamically based on the provided review data,
        objective code, and outcome code. Forms are tailored to the specific assessment
        requirements and are intended to facilitate interactive work with dynamic
        datasets.

        :return: A dynamically generated subclass of `ModelForm` with fields specific
            to the review's outcomes and objectives.
        """

        def generate_fields_map(review, objective_code, outcome_code):
            principle, _ = outcome_code.split(".")
            outcome = review.assessment.get_caf_outcome_by_id(objective_code, outcome_code)
            answered_statements = review.assessment.get_section_by_outcome_id(outcome_code)
            fields = {}
            for indicator, statements in outcome["indicators"].items():
                idx = 1
                for key, statement in statements.items():
                    indicator_id = f"{indicator}_{key}"
                    indicator_comment = f"{indicator_id}_comment"

                    fields[indicator_id] = ChoiceField(
                        label=f"{indicator} statement {idx}",
                        help_text=statement["description"],
                        choices=[("yes", "Yes"), ("no", "No")],
                        required=True,
                        widget=RadioSelect(),
                    )
                    idx += 1
                    fields[indicator_comment] = CharField(
                        label="Alternative controls",
                        help_text=answered_statements["indicators"].get(indicator_comment, ""),
                        validators=([WordCountValidator(750)]),
                        widget=Textarea(attrs={"rows": 5, "max_words": 750}),
                        # You only require the inout if they have entered any text already
                        required=answered_statements["indicators"].get(indicator_comment, "") != "",
                    )

            fields["review_decision"] = ChoiceField(
                label="review decision",
                help_text="Overall independent review outcome",
                choices=[
                    ("achieved", "Achieved"),
                    ("partially-achieved", "Partially achieved"),
                    ("not-achieved", "Not achieved"),
                ]
                # Check if the outcome is partially achieved, if so, only allow achieved and not achieved
                if outcome["indicators"].get("partially-achieved")
                else [("achieved", "Achieved"), ("not-achieved", "Not achieved")],
            )
            fields["review_comment"] = CharField(
                help_text="Comment on the contributing outcome",
                label="review comment",
                validators=([WordCountValidator(1500)]),
                widget=Textarea(
                    attrs={"rows": 10, "max_words": 1500},
                ),
            )
            return fields

        def generate_form_class(*, review, objective_code, outcome_code, **kwargs):
            class ReviewOutcomeForm(ModelForm):
                class Meta:
                    model = Review
                    fields = []

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.fields.update(generate_fields_map(review, objective_code, outcome_code))
                    initial_values = review.get_outcome_review(objective_code, outcome_code)
                    for key, value in initial_values.items():
                        self.fields[key].initial = value

            return ReviewOutcomeForm

        return generate_form_class(review=self.object, **self.kwargs)


class AddRecommendationView(BaseReviewMixin, UpdateView, ABC):
    """
    Handles the view for adding recommendations to a review.

    This class is primarily used for managing the interface for adding and managing
    recommendations within a review context. It provides mechanisms to handle forms,
    context data, and redirection based on form validation or user input. It is an
    abstract view requiring concrete implementation for specific methods to function
    properly.

    The class supports preview and confirmation flows for user recommendations
    with different output based on the state of the submitted data. It also manages
    breadcrumbs for navigation and overrides specific behaviors to satisfy the
    functional requirements of the form management process.

    *NOTE*: Any class extending this must explicitly call self.object.save() after the
    comments have been processed in the save_recommendations method.

    :ivar template_name: Path to the template used for this view.
    :type template_name: str
    :ivar form_class: The Django formset class used for handling recommendations.
    :type form_class: type
    :ivar model: The model associated with the recommendations view.
    :type model: type
    """

    template_name = "review/assessment/recommendation.html"
    model = Review

    def get_form_class(self):
        """
        Formset for collecting recommendations.
        """
        return formset_factory(
            RecommendationForm,
            # Show the extra form initially, otherwise let the user decide if they want to add more recommendations
            extra=1 if not self.get_initial() else 0,
            can_delete=True,
        )

    def get_success_url(self):
        return reverse(
            "objective-summary", kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]}
        )

    def get_initial(self):
        return self.get_comments()

    @abstractmethod
    def get_comments(self):
        pass

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Formset does not accept instance as a kwarg
        kwargs.pop("instance", None)
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["preview_form"] = PreviewForm(initial={"finished": False})
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Edit draft review",
            },
        ]
        return data

    def form_valid(self, comment_formset):
        """
        Processes and validates comment forms, handles preview and confirmation statuses, and determines the
        appropriate response or redirection based on user actions.

        :param comment_formset: A formset containing the forms representing user comments.
        :type comment_formset: BaseFormSet
        :return: A TemplateResponse object with context data or a redirect to the success URL based on the
                 user's form submission.
        :rtype: Union[TemplateResponse, HttpResponseRedirect]
        """
        preview_form = PreviewForm(self.request.POST)
        preview_form.full_clean()
        if preview_form.cleaned_data["preview_status"] == "confirm":
            comments = [
                {
                    "text": f.cleaned_data["text"],
                    "title": f.cleaned_data["title"],
                }
                for f in comment_formset.forms
                if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
            ]
            self.save_recommendations(comments)
            return redirect(self.get_success_url())
        elif preview_form.cleaned_data["preview_status"] == "preview":
            # Data validation errors are handled by the formset, so we only need to check for empty forms

            for form in comment_formset.forms:
                if not form.cleaned_data:
                    form.add_error("text", ValidationError("This field is required.", code="required"))
                    form.add_error("title", ValidationError("This field is required.", code="required"))
                elif not form.cleaned_data.get("DELETE", False):
                    if not form.cleaned_data["text"]:
                        form.add_error("text", ValidationError("This field is required.", code="required"))
                    if not form.cleaned_data["title"]:
                        form.add_error("title", ValidationError("This field is required.", code="required"))

            errors_added = any(form.errors for form in comment_formset.forms)
            if errors_added:
                return TemplateResponse(
                    request=self.request,
                    template=self.template_name,
                    context=self.get_context_data() | {"form": comment_formset},
                )
            # If no validation errors were found, we can proceed with the preview
            return TemplateResponse(
                request=self.request,
                template="review/assessment/recommendation-confirmation.html",
                # Override the preview form so the next submission confirms the preview
                context=self.get_context_data()
                | {"preview_form": PreviewForm(initial={"preview_status": "confirm"}), "form": comment_formset},
            )

        # This is the change path
        return TemplateResponse(
            request=self.request,
            template="review/assessment/recommendation.html",
            # Override the preview form so the next submission confirms the preview
            context=self.get_context_data()
            | {"preview_form": PreviewForm(initial={"preview_status": "preview"}), "form": comment_formset},
        )

    @abstractmethod
    def save_recommendations(self, comments):
        pass


class AddOutcomeRecommendationView(AddRecommendationView):
    """
    Handles the addition of outcome-specific recommendations for an assurance review.

    This class facilitates the retrieval, contextualization, and saving of recommendations specific to
    an outcome under a broader objective. It works within the context of an assurance review process,
    allowing users to summarize direct improvement areas identified for a given outcome.

    :ivar object: Instance of the model that provides access to methods for managing outcome
        recommendations and associated data.
    :type object: Any
    :ivar kwargs: Dictionary of keyword arguments passed during view initialization, containing
        details like `objective_code` and `outcome_code` relevant to recommendations.
    :type kwargs: dict
    """

    def get_comments(self):
        existing_comments = self.object.get_outcome_recommendations(
            self.kwargs["objective_code"], self.kwargs["outcome_code"]
        )
        return existing_comments

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        outcome = self.object.assessment.get_caf_outcome_by_id(
            self.kwargs["objective_code"], self.kwargs["outcome_code"]
        )
        data["title"] = f"{outcome['code']} - {outcome['title']}"
        data["recommendation_type"] = "outcome"
        data[
            "description"
        ] = """Use this section to add recommendations for this outcome. Each recommendation should
        summarise a direct improvement area identified during the assurance review."""
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": reverse(
                    "objective-summary",
                    kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]},
                ),
                "text": f"Objective {self.kwargs['objective_code']} - {outcome['title']}",
            },
            {
                "url": None,
                "text": f"Add a recommendation for {outcome['code']} - {outcome['title']}",
            },
        ]
        return data

    def save_recommendations(self, comments):
        self.object.set_outcome_recommendations(self.kwargs["objective_code"], self.kwargs["outcome_code"], comments)
        self.object.last_updated_by = self.request.user
        self.object.save()


class BaseAddCommentsView(BaseReviewMixin, UpdateView, ABC):
    """
    Base view for adding comments in the review editing process.

    This abstract class serves as a base for managing the addition of comments
    to review instances. It provides methods and functionality for handling
    comments through forms, ensuring proper setup and processing, and managing
    breadcrumbs for contextual navigation.

    :ivar form_class: The form class utilized by the view.
    :type form_class: type[ModelForm]
    """

    form_class: type[ModelForm] = CommentsForm

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Edit draft review",
            },
        ]
        return data

    @abstractmethod
    def set_comments(self, comments, instance: Review):
        """
        Abstract method for setting comments to a specified instance.

        This method should be implemented by subclasses to provide functionality
        for assigning a comment to a specific review instance.

        *NOTE*: Do not call form.save() in this method. As it is called by the parent class.

        :param comments: New comment to be set.
        :type comments: Str
        :param instance: Review instance to which the comment will be assigned.
        :type instance: Review
        :return: None
        """
        pass

    @abstractmethod
    def get_comments(self):
        """
        An abstract method that enforces the implementation of acquiring comments
        from a subclass. This method serves as a blueprint to be overridden by
        any subclass implementation, ensuring a uniform interface for managing
        or processing comments.

        :raises NotImplementedError: Raised if the method is not implemented
            in a subclass.
        :return: None
        """
        pass

    @atomic
    @final
    def form_valid(self, form):
        """
        Validates the submitted form and performs post-validation actions.

        The method processes the validated form data, including setting comments
        and assigning the user who updated the instance. It then proceeds with
        the default form validation behavior.

        :param form: The validated form instance containing user input
            and associated model instance.
        :type form: Form
        :return: The HTTP response returned after successfully processing
            the valid form.
        :rtype: HttpResponse
        """
        self.set_comments(form.cleaned_data["text"], form.instance)
        form.instance.last_updated_by = self.request.user
        return super().form_valid(form)

    def get_initial(self):
        """
        Retrieves the initial state with pre-defined comments.

        :return: A dictionary containing the initial predefined text.
        :rtype: dict
        """
        return {"text": self.get_comments()}

    @abstractmethod
    def get_comment_category(self):
        """
        Defines an abstract method to get the comment category. Subclasses must
        override this method to provide the logic for determining the category
        of a specific comment.

        :return: Returns the category of the comment as implemented in the
                 subclass.
        :rtype: str
        """
        pass


class AddObjectiveCommentsView(BaseAddCommentsView, ABC):
    """
    Provides functionality for adding and managing comments for specific objectives
    within an assessment or review. This class abstracts common behaviors for
    adding, retrieving, and managing comments related to objectives, enforces the
    implementation of specific methods through abstract definitions, and configures
    context data with breadcrumbs to improve navigation.

    This class can be extended to customize functionality specific to different
    subclasses that deal with objective-related comments.

    :ivar object: The object being assessed that holds the objective-level
                  information and comments.
    :type object: Any

    :ivar request: The current HTTP request context used to fetch user information
                   for actions like tracking updates.
    :type request: HttpRequest
    """

    def get_success_url(self):
        return reverse(
            "objective-summary", kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]}
        )

    def set_comments(self, comments: str, instance: Review):
        """
        Sets the objective comments for a specific review instance and updates the user
        who last modified the review instance.

        :param comments: The comments to be set for the review instance.
        :type comments: str
        :param instance: The review instance on which the comments are to be set.
        :type instance: Review
        :return: None
        """
        instance.set_objective_comments(self.kwargs["objective_code"], self.get_comment_category(), comments)
        if self.request.user.is_authenticated:
            instance.last_updated_by = self.request.user
        else:
            raise PermissionDenied("You must be logged in to add comments.")

    def get_comments(self) -> str:
        """
        Retrieves comments associated with a specific objective.

        This method uses the `objective_code` provided in the `kwargs` dictionary and
        a comment category determined by `get_comment_category()` to fetch comments
        for the related objective.

        :raises KeyError: If "objective_code" key is missing in `kwargs`.

        :return: The retrieved comments for the given objective.
        :rtype: str
        """
        return self.object.get_objective_comments(self.kwargs["objective_code"], self.get_comment_category())

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        objective = self.object.assessment.get_caf_objective_by_id(self.kwargs["objective_code"])
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": reverse(
                    "objective-summary",
                    kwargs={"pk": self.kwargs["pk"], "objective_code": self.kwargs["objective_code"]},
                ),
                "text": f"Objective {self.kwargs['objective_code']} - {objective['title']}",
            },
        ]
        return data


class AddObjectiveAreasOfImprovementView(AddObjectiveCommentsView):
    """
    Handles the addition of comments related to objective areas of improvement.

    This class is used to manage the comments that fall under the category of
    "objective areas of improvement" in a review or assessment context. It inherits
    from `AddObjectiveCommentsView` and modifies the context data and
    comment category to match the specific requirements for handling areas
    of improvement.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    """

    template_name = "review/assessment/objective-areas-of-improvement.html"

    def get_comment_category(self):
        return "objective-areas-of-improvement"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "Areas for improvement",
            }
        ]
        return data


class AddObjectiveAreasOfGoodPracticeView(AddObjectiveCommentsView):
    """
    Represents a detailed view for adding comments related to objective areas of good practice.

    This class extends the functionality to manage the process of adding comments
    specifically for the category "objective areas of good practice" and also handles
    templatized rendering. The view provides context for breadcrumbs used in the
    template.

    :ivar template_name: The path to the template used for rendering the view.
    :type template_name: str
    """

    template_name = "review/assessment/objective-areas-of-good-practice.html"

    def get_comment_category(self):
        return "objective-areas-of-good-practice"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "Areas of good practice",
            }
        ]
        return data


class AddObjectiveRecommendationView(AddObjectiveCommentsView):
    template_name = "review/assessment/objective-overview.html"

    def get_comment_category(self):
        return "objective-overview"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "Objective overview",
            }
        ]
        return data


class AddReviewCommentsView(BaseAddCommentsView, ABC):
    """
    Handles the addition of comments to a review instance.

    This class provides methods to set and retrieve comments associated with
    a review instance. Additionally, it determines the redirect URL upon a
    successful operation.

    :ivar object: The review object tied to this view.
    :type object: Review
    """

    def set_comments(self, comments: str, instance: Review):
        """
        Sets comments for the specified instance by associating them with a specific category.

        The function uses the provided comments and links them to a category obtained from
        the instance method ``get_comment_category``. This ensures that additional detail
        is updated within the specified instance.

        :param comments: The comments to be added for the instance.
        :param instance: The instance of the Review where the comments will be set.
        :return: None
        """
        instance.set_additional_detail(self.get_comment_category(), comments)

    def get_comments(self) -> str:
        """
        Provides functionality to retrieve specific comments associated with a given
        object and category. This method dynamically fetches and constructs comment
        details based on the associated comment category.

        :return: The retrieved comments as a string.
        :rtype: str
        """
        return self.object.get_additional_detail(self.get_comment_category())

    def get_success_url(self):
        return reverse(
            "edit-review",
            kwargs={
                "pk": self.kwargs["pk"],
            },
        )


class AddQualityOfEvidenceView(AddReviewCommentsView):
    """
    Represents a view for adding quality of evidence during an assessment review.

    This class is responsible for rendering the quality of evidence page as part of
    the assessment review process. It inherits common behaviors and attributes
    from the `AddReviewCommentsView` base class and extends it to handle
    quality of evidence-specific functionalities.

    :ivar template_name: Path to the HTML template used for the quality-of-evidence
        review page.
    :type template_name: str
    """

    template_name = "review/assessment/quality-of-evidence.html"

    def get_comment_category(self):
        return "quality_of_evidence"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "Quality of evidence",
            }
        ]
        return data


class AddReviewMethodView(AddReviewCommentsView):
    """
    Handles the display and interaction for adding review methods in the review
    assessment feature.

    This class is responsible for rendering the review method page and providing
    the necessary context and data required for its functionality.

    :ivar template_name: The path to the template used for rendering the review
        method page.
    :type template_name: str
    """

    template_name = "review/assessment/review-method.html"

    def get_comment_category(self):
        return "review_method"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "Review method",
            }
        ]
        return data


class AddIarPeriodView(AddReviewCommentsView):
    """
    Handles the addition of review comments for an IAR (Independent Assessment Report) period.

    This class is responsible for rendering the IAR period review comment page and processing
    the related form data. It extends functionality from AddReviewCommentsView to support
    specific customization required for IAR period reviews.

    :ivar template_name: Path to the template used for rendering the IAR period review page.
    :type template_name: str
    :ivar form_class: Form class used to handle input data for the review period.
    :type form_class: type
    """

    template_name = "review/assessment/iar-period.html"
    form_class = ReviewPeriodForm

    def get_comment_category(self):
        return "iar_period"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = data["breadcrumbs"] + [
            {
                "url": None,
                "text": "IAR period",
            }
        ]
        return data


class CreateReportView(BaseReviewMixin, UpdateView):
    """
    Handles the creation of a report at the final stage of the review assessment process.

    This view extends both `BaseReviewMixin` and `UpdateView` to provide functionality for
    updating a specific review instance while enabling the generation of a report. The class
    is primarily used for interacting with the "create report" feature within the review
    assessment interface. The form is validated based on specific conditions, and successful
    completion redirects users to confirmation or edit pages.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    :ivar model: The model class used by the view to manipulate data.
    :type model: type[Review]
    :ivar fields: Fields of the `Review` model to be included in the form.
    :type fields: list
    """

    template_name = "review/assessment/create-report.html"
    model = Review
    fields = []
    logger: logging.Logger = logging.getLogger("CreateReportView")

    def get_success_url(self):
        return reverse("show-report-confirmation", kwargs={"pk": self.kwargs["pk"]})

    def form_valid(self, form: ModelForm):
        """
        Handles the validation of a submitted form and performs specific actions
        based on the form data and user input.

        If the form is submitted with an `action` value of "create_report" and the
        instance's `status` is "in_progress", the method marks the review as complete,
        updates the `last_updated_by` field with the current user, and saves the
        instance. It then redirects the user to the success URL. In other cases, it
        redirects the user to the "edit-review" page with the appropriate primary key.

        :param form: The form object being validated.
        :type form: ModelForm
        :return: A redirect response either to the success URL or the "edit-review"
                 page based on the form validation logic.
        :rtype: HttpResponseRedirect
        """
        if self.request.POST.get("action") == "create_report":
            try:
                form.instance.mark_review_complete(SessionUtil.get_current_user_profile(self.request))
                form.instance.last_updated_by = self.request.user
                self.logger.info(f"Review {form.instance.id} marked as complete by user {self.request.user.id}")
                return super().form_valid(form)
            except ValidationError as ex:
                self.logger.warning(f"Error marking review {form.instance.id} as complete: {ex}")
                form.add_error(None, "Could not generate the report : " + ex.message)
                return self.form_invalid(form)

        return redirect(reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}))


class ShowReportConfirmation(BaseReviewMixin, DetailView):
    """
    Manages the display of the Review confirmation view.

    This class is responsible for rendering a detailed confirmation view for a
    specific Review instance. It utilizes a template to present the review details
    and ensures the proper context is provided for confirmation. The class inherits
    from `BaseReviewMixin` and `DetailView` to facilitate review-specific logic and
    detailed view rendering, respectively.

    :ivar template_name: The path to the template used for rendering the
        confirmation view.
    :type template_name: str
    :ivar model: The model associated with this view, representing the Review
        object.
    :type model: type
    :ivar fields: A list of model fields relevant for this view. This can be
        customized further as required.
    :type fields: list[str]
    """

    template_name = "review/assessment/show-confirmation.html"
    model = Review
    fields: list[str] = []
