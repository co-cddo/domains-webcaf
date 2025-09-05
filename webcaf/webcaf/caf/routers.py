import logging
import os
from typing import Any, Generator, Optional

import yaml
from django.conf import settings
from django.urls import path, reverse_lazy
from django.utils.text import slugify
from django.views.generic import FormView

from webcaf import urls
from webcaf.webcaf.abcs import FrameworkRouter
from webcaf.webcaf.caf.views.factory import create_form_view
from webcaf.webcaf.forms.factory import create_form

from .field_providers import (
    FieldProvider,
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)

FrameworkValue = str | dict | int | None

FormViewClass = type[FormView]

CAF32Element = dict[str, Any]


class CAF32Router(FrameworkRouter):
    framework_path = os.path.join(settings.BASE_DIR, "..", "frameworks", "cyber-assessment-framework-v3.2.yaml")
    path_prefix = "caf32"
    logger = logging.getLogger("CAF32Router")

    @staticmethod
    def _build_breadcrumbs(element: CAF32Element) -> list[dict[str, str]]:
        breadcrumbs: list = []
        # We can only build the root breadcrumb here as the rest of it is dependent on the current assessment
        breadcrumbs.insert(0, {"url": reverse_lazy("my-account"), "text": "My account"})
        return breadcrumbs

    def __init__(self, exit_url: str = "index") -> None:
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
            template_name = f"caf/{element['type']}.html"
            class_prefix = f"{self.__class__.path_prefix.capitalize()}{element['type'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                class_prefix=class_prefix,
                class_id=element["code"],
                extra_context=extra_context | {"objective_data": element},
            )
            url_to_add = path(
                f"{self.__class__.path_prefix}/{url_path}/",
                element["view_class"].as_view(),
                name=element["short_name"],
            )
            urls.urlpatterns.append(url_to_add)
        else:
            template_name = f"caf/{element['stage']}.html"
            class_prefix = f"{self.__class__.path_prefix.capitalize()}Outcome{element['stage'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                form_class=form_class,
                class_prefix=class_prefix,
                stage=element["stage"],
                class_id=element["code"],
                extra_context=extra_context
                | {
                    "objective_name": f"Objective {element['parent']['parent']['code']} - {element['parent']['parent']['title']}",
                    "objective_code": element["parent"]["parent"]["code"],
                    "outcome": element,
                    "objective_data": element["parent"]["parent"],
                },
            )
            url_to_add = path(
                f"{self.__class__.path_prefix}/{url_path}/{element['stage']}/",
                element["view_class"].as_view(),
                name=element["short_name"],
            )
            urls.urlpatterns.append(url_to_add)
        self.logger.info(f"Added {url_to_add}")

    def _traverse_framework(self) -> Generator[CAF32Element, None, None]:
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
                "short_name": f"{self.__class__.path_prefix}_objective_{objective_code}",
                "parent": None,
            }
            yield objective_
            for principle_code, principle in objective.get("principles", {}).items():
                principle_ = {
                    **principle,
                    "type": "principle",
                    "code": principle_code,
                    "short_name": f"{self.__class__.path_prefix}_principle_{principle_code}",
                    "parent": objective_,
                }
                yield principle_
                for outcome_code, outcome in principle.get("outcomes", {}).items():
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"{self.__class__.path_prefix}_indicators_{outcome_code}",
                        "parent": principle_,
                        "stage": "indicators",
                    }
                    yield outcome_
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"{self.__class__.path_prefix}_confirmation_{outcome_code}",
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
        with open(self.__class__.framework_path, "r") as file:
            self.framework = yaml.safe_load(file)
            self.elements = list(self._traverse_framework())

    def get_sections(self) -> list[dict]:
        return list(filter(lambda x: x["type"] == "objective", self.elements))

    def get_section(self, objective_id: str) -> Optional[dict]:
        return next((x for x in self.get_sections() if x["code"] == objective_id), None)

    # Keeping this interface so we can separate generating the order of the elements
    # from creating the Django urls
    def execute(self) -> None:
        self._create_route()


class CAF40Router(CAF32Router):
    framework_path = os.path.join(settings.BASE_DIR, "..", "frameworks", "cyber-assessment-framework-v4.0.yaml")
    path_prefix = "caf40"
    logger = logging.getLogger("CAF40Router")
