import yaml
from django.urls import NoReverseMatch, path, reverse_lazy
from django.utils.text import slugify

from webcaf import urls
from webcaf.webcaf.form_factory import create_form
from webcaf.webcaf.view_factory import create_form_view

# Import two field providers, so we can switch for demo purposes
from .caf32_field_providers import OutcomeIndicatorsFieldProvider  # noqa: F401
from .caf32_field_providers import TabbedOutcomeIndicatorsFieldProvider  # noqa: F401
from .caf32_field_providers import FieldProvider, OutcomeConfirmationFieldProvider

# INDICATORS_FIELD_PROVIDER = OutcomeIndicatorsFieldProvider
INDICATORS_FIELD_PROVIDER = TabbedOutcomeIndicatorsFieldProvider

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
    def _build_breadcrumbs(url_name, parent_map):
        breadcrumbs = []
        current = url_name
        while current in parent_map:
            parent = parent_map[current]["parent"]
            text = parent_map[current]["text"]
            try:
                url = reverse_lazy(current)
            except NoReverseMatch:
                url = "#"
            breadcrumbs.insert(0, {"url": url, "text": text})
            current = parent
        if current == "root":
            breadcrumbs.insert(0, {"url": "#", "text": "Root"})
        return breadcrumbs

    @staticmethod
    def _create_view_and_url(
        item: dict, item_type: str, success_url_name: str, parent_map, url_name, form_class=None
    ) -> tuple[dict, str]:
        """
        Takes an element from the CAF, the url for the next page in the route and a form class
        to create a view class and add a path for the view to Django's urlpatterns.
        """
        url_path = slugify(f"{item['code']}-{item['title']}")
        extra_context = {
            "title": item.get("title"),
            "description": item.get("description"),
            "breadcrumbs": FrameworkRouter._build_breadcrumbs(url_name, parent_map),
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
    def _build_url_names(framework: dict):
        """
        Each page in the route has a form button that points to the next page. This means we need the name
        of the next url in the sequence each time we generate a view class and form class. This builds a
        list of all the url names for this purpose.
        """
        all_url_names = []
        parent_map = {}
        for obj_key, objective in framework.get("objectives", {}).items():
            obj_url_name = f"objective_{obj_key}"
            all_url_names.append(obj_url_name)
            parent_map[obj_url_name] = {"parent": "root", "text": objective.get("title", obj_key)}
            for principle_key, principle in objective.get("principles", {}).items():
                principle_url_name = f"principle_{principle_key}"
                all_url_names.append(principle_url_name)
                parent_map[principle_url_name] = {"parent": obj_url_name, "text": principle.get("title", principle_key)}
                for outcome_key, outcome in principle.get("outcomes", {}).items():
                    indicators_url_name = f"indicators_{outcome_key}"
                    outcome_url_name = f"confirmation_{outcome_key}"
                    all_url_names.append(indicators_url_name)
                    all_url_names.append(outcome_url_name)
                    parent_map[indicators_url_name] = {
                        "parent": principle_url_name,
                        "text": outcome.get("title", outcome_key),
                    }
                    parent_map[outcome_url_name] = {
                        "parent": principle_url_name,
                        "text": outcome.get("title", outcome_key),
                    }
        return all_url_names, parent_map

    @staticmethod
    def _prepare_outcome_stage(
        outcome: dict,
        outcome_stage: str,
        outcome_key: str,
        all_url_names: list[str],
        parent_map: dict,
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
        outcome_key: str,
        outcome: dict,
        principle_key: str,
        obj_key: str,
        all_url_names: list[str],
        parent_map: dict,
        exit_url: str,
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
        indicators_stage, indicators_url_name, success_url = FrameworkRouter._prepare_outcome_stage(
            outcome_copy, "indicators", outcome_key, all_url_names, parent_map
        )
        # Once we settle on a design we can just use the desired field provider
        provider: FieldProvider = INDICATORS_FIELD_PROVIDER(indicators_stage)
        indicators_form = create_form(provider)
        indicators_stage, _ = FrameworkRouter._create_view_and_url(
            indicators_stage, "indicators", success_url, parent_map, indicators_url_name, form_class=indicators_form
        )
        items.append(indicators_stage)
        confirmation_stage, confirmation_url_name, success_url = FrameworkRouter._prepare_outcome_stage(
            outcome_copy, "confirmation", outcome_key, all_url_names, parent_map, exit_url
        )
        provider = OutcomeConfirmationFieldProvider(confirmation_stage)
        outcome_form = create_form(provider)
        confirmation_stage, _ = FrameworkRouter._create_view_and_url(
            confirmation_stage, "confirmation", success_url, parent_map, confirmation_url_name, form_class=outcome_form
        )
        items.append(confirmation_stage)
        return items

    @staticmethod
    def _process_principle(
        principle_key: str, principle: dict, obj_key: str, all_url_names: list[str], parent_map: dict, exit_url: str
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
        principle_copy, _ = FrameworkRouter._create_view_and_url(
            principle_copy, "principle", success_url, parent_map, f"principle_{principle_key}"
        )
        for outcome_key, outcome in principle.get("outcomes", {}).items():
            outcome_items = FrameworkRouter._process_outcome(
                outcome_key, outcome, principle_key, obj_key, all_url_names, parent_map, exit_url
            )
            items.extend(outcome_items)
        return principle_copy, items

    @staticmethod
    def _create_route(framework: dict, exit_url: str = "index") -> None:
        """
        Takes a dictionary representing the CAF framework, or a subset of it, and creates a linear
        route through the web application. This is done by creating a view class and form class for
        each page and then adding the paths to Django's urlpatterns.

        This directly handles the objectives elements and calls other methods to deal with the
        principles and outcomes.
        """
        all_url_names, parent_map = FrameworkRouter._build_url_names(framework)
        for i, obj_key in enumerate(framework.get("objectives", {}).items()):
            obj_key, objective = obj_key
            obj_copy = objective.copy()
            obj_copy.update({"type": "objective", "id": obj_key})
            if "principles" in obj_copy:
                del obj_copy["principles"]
            current_index = all_url_names.index(f"objective_{obj_key}")
            success_url = FrameworkRouter._get_success_url(current_index, all_url_names, exit_url)
            obj_copy, _ = FrameworkRouter._create_view_and_url(
                obj_copy, "objective", success_url, parent_map, f"objective_{obj_key}"
            )
            for principle_key, principle in objective.get("principles", {}).items():
                FrameworkRouter._process_principle(
                    principle_key, principle, obj_key, all_url_names, parent_map, exit_url
                )

    def __init__(self, framework_path) -> None:
        self.file_path = framework_path
        self.framework: dict = {}
        self._read()

    def _read(self) -> None:
        with open(self.file_path, "r") as file:
            self.framework = yaml.safe_load(file)

    def all_route(self) -> None:
        self._create_route(self.framework)
