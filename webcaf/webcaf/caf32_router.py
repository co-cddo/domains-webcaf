import copy

import yaml
from django.urls import path
from django.utils.text import slugify

from webcaf import urls

from .caf32_field_providers import (
    FieldProvider,
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)
from .form_factory import create_form
from .view_factory import create_form_view

FrameworkValue = str | dict | int | None


class FrameworkRouter:
    """
    This class is the primary interface between the YAML CAF and the rest of the application. It's declared
    as a class partly in case we later want to use an ABC to declare a common interface for different types
    of router.

    It reads the YAML and from there can produce a route based on all the outcomes, only those associated with
    organisations or only those associated with systems. This is done by creating a class for each view and form
    element in the CAF then updating Django's url patterns with paths to the views. Each form is provided the
    success_url for the next page in the route.
    """

    @staticmethod
    def _get_success_url(current_index: int, all_url_names: list[str], exit_url: str) -> str:
        """
        Determine the success URL for a form.
        If there's a next URL in the sequence, use that, otherwise use the exit URL.
        """
        if current_index + 1 < len(all_url_names):
            return all_url_names[current_index + 1]
        else:
            return exit_url

    @staticmethod
    def _create_view_and_url(item: dict, item_type: str, success_url_name: str, form_class=None) -> tuple[dict, str]:
        """
        Takes an element from the CAF, the url for the next page in the route and a form class
        to create a view class and add a path for the view to Django's urlpatterns.
        """
        url_path = slugify(f"{item['code']}-{item['title']}")
        url_name = f"{item_type}_{item['id']}"
        extra_context = {
            "title": item.get("title"),
            "description": item.get("description"),
        }
        if item_type in ["objective", "principle"]:
            template_name = "title.html"
            class_prefix = f"{item_type.capitalize()}View"
            item["view_class"] = create_form_view(
                success_url_name=success_url_name,
                template_name=template_name,
                class_prefix=class_prefix,
                class_id=item["id"],
                extra_context=extra_context,
            )
            urls.urlpatterns.append(path(f"{url_path}/", item["view_class"].as_view(), name=url_name))
        else:
            template_name = "outcome.html"
            class_prefix = f"Outcome{item_type.capitalize()}View"
            item["view_class"] = create_form_view(
                success_url_name=success_url_name,
                template_name=template_name,
                form_class=form_class,
                class_prefix=class_prefix,
                class_id=item["id"],
                extra_context=extra_context,
            )
            urls.urlpatterns.append(path(f"{url_path}/{item_type}/", item["view_class"].as_view(), name=url_name))

        return item, url_name

    @staticmethod
    def _build_url_names(framework: dict) -> list[str]:
        """
        Each page in the route has a form button that points to the next page. This means we need the name
        of the next url in the sequence each time we generate a view class and form class. This builds a
        list of all the url names for this purpose.
        """
        all_url_names = []
        for obj_key, objective in framework.get("objectives", {}).items():
            obj_url_name = f"objective_{obj_key}"
            all_url_names.append(obj_url_name)
            for principle_key, principle in objective.get("principles", {}).items():
                principle_url_name = f"principle_{principle_key}"
                all_url_names.append(principle_url_name)
                for outcome_key, _ in principle.get("outcomes", {}).items():
                    indicators_url_name = f"indicators_{outcome_key}"
                    outcome_url_name = f"confirmation_{outcome_key}"
                    all_url_names.append(indicators_url_name)
                    all_url_names.append(outcome_url_name)
        return all_url_names

    @staticmethod
    def _prepare_outcome_stage(
        outcome: dict,
        outcome_stage: str,
        outcome_key: str,
        all_url_names: list[str],
        # Need to change this to a better default value
        exit_url: str = "#",
    ) -> tuple[dict, str, str]:
        """
        Prepares a stage in the route relating to a outcome, either where indicators are entered or
        the outcome is agreed.
        """
        outcome_copy = outcome.copy()
        outcome_copy["type"] = f"outcome-{outcome_stage}"
        url_name = f"{outcome_stage}_{outcome_key}"
        current_index = all_url_names.index(url_name)

        if outcome_stage == "indicators":
            success_url = f"confirmation_{outcome_key}"
        else:
            success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)

        return outcome_copy, url_name, success_url

    @staticmethod
    def _process_outcome(
        outcome_key: str, outcome: dict, principle_key: str, obj_key: str, all_url_names: list[str], exit_url: str
    ) -> list[dict]:
        """
        Processes a 'outcome' dictionary from the CAF. Each outcome results in two pages in the route, one
        for indicators and the other for the result.

        If the outcome is the last element in the route the form button points to an exit url. Otherwise to
        the next page in the route, which can be a outcome, principle or objective.
        """
        items = []
        outcome_copy = outcome.copy()
        outcome_copy.update(
            {
                "id": outcome_key,
                "principle_id": principle_key,
                "objective_id": obj_key,
            }
        )
        indicators_stage, _, success_url = FrameworkRouter._prepare_outcome_stage(
            outcome_copy, "indicators", outcome_key, all_url_names
        )
        provider: FieldProvider = OutcomeIndicatorsFieldProvider(indicators_stage)
        indicators_form = create_form(provider)
        indicators_stage, _ = FrameworkRouter._create_view_and_url(
            indicators_stage, "indicators", success_url, form_class=indicators_form
        )
        items.append(indicators_stage)
        confirmation_stage, _, success_url = FrameworkRouter._prepare_outcome_stage(
            outcome_copy, "confirmation", outcome_key, all_url_names, exit_url
        )
        provider = OutcomeConfirmationFieldProvider(confirmation_stage)
        outcome_form = create_form(provider)
        confirmation_stage, _ = FrameworkRouter._create_view_and_url(
            confirmation_stage, "confirmation", success_url, form_class=outcome_form
        )
        items.append(confirmation_stage)
        return items

    @staticmethod
    def _process_principle(
        principle_key: str, principle: dict, obj_key: str, all_url_names: list[str], exit_url: str
    ) -> tuple[dict, list[dict]]:
        """
        Processes a 'principle' dictionary from the CAF. These are much simpler than outcomes.
        """
        items = []
        principle_copy = principle.copy()
        principle_copy.update(
            {
                "type": "principle",
                "id": principle_key,
                "objective_id": obj_key,
            }
        )
        if "outcomes" in principle_copy:
            del principle_copy["outcomes"]
        current_index = all_url_names.index(f"principle_{principle_key}")
        success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)
        principle_copy, _ = FrameworkRouter._create_view_and_url(principle_copy, "principle", success_url)
        for outcome_key, outcome in principle.get("outcomes", {}).items():
            outcome_items = FrameworkRouter._process_outcome(
                outcome_key, outcome, principle_key, obj_key, all_url_names, exit_url
            )
            items.extend(outcome_items)
        return principle_copy, items

    @staticmethod
    def _create_route(framework: dict, exit_url: str = "index") -> list[dict[str, FrameworkValue]]:
        """
        Takes a dictionary representing the CAF framework, or a subset of it, and creates a linear
        route through the web application. This is done by creating a view class and form class for
        each page and then adding the paths to Django's urlpatterns.

        This directly handles the objectives elements and calls other methods to deal with the
        principles and outcomes.
        """
        # There are currenltly no protections against this being called more than once, which would lead
        # to pages displaying in the wrong order if called with different parameters
        flattened = []
        all_url_names = FrameworkRouter._build_url_names(framework)
        for i, obj_key in enumerate(framework.get("objectives", {}).items()):
            obj_key, objective = obj_key
            obj_copy = objective.copy()
            obj_copy.update({"type": "objective", "id": obj_key})
            if "principles" in obj_copy:
                del obj_copy["principles"]
            current_index = all_url_names.index(f"objective_{obj_key}")
            success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)
            obj_copy, _ = FrameworkRouter._create_view_and_url(obj_copy, "objective", success_url)
            flattened.append(obj_copy)
            for principle_key, principle in objective.get("principles", {}).items():
                principle_copy, outcome_items = FrameworkRouter._process_principle(
                    principle_key, principle, obj_key, all_url_names, exit_url
                )
                flattened.append(principle_copy)
                flattened.extend(outcome_items)
        return flattened

    def __init__(self, framework_path) -> None:
        self.file_path = framework_path
        self.framework: dict = {}
        self._read()

    def _read(self) -> None:
        with open(self.file_path, "r") as file:
            self.framework = yaml.safe_load(file)

    def _filter_framework_by_scope(self, scope: str) -> dict[str, FrameworkValue]:
        """
        This filters the framework according to the scope which is either 'organisation' or 'system'. It
        removes outcomes which do not match the scope argument, then any principles which do not have
        any outcomes, then any objectives which do not have any principles.
        """
        filtered_framework = copy.deepcopy(self.framework)
        principles_to_keep = set()
        objectives_to_keep = set()
        for obj_key, objective in list(filtered_framework.get("objectives", {}).items()):
            for principle_key, principle in list(objective.get("principles", {}).items()):
                has_outcomes = False
                for outcome_key, outcome in list(principle.get("outcomes", {}).items()):
                    if outcome.get("scope") != scope:
                        del principle["outcomes"][outcome_key]
                    else:
                        has_outcomes = True
                        principles_to_keep.add(principle_key)
                        objectives_to_keep.add(obj_key)
                if not has_outcomes:
                    del objective["principles"][principle_key]
            if obj_key not in objectives_to_keep:
                del filtered_framework["objectives"][obj_key]
        return filtered_framework

    # This is currently only used in the tests but it's useful since it doesn't interfere
    # with the ordering of the pages
    def all_route(self) -> list[dict[str, FrameworkValue]]:
        return self._create_route(self.framework)

    def org_route(self) -> list[dict[str, FrameworkValue]]:
        filtered = self._filter_framework_by_scope("organisation")
        return self._create_route(filtered)

    def system_route(self) -> list[dict[str, FrameworkValue]]:
        filtered = self._filter_framework_by_scope("system")
        return self._create_route(filtered)
