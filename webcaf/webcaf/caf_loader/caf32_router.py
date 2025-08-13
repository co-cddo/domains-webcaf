import logging
from typing import Any

import yaml

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

    logger = logging.getLogger(__name__)
    all_url_names: list[str] = []
    parent_map: dict[str, Any] = {}

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

    def __init__(self, framework_path) -> None:
        self.file_path = framework_path
        self.framework: dict = {}
        self._read()
        self.all_url_names, self.parent_map = self._build_url_names(self.framework)

    def _read(self) -> None:
        with open(self.file_path, "r") as file:
            self.framework = yaml.safe_load(file)
