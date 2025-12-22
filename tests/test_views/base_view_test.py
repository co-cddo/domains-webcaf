from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase

from webcaf.webcaf.models import Organisation, System, UserProfile


class BaseViewTest(TestCase):
    """
    Base class for testing the views.
    This sets up the base data such as organisations, systems and the users for testing.
    """

    org_map: dict[str, Any] = {}

    @classmethod
    def email_from_username_and_org(cls, user_name, org_name):
        """
        Converts a username and organization name into an email address.

        :param user_name: The username of the individual.
        :param org_name: The name of the organization.

        :return: A formatted email address in the format `username@organization.gov.uk`.
        """
        return f"{user_name}@{org_name.lower().replace(' ', '')}.gov.uk"

    @classmethod
    def setUpTestData(cls):
        """
        Summary:
            Set up test data for organisations, systems, and users.

        :param: None

        :return: None

        Details:
            This class method is used to set up initial test data in the database.
            It creates several organisations with associated systems and users.
            Each organisation has a "Big", "Medium", and "Large" version of each system and user type.
            The users are created with email addresses derived from their usernames and organisation names.

        Notes:
            - This method is intended to be used in test cases to provide consistent data for testing.
            - It uses Django ORM's `get_or_create` method to avoid creating duplicates if the data already exists.
        """
        for org_name in ["Big organisation", "Medium organisation", "Large organisation"]:
            org, created = Organisation.objects.get_or_create(name=org_name)
            cls.org_map[org_name] = {}
            cls.org_map[org_name]["organisation"] = org

            cls.org_map[org_name]["systems"] = {}
            for system_name in ["Big system", "Medium system", "Large system"]:
                system, created = System.objects.get_or_create(name=system_name, organisation=org)
                cls.org_map[org_name]["systems"][system_name] = system

            cls.org_map[org_name]["users"] = {}
            for user_name in ["organisation_user", "organisation_lead", "cyber_advisor", "assessor"]:
                user_name_with_email = cls.email_from_username_and_org(user_name, org_name)
                user, created = User.objects.get_or_create(
                    username=user_name_with_email,
                )
                cls.org_map[org_name]["users"][user_name] = user
                if created:
                    UserProfile.objects.get_or_create(user=user, role=user_name, organisation=org)

        # Initial configuration for testing
        cls.user_role = "organisation_user"
        cls.organisation_name = "Big organisation"
        cls.system_name = "Medium system"

        cls.user_profile = UserProfile.objects.get(role=cls.user_role, organisation__name=cls.organisation_name)
        cls.test_system = System.objects.get(name=cls.system_name, organisation__name=cls.organisation_name)

        cls.test_user = User.objects.get(username=cls.email_from_username_and_org(cls.user_role, cls.organisation_name))
        cls.test_organisation = Organisation.objects.get(id=cls.test_system.organisation.id)
