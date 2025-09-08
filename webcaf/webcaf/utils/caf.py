import logging
from collections import defaultdict

from django.forms.forms import Form


class CafFormUtil:
    """
    Provides utility methods to work with form fields in a categorized manner.

    This utility class contains methods to retrieve category names based on
    field prefixes, and to calculate indexed positions of fields in human-readable
    formats for categorized forms. It also handles logging for any unexpected
    conditions while indexing fields.

    :ivar logger: Logger instance for logging errors and informational messages.
    :type logger: logging.Logger
    """

    logger = logging.getLogger("CafFormUtil")

    @staticmethod
    def get_category_name(field_name: str) -> str:
        """
        Determines and returns the category name based on the prefix of the given field name.

        The method analyzes the prefix of the provided `field_name` and maps it to a specific
        category name. If the prefix matches "achieved", the category is "Achieved". If the prefix
        matches "partially-achieved", the category is "Partially achieved". For all other prefixes,
        the category will be "Not achieved".

        :param field_name: The name of the field to evaluate.
        :type field_name: str
        :return: The corresponding category name based on the field name's prefix.
        :rtype: str
        """
        prefix = field_name.split("_")[0]
        if prefix == "achieved":
            return "Achieved"
        if prefix == "partially-achieved":
            return "Partially achieved"
        return "Not achieved"

    @staticmethod
    def human_index(form: Form, field_name: str) -> int:
        """
        Builds an index of fields categorized by their prefix and derives the human-readable
        index of a specific field within its category.

        :param form: The form object containing fields organized by category.
            Assumes that the provided form contains field names structured as
            "<category>_<name>" and skips fields ending with "_comment".
            Each category is determined as the prefix before the first underscore.

        :param field_name: The name of the field for which a human-readable index
            is derived. Should follow the format "<category>_<field_name>".

        :return: The derived integer index of the given field within its category,
            starting from 1. Returns -1 if the field is not found in the category.
        """
        # Build an index of fields by category prefix so we can derive human numbers per tab/category
        fields_by_category = defaultdict(list)
        for name in form.fields.keys():
            if not name.endswith("_comment"):
                category = name.split("_")[0]
                fields_by_category[category].append(name.split("_")[1])
        category, field_name = field_name.split("_")
        try:
            return fields_by_category[category].index(field_name) + 1
        except ValueError:
            # This shouldn't happen, but if it does, log an error and return a generic message
            CafFormUtil.logger.error(f"Field {field_name} not found in category {category}")
            return -1
