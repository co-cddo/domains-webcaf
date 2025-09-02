from webcaf.webcaf.models import UserProfile


class PermissionUtil:
    @staticmethod
    def current_user_can_create_system(user_profile: UserProfile):
        """
        Determines if the current user has the permissions to create a system based on their role.
        This method verifies the user's role in the system to ensure it matches the required criteria.

        :param user_profile: The profile object of the current user, containing user information
            and their role.
        :type user_profile: UserProfile
        :return: A boolean value indicating whether the user has the permission to create a system.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["cyber_advisor"]

    @staticmethod
    def current_user_can_view_systems(user_profile: UserProfile):
        """
        Checks if the current user has the necessary permissions to view systems.

        This method examines the role of the provided user profile to determine if
        the user is permitted to view systems. Only users with specific roles are
        granted access.

        :param user_profile: The user profile to be checked, representing the current
            user's details and permissions.
        :type user_profile: UserProfile
        :return: Returns a boolean indicating whether the current user is allowed
            to view systems.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["cyber_advisor"]

    @staticmethod
    def current_user_can_create_user(user_profile: UserProfile):
        """
        Checks if the current user has permissions to create a new user. The method evaluates whether
        the provided user has a role permitting user creation.

        :param user_profile: The profile of the user whose permissions are to be checked
        :type user_profile: UserProfile
        :return: A boolean indicating whether the user has creation permissions
        :rtype: bool
        """
        return user_profile and user_profile.role in ["cyber_advisor", "organisation_lead"]

    @staticmethod
    def current_user_can_delete_user(user_profile: UserProfile):
        """
        Determine if the current user has permissions to delete a given user
        profile. This check is based on the user's role.

        :param user_profile: The user profile to check for deletion permissions.
        :type user_profile: UserProfile
        :return: True if the current user can delete the given user profile,
            False otherwise.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["cyber_advisor", "organisation_lead"]

    @staticmethod
    def current_user_can_view_users(user_profile: UserProfile):
        """
        Checks if the current user has permissions to view users.

        This method determines whether a user has the necessary permissions based on
        their role. Roles that are granted permissions include 'cyber_advisor' and
        'organisation_lead'.

        :param user_profile: The profile object of the current user to check permissions for.
        :type user_profile: UserProfile
        :return: A boolean indicating whether the current user can view users.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["cyber_advisor", "organisation_lead"]

    @staticmethod
    def current_user_can_start_assessment(user_profile: UserProfile):
        """
        Determines if the current user has the necessary role to start an assessment.

        The method checks if the provided user profile exists and if the user's role
        is set to 'organisation_lead'. If both conditions are met, the method returns
        True, indicating that the user can start an assessment. Otherwise, it returns
        False.

        :param user_profile: The profile of the user for whom the authorization check
            is being performed.
        :type user_profile: UserProfile
        :return: A boolean value indicating whether the user can start an assessment.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["organisation_lead"]

    @staticmethod
    def current_user_can_view_assessments(user_profile: UserProfile):
        """
        Determines if the current user has permission to view assessments.

        This method checks whether the given user's role grants them the ability
        to view assessments. Only users with specific roles are allowed
        to view assessments within the system.

        :param user_profile: The user profile containing role information
            of the current user.
        :type user_profile: UserProfile
        :return: True if the user has the required permissions to view
            assessments, False otherwise.
        :rtype: bool
        """
        return user_profile and user_profile.role in ["organisation_lead", "organisation_user"]

    @staticmethod
    def current_user_can_submit_assessment(user_profile: UserProfile):
        """
        Checks if the current user has permissions to submit an assessment.

        This method evaluates whether the given user profile corresponds to a user role
        that is allowed to submit assessments. Only users with the role
        "organisation_lead" are granted this permission.

        :param user_profile: The profile of the user being checked for permission.
        :type user_profile: UserProfile
        :return: True if the user has the permission to submit an assessment,
            otherwise False.
        :rtype: bool
        """
        return user_profile and user_profile.role in [
            "organisation_lead",
        ]
