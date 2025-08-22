from abc import ABC, abstractmethod
from typing import Any, Generator

import yaml
from django.views.generic import FormView

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

    @abstractmethod
    def execute(self) -> None:
        pass


class CAF32Router(FrameworkRouter):
    def __init__(self, framework_path, exit_url: str = "index") -> None:
        self.file_path = framework_path
        self.exit_url = exit_url
        self.framework: CAF32Element = {}
        self.elements: list[CAF32Element] = []
        self._read()

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

    def _read(self) -> None:
        with open(self.file_path, "r") as file:
            self.framework = yaml.safe_load(file)
            self.elements = list(self.traverse_framework())

    # Keeping this interface so we can separate generating the order of the elements
    # from creating the Django urls
    def execute(self) -> None:
        self._read()
