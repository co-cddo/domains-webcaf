from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery
from django.forms import ModelForm
from django.urls import reverse
from django.views.generic import FormView

from webcaf.webcaf.models import Assessment, System, UserProfile


class EditAssessmentView(LoginRequiredMixin, FormView):
    login_url = "/oidc/authenticate/"  #
    template_name = "assessment/draft-assessment.html"

    def get_context_data(self, **kwargs):
        assessment_id = self.kwargs.get("assessment_id")
        current_profile = UserProfile.objects.get(id=self.request.session["current_profile_id"])
        current_organisation = current_profile.organisation
        assessment = Assessment.objects.get(
            id=assessment_id, status="draft", assessment_period="25/26", system__organisation_id=current_organisation.id
        )
        if "draft_assessment" not in self.request.session:
            # Set a draft assessment if it is not already in the session
            self.request.session["draft_assessment"] = {}
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["assessment_id"] = assessment.id
        draft_assessment["system"] = assessment.system.id
        draft_assessment["caf_profile"] = assessment.caf_profile
        data = {
            "draft_assessment": draft_assessment,
            "breadcrumbs": [
                {"url": reverse("my-account"), "text": "My account"},
            ]
            + self.breadcrumbs(assessment.id),
        }
        data["systems"] = (
            System.objects.filter(organisation=current_organisation)
            .exclude(
                # Exclude any systems that already have draft assessments assigned
                id__in=[Subquery(Assessment.objects.filter(status="draft").values("system_id"))]
            )
            .union(System.objects.filter(id=assessment.system_id))
        )

        # Need to persist the session as sometimes it does not save automatically
        self.request.session.save()
        return data

    def get_form_kwargs(self):
        """
        Add the form instance to the kwargs.
        :return:
        """
        kwargs = super().get_form_kwargs()
        assessment_to_modify = Assessment.objects.get(id=self.kwargs.get("assessment_id"), status="draft")
        curren_organisation = UserProfile.objects.get(id=self.request.session["current_profile_id"]).organisation
        if assessment_to_modify.system.id not in curren_organisation.systems.values_list("id", flat=True):
            raise Exception("You are not allowed to edit this assessment")
        kwargs["instance"] = assessment_to_modify
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("edit-draft-assessment", kwargs={"assessment_id": self.kwargs["assessment_id"]})

    def breadcrumbs(self, assessment_id: int):
        return [{"url": "#", "text": "Edit draft assessment"}]


class AssessmentProfileForm(ModelForm):
    class Meta:
        model = Assessment
        fields = ["caf_profile"]


class AssessmentSystemForm(ModelForm):
    class Meta:
        model = Assessment
        fields = ["system"]


class EditAssessmentProfileView(EditAssessmentView):
    template_name = "assessment/caf-profile.html"
    form_class = AssessmentProfileForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_id": assessment_id,
                    },
                ),
                "text": "Edit draft assessment",
            },
            {"url": "#", "text": "Choose Profile"},
        ]


class EditAssessmentSystemView(EditAssessmentView):
    template_name = "assessment/system-details.html"
    form_class = AssessmentSystemForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_id": assessment_id,
                    },
                ),
                "text": "Edit draft assessment",
            },
            {"url": "#", "text": "Choose System"},
        ]


class CreateAssessmentView(LoginRequiredMixin, FormView):
    """ """

    login_url = "/oidc/authenticate/"  # OIDC login route
    template_name = "assessment/draft-assessment.html"

    def get_context_data(self, **kwargs):
        data = {}
        profile_id = self.request.session["current_profile_id"]
        profile = UserProfile.objects.get(user=self.request.user, id=profile_id)
        data["breadcrumbs"] = [
            {"url": reverse("my-account"), "text": "My account"},
        ] + self.breadcrumbs()
        data["profile"] = profile
        data["draft_assessment"] = self.request.session.get("draft_assessment", {})
        # Show only the systems needing new drafts
        data["systems"] = System.objects.filter(organisation=profile.organisation).exclude(
            id__in=[Subquery(Assessment.objects.filter(status="draft").values("system_id"))]
        )
        return data

    def get_success_url(self):
        return reverse("create-draft-assessment")

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        current_organisation = UserProfile.objects.get(id=self.request.session["current_profile_id"]).organisation
        if "system" in draft_assessment and "caf_profile" in draft_assessment:
            system = System.objects.get(id=draft_assessment["system"], organisation=current_organisation)
            assessment, _ = Assessment.objects.get_or_create(
                status="draft",
                assessment_period="25/26",
                system=system,
                defaults={
                    "created_by": self.request.user,
                    "caf_profile": draft_assessment["caf_profile"],
                    "last_updated_by": self.request.user,
                },
            )
            draft_assessment["assessment_id"] = assessment.id
            assessment.last_updated_by = self.request.user
            assessment.save()
            # Forward to editing the draft now.
            reverse("edit-draft-assessment", kwargs={"assessment_id": assessment.id})
        return super().form_valid(form)

    def breadcrumbs(self):
        return [{"url": "#", "text": "Start a draft assessment"}]


class CreateAssessmentProfileView(CreateAssessmentView):
    form_class = AssessmentProfileForm
    template_name = "assessment/caf-profile.html"

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["caf_profile"] = form.cleaned_data["caf_profile"]
        self.request.session.save()
        return super().form_valid(form)

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose a CAF profile"},
        ]


class CreateAssessmentSystemView(CreateAssessmentView):
    form_class = AssessmentSystemForm
    template_name = "assessment/system-details.html"

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["system"] = form.cleaned_data["system"].id
        self.request.session.save()
        return super().form_valid(form)

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose System"},
        ]
