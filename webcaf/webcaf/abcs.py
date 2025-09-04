from abc import ABC, abstractmethod
from typing import Optional


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
    def get_sections(self) -> list[dict]:
        pass

    @abstractmethod
    def get_section(self, id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def execute(self) -> None:
        pass


class FieldProvider(ABC):
    """
    An interface for providing specifications for form fields, based on an
    assessment framework. These are consumed by the form factory.

    The purpose of this class is to separate the form factory from the
    specifics of the assessment framework.
    """

    @abstractmethod
    def get_metadata(self) -> Optional[dict]:
        pass

    @abstractmethod
    def get_field_definitions(self) -> list[dict]:
        pass
