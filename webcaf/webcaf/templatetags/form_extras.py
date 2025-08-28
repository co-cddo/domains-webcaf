from django import template

register = template.Library()


@register.filter
def filter_fields(form, prefix):
    """
    Filter the fields of a form based on a specific prefix. This function retrieves all fields
    from the provided form whose names start with the given prefix and do not end with
    "_comment".

    :param form: The form instance containing the fields to filter.
    :type form: Any
    :param prefix: The prefix string used to filter the field names.
    :type prefix: str
    :return: A list of filtered fields that match the criteria.
    :rtype: list
    """
    return [field for field in form if field.name.startswith(prefix) and not field.name.endswith("_comment")]


@register.simple_tag
def get_comment_field(form, field_name, choice):
    """
    Retrieve a comment field from the given form based on the specified field name and choice.

    This function searches through the fields in the form for a field whose name
    matches the pattern of starting with the given field_name and ending with
    the specified choice and "_comment". If such a field exists, it returns the
    matching field. If no matching field is found, it returns None.

    :param form: The form object containing multiple fields.
    :type form: Iterable
    :param field_name: The base name of the field to search for. All matching
        fields should start with this base name.
    :type field_name: str
    :param choice: The choice identifier to narrow down the field search. All
        matching fields should end with this choice followed by "_comment".
    :type choice: str
    :return: The matched form field if found, otherwise None.
    :rtype: Optional[Any]
    """
    matched_fields = [
        field for field in form if field.name.startswith(field_name) and field.name.endswith(f"_{choice}_comment")
    ]
    if matched_fields:
        return matched_fields[0]
    return None
