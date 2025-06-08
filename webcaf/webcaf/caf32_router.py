import copy

import yaml
from django.urls import path
from django.utils.text import slugify

from webcaf import urls

from .caf32_field_providers import (
    FieldProvider,
    SectionIndicatorsFieldProvider,
    SectionOutcomeFieldProvider,
)
from .form_factory import create_form
from .view_factory import create_form_view

FrameworkValue = str | dict | int | None


class FrameworkRouter:
    """
    This class is the primary interface between the YAML CAF and the rest of the application. It's declared
    as a class partly in case we later want to use an ABC to declare a common interface for different types
    of router.

    It reads the YAML and from there can produce a route based on all the sections, only those associated with
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
            template_name = "section.html"
            section_type = item_type.split("-")[1]
            class_prefix = f"Section{section_type.capitalize()}View"
            item["view_class"] = create_form_view(
                success_url_name=success_url_name,
                template_name=template_name,
                form_class=form_class,
                class_prefix=class_prefix,
                class_id=item["id"],
                extra_context=extra_context,
            )
            urls.urlpatterns.append(path(f"{url_path}/{section_type}/", item["view_class"].as_view(), name=url_name))

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
                for section_key, _ in principle.get("sections", {}).items():
                    indicators_url_name = f"section-indicators_{section_key}"
                    outcome_url_name = f"section-outcome_{section_key}"
                    all_url_names.append(indicators_url_name)
                    all_url_names.append(outcome_url_name)
        return all_url_names

    @staticmethod
    def _prepare_section_stage(
        section_base: dict,
        section_type: str,
        section_key: str,
        all_url_names: list[str],
        # Need to change this to a better default value
        exit_url: str = "#",
    ) -> tuple[dict, str, str]:
        """
        Prepares a stage in the route relating to a section, either where indicators are entered or
        the outcome is agreed.
        """
        item_copy = section_base.copy()
        item_copy["type"] = f"section-{section_type}"
        url_name = f"section-{section_type}_{section_key}"
        current_index = all_url_names.index(url_name)

        if section_type == "indicators":
            success_url = f"section-outcome_{section_key}"
        else:  # outcome
            success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)

        return item_copy, url_name, success_url

    @staticmethod
    def _process_section(
        section_key: str, section: dict, principle_key: str, obj_key: str, all_url_names: list[str], exit_url: str
    ) -> list[dict]:
        """
        Processes a 'section' dictionary from the CAF. Each section results in two pages in the route, one
        for indicators and the other for the result.

        If the section is the last element in the route the form button points to an exit url. Otherwise to
        the next page in the route, which can be a section, principle or objective.
        """
        items = []
        section_base = section.copy()
        section_base.update(
            {
                "id": section_key,
                "principle_id": principle_key,
                "objective_id": obj_key,
            }
        )
        indicators_copy, _, success_url = FrameworkRouter._prepare_section_stage(
            section_base, "indicators", section_key, all_url_names
        )
        provider: FieldProvider = SectionIndicatorsFieldProvider(indicators_copy)
        indicators_form = create_form(provider)
        indicators_copy, _ = FrameworkRouter._create_view_and_url(
            indicators_copy, "section-indicators", success_url, form_class=indicators_form
        )
        items.append(indicators_copy)
        outcome_copy, _, success_url = FrameworkRouter._prepare_section_stage(
            section_base, "outcome", section_key, all_url_names, exit_url
        )
        provider = SectionOutcomeFieldProvider(outcome_copy)
        outcome_form = create_form(provider)
        outcome_copy, _ = FrameworkRouter._create_view_and_url(
            outcome_copy, "section-outcome", success_url, form_class=outcome_form
        )
        items.append(outcome_copy)
        return items

    @staticmethod
    def _process_principle(
        principle_key: str, principle: dict, obj_key: str, all_url_names: list[str], exit_url: str
    ) -> tuple[dict, list[dict]]:
        """
        Processes a 'principle' dictionary from the CAF. These are much simpler than sections.
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
        if "sections" in principle_copy:
            del principle_copy["sections"]
        current_index = all_url_names.index(f"principle_{principle_key}")
        success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)
        principle_copy, _ = FrameworkRouter._create_view_and_url(principle_copy, "principle", success_url)
        for section_key, section in principle.get("sections", {}).items():
            section_items = FrameworkRouter._process_section(
                section_key, section, principle_key, obj_key, all_url_names, exit_url
            )
            items.extend(section_items)
        return principle_copy, items

    @staticmethod
    def _create_route(framework: dict, exit_url: str = "index") -> list[dict[str, FrameworkValue]]:
        """
        Takes a dictionary representing the CAF framework, or a subset of it, and creates a linear
        route through the web application. This is done by creating a view class and form class for
        each page and then adding the paths to Django's urlpatterns.

        This directly handles the objectives elements and calls other methods to deal with the
        principles and sections.
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
                principle_copy, section_items = FrameworkRouter._process_principle(
                    principle_key, principle, obj_key, all_url_names, exit_url
                )
                flattened.append(principle_copy)
                flattened.extend(section_items)
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
        removes sections which do not match the scope argument, then any principles which do not have
        any sections, then any objectives which do not have any principles.
        """
        filtered_framework = copy.deepcopy(self.framework)
        principles_to_keep = set()
        objectives_to_keep = set()
        for obj_key, objective in list(filtered_framework.get("objectives", {}).items()):
            for principle_key, principle in list(objective.get("principles", {}).items()):
                has_sections = False
                for section_key, section in list(principle.get("sections", {}).items()):
                    if section.get("scope") != scope:
                        del principle["sections"][section_key]
                    else:
                        has_sections = True
                        principles_to_keep.add(principle_key)
                        objectives_to_keep.add(obj_key)
                if not has_sections:
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
