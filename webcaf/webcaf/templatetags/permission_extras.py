from django import template

from webcaf.webcaf.models import UserProfile
from webcaf.webcaf.utils.permission import PermissionUtil

register = template.Library()


@register.simple_tag()
def current_user_can_create_system(user_profile: UserProfile) -> bool:
    """
    Check if the current user has permission to create a system.

    This function utilizes the `PermissionUtil` utility to determine if the
    specified user has the required permissions to create a system.

    :param user_profile: The profile of the user to check permission for.
    :type user_profile: UserProfile
    :return: True if the user has permission to create a system, otherwise False.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_create_system(user_profile)


@register.simple_tag()
def current_user_can_view_systems(user_profile: UserProfile) -> bool:
    """
    Determines if the current user has permission to view systems.

    This function evaluates the provided user profile to check if the current user
    is authorized to view systems based on permission utility logic.

    :param user_profile: The profile of the user whose permissions are being checked.
    :type user_profile: UserProfile
    :return: True if the user can view systems, False otherwise.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_view_systems(user_profile)


@register.simple_tag()
def current_user_can_create_user(user_profile: UserProfile) -> bool:
    """
    Determine if the current user has permission to create another user.

    This function checks the user profile to determine if the current user
    has the necessary permissions to create a new user.

    :param user_profile: UserProfile object representing the current user.
    :type user_profile: UserProfile
    :return: Boolean indicating whether the current user has permission to
        create a new user.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_create_user(user_profile)


@register.simple_tag()
def current_user_can_view_users(user_profile: UserProfile) -> bool:
    """
    Checks if the current user has permissions to view user profiles.

    This function utilizes the `PermissionUtil.current_user_can_view_users` method to
    determine whether the current user has the necessary authorization to
    access user profile information.

    :param user_profile: The user profile to check permissions against.
    :type user_profile: Any
    :return: Boolean indicating whether the current user has permission to view
             the given user profile.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_view_users(user_profile)


@register.simple_tag()
def current_user_can_start_assessment(user_profile: UserProfile) -> bool:
    """
    Determines if the current user has the permission to start an assessment.

    :param user_profile: The profile of the user for whom the assessment start
        permission is being checked.
    :type user_profile: object
    :return: A boolean indicating whether the user can start an assessment.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_start_assessment(user_profile)


@register.simple_tag()
def current_user_can_submit_assessment(user_profile: UserProfile) -> bool:
    """
    Determines whether the current user has permission to submit assessments.

    :param user_profile: An instance of UserProfile representing the user's profile.
    :type user_profile: UserProfile
    :return: A boolean indicating whether the user can view assessments.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_submit_assessment(user_profile)


@register.simple_tag()
def current_user_can_view_assessments(user_profile: UserProfile) -> bool:
    """
    Determines whether the current user has permission to view assessments.

    :param user_profile: An instance of UserProfile representing the user's profile.
    :type user_profile: UserProfile
    :return: A boolean indicating whether the user can view assessments.
    :rtype: bool
    """
    return PermissionUtil.current_user_can_view_assessments(user_profile)


@register.simple_tag()
def get_my_account_text(user_profile: UserProfile) -> str:
    """
    Determines and retrieves a description text specific to the role of the provided user profile. The text varies
    depending on the role of the user, such as `cyber_advisor`, `organisation_lead`, or `organisation_user`.
    If no valid user profile is provided, it returns an empty string.

    :param user_profile: The user profile object containing role information
    :type user_profile: UserProfile
    :return: A string description corresponding to the role of the user, or an empty string if no user profile is provided.
    :rtype: str
    """
    return UserProfile.ROLE_DESCRIPTIONS[user_profile.role] if user_profile and user_profile.role else ""
