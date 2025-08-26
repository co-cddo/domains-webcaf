import logging
from abc import ABC, abstractmethod
from typing import Any, Generator

import yaml
from django.urls import NoReverseMatch, path, reverse_lazy
from django.utils.text import slugify
from django.views.generic import FormView

from webcaf import urls
from webcaf.webcaf.views.view_factory import create_form_view

from .caf32_field_providers import (
    FieldProvider,
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)
from .form_factory import create_form

FrameworkValue = str | dict | int | None

FormViewClass = type[FormView]

CAF32Element = dict[str, Any]


# This is really just a placeholder for now. Until we add in new frameworks we can't know what makes sense
# to be included in a common interface.
class FrameworkRouter(ABC):
    """
    This class is the primary interface between the YAML CAF and the rest of the application. It's declared
    as a class partly in case we later want to use an ABC to declare a common interface for different types
    of router.

    It reads the YAML and from there can produce a route based on all the outcomes, only those associated with
    organisations or only those associated with systems. This is done by creating a class for each view and form
    element in the CAF then updating Django's url patterns with paths to the views. Each form is provided the
    success_url for the next page in the route.
    """

    all_url_names: list[str] = []
    parent_map: dict[str, Any] = {}

    @abstractmethod
    def execute(self) -> None:
        pass


class CAF32Router(FrameworkRouter):
    logger = logging.getLogger("FrameworkRouter")

    @staticmethod
    def _build_breadcrumbs(element: CAF32Element) -> list[dict[str, str]]:
        breadcrumbs: list = []
        current_element = element
        while current_element:
            try:
                url = reverse_lazy(current_element["short_name"])
            except NoReverseMatch:
                url = "#"
            breadcrumbs.insert(0, {"url": url, "text": current_element["title"]})
            current_element = current_element.get("parent")  # type: ignore
        if current_element is None:
            breadcrumbs.insert(0, {"url": "#", "text": "Root"})
        return breadcrumbs

    def __init__(self, framework_path, exit_url: str = "index") -> None:
        self.file_path = framework_path
        self.exit_url = exit_url
        self.framework: CAF32Element = {}
        self.elements: list[CAF32Element] = []
        self._read()

    def _get_success_url(self, element: CAF32Element) -> str:
        """
        Determine the success URL for a form.
        If there's a next URL in the sequence, use that, otherwise use the exit URL.
        """
        current_index = self.elements.index(element)
        if current_index + 1 < len(self.elements):
            return self.elements[current_index + 1]["short_name"]
        else:
            return self.exit_url

    def _create_view_and_url(self, element: CAF32Element, form_class=None) -> None:
        """
        Takes an element from the CAF, the url for the next page in the route and a form class
        to create a view class and add a path for the view to Django's urlpatterns.
        """
        url_path = slugify(f"{element['code']}-{element['title']}")
        extra_context = {
            "title": element.get("title"),
            "description": element.get("description"),
            "breadcrumbs": CAF32Router._build_breadcrumbs(element),
        }
        if element["type"] in ["objective", "principle"]:
            template_name = "title.html"
            class_prefix = f"{element['type'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                class_prefix=class_prefix,
                class_id=element["code"],
                extra_context=extra_context,
            )
            url_path_to_add = path(f"{url_path}/", element["view_class"].as_view(), name=element["short_name"])
            urls.urlpatterns.append(url_path_to_add)
        else:
            template_name = f"{element['stage']}.html"
            class_prefix = f"Outcome{element['stage'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                form_class=form_class,
                class_prefix=class_prefix,
                class_id=element["code"],
                extra_context=extra_context,
            )
            url_path_to_add = path(
                f"{url_path}/{element['stage']}/", element["view_class"].as_view(), name=element["short_name"]
            )
            urls.urlpatterns.append(url_path_to_add)
        self.logger.info(f"Added {url_path_to_add}")

    def traverse_framework(self) -> Generator[CAF32Element, None, None]:
        """
        Traverse the framework structure and yield those elements requiring their own
        page in a single sequence.
        """
        for objective_code, objective in self.framework.get("objectives", {}).items():
            objective_ = {
                # Add the dictionary taken from the YAML first so that our code value
                # is set from the dict key and not the value *within* the dict. We
                # can probably remove the code attributes from the YAML
                **objective,
                "type": "objective",
                "code": objective_code,
                "short_name": f"objective_{objective_code}",
                "parent": None,
            }
            yield objective_
            for principle_code, principle in objective.get("principles", {}).items():
                principle_ = {
                    **principle,
                    "type": "principle",
                    "code": principle_code,
                    "short_name": f"principle_{principle_code}",
                    "parent": objective_,
                }
                yield principle_
                for outcome_code, outcome in principle.get("outcomes", {}).items():
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"indicators_{outcome_code}",
                        "parent": principle_,
                        "stage": "indicators",
                    }
                    yield outcome_
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"confirmation_{outcome_code}",
                        "parent": principle_,
                        "stage": "confirmation",
                    }
                    yield outcome_

    def _process_outcome(self, element) -> None:
        if element.get("stage") == "indicators":
            provider: FieldProvider = OutcomeIndicatorsFieldProvider(element)
            indicators_form = create_form(provider)
            self._create_view_and_url(element, form_class=indicators_form)
        elif element.get("stage") == "confirmation":
            provider = OutcomeConfirmationFieldProvider(element)
            outcome_form = create_form(provider)
            self._create_view_and_url(element, form_class=outcome_form)

    def _create_route(self) -> None:
        for element in self.elements:
            if element["type"] == "objective":
                self._create_view_and_url(element, "objective")
            elif element["type"] == "principle":
                self._create_view_and_url(element, "principle")
            elif element["type"] == "outcome":
                self._process_outcome(element)

    def _read(self) -> None:
        with open(self.file_path, "r") as file:
            self.framework = yaml.safe_load(file)
            self.elements = list(self.traverse_framework())

    # Keeping this interface so we can separate generating the order of the elements
    # from creating the Django urls
    def execute(self) -> None:
        self._create_route()
