from django import template

from webcaf.webcaf.models import UserProfile

register = template.Library()


@register.filter
def call_method(obj, arg):
    """
    Utility method to call a method on an object. USed in the templates.
    :param obj:
    :param arg:
    :return:
    """
    return getattr(obj, arg)()  # or obj.my_method(arg) if you hardcode


@register.filter
def get_achieved_field(obj, arg):
    return obj.fields["achieved_" + arg]


@register.filter
def get_not_achieved_field(obj, arg):
    return obj.fields["not-achieved_" + arg]


@register.filter
def get_partially_achieved_field(obj, arg):
    return obj.fields["partially-achieved_" + arg]


@register.filter
def get_achieved_field_comment(obj, arg):
    return obj.fields.get(arg + "_comment", None)


@register.filter
def get_not_achieved_field_comment(obj, arg):
    return obj.fields.get(arg + "_comment", None)


@register.filter
def get_partially_achieved_field_comment(obj, arg):
    return obj.fields.get(arg + "_comment", None)


@register.simple_tag
def get_field_for_section(form, field_name, section_type):
    """Get field based on section type"""
    if section_type == "achieved":
        return get_achieved_field(form, field_name)
    elif section_type == "not-achieved":
        return get_not_achieved_field(form, field_name)
    elif section_type == "partially-achieved":
        return get_partially_achieved_field(form, field_name)
    return None


@register.simple_tag
def get_field_comment_for_section(form, full_name, section_type):
    """Get field comment based on section type"""
    if section_type == "achieved":
        return get_achieved_field_comment(form, full_name)
    elif section_type == "not-achieved":
        return get_not_achieved_field_comment(form, full_name)
    elif section_type == "partially-achieved":
        return get_partially_achieved_field_comment(form, full_name)
    return None


@register.simple_tag
def should_display_details_section(outcome_status, current_choice):
    if current_choice == "confirm":
        return False
    if outcome_status == "Not achieved" and current_choice in ("change_to_achieved", "change_to_partially_achieved"):
        return True
    if outcome_status == "Achieved" and current_choice in ("change_to_not_achieved", "change_to_partially_achieved"):
        return True
    return False


@register.simple_tag
def should_display_choice(outcome_status, current_choice):
    if outcome_status == "Not achieved" and current_choice in (
        "confirm",
        "change_to_achieved",
        "change_to_partially_achieved",
    ):
        return True
    if outcome_status == "Achieved" and current_choice in ("confirm", "change_to_partially_achieved"):
        return True
    if outcome_status == "Partially achieved" and current_choice in (
        "confirm",
        "change_to_not_achieved",
        "change_to_achieved",
    ):
        return True
    return False


@register.simple_tag
def get_field_value(form, field_name):
    return form.initial.get(field_name, "")


@register.simple_tag
def get_role_name(role):
    return next(filter(lambda x: x[0] == role, UserProfile.ROLE_CHOICES))[1]
