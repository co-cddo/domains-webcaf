import csv
from io import BytesIO, StringIO

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from webcaf.webcaf.admin import OrganisationAdmin
from webcaf.webcaf.models import Organisation, UserProfile


def add_middleware(request):
    """
    Adds and processes Django middleware to the request object, enabling session
    and message handling.

    This function initializes and invokes Django's SessionMiddleware
    and MessageMiddleware to process the given request. It ensures that
    request.session is properly initialized and saved, and prepares the request
    for message management.

    :param request: The HTTP request object that middleware will process.
    :type request: HttpRequest
    :return: The processed HTTP request object with initialized session and
        message handling.
    :rtype: HttpRequest
    """

    # Django middleware expects a callable to initialize
    def get_response(request):
        return HttpResponse()

    # Initialize middleware properly
    session_middleware = SessionMiddleware(get_response)
    session_middleware.process_request(request)
    request.session.save()

    message_middleware = MessageMiddleware(get_response)
    message_middleware.process_request(request)

    return request


class OrganisationAdminImportCSVTest(TestCase):
    """Tests for the OrganisationAdmin import_csv method."""

    def setUp(self):
        """Set up test data and instances for each test."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = OrganisationAdmin(Organisation, self.site)

        # Create a superuser for admin requests

        self.superuser = User.objects.create_superuser(
            username="admin@test.gov.uk", email="admin@test.gov.uk", password="testpass123"  # pragma: allowlist secret
        )

    def create_csv_file(self, rows):
        """
        Helper method to create an InMemoryUploadedFile from CSV data.

        :param rows: List of dictionaries representing CSV rows
        :return: InMemoryUploadedFile object
        """
        csv_buffer = StringIO()
        if rows:
            writer = csv.DictWriter(csv_buffer, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        csv_buffer.seek(0)
        csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        return InMemoryUploadedFile(csv_bytes, "file", "test.csv", "text/csv", csv_bytes.getbuffer().nbytes, None)

    def test_import_csv_get_request_renders_form(self):
        """Test that GET request renders the upload form."""
        request = self.factory.get("/admin/webcaf/organisation/import-org-csv/")
        request.user = self.superuser

        response = self.admin.import_csv(add_middleware(request))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Import CSV File", response.content)

    def test_import_csv_creates_new_organisation(self):
        """Test that import_csv creates a new organisation when it doesn't exist."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user1@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Check organisation was created
        self.assertTrue(Organisation.objects.filter(name="Test Organisation").exists())
        org = Organisation.objects.get(name="Test Organisation")

        # Check user was created
        self.assertTrue(User.objects.filter(email="user1@test.gov.uk").exists())

        # Check user profile was created
        user = User.objects.get(email="user1@test.gov.uk")
        self.assertTrue(UserProfile.objects.filter(user=user, organisation=org, role="cyber_advisor").exists())

    def test_import_csv_finds_existing_organisation_by_reference(self):
        """Test that import_csv finds existing organisation by reference."""
        existing_org = Organisation.objects.create(name="Existing Org", reference="ORG001")

        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Different Name",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Should not create a new organisation
        self.assertEqual(Organisation.objects.count(), 1)

        # Should use existing organisation
        user = User.objects.get(email="user@test.gov.uk")
        self.assertTrue(UserProfile.objects.filter(user=user, organisation=existing_org).exists())

    def test_import_csv_finds_existing_organisation_by_name(self):
        """Test that import_csv finds existing organisation by name when reference is empty."""
        existing_org = Organisation.objects.create(name="Existing Org")

        csv_data = [
            {
                "Reference": "",
                "Type": "",
                "Organisation": "Existing Org",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Should not create a new organisation
        self.assertEqual(Organisation.objects.count(), 1)

        # Should use existing organisation
        user = User.objects.get(email="user@test.gov.uk")
        self.assertTrue(UserProfile.objects.filter(user=user, organisation=existing_org).exists())

    def test_import_csv_creates_multiple_users_from_email_columns(self):
        """Test that import_csv creates users from all email columns."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user1@test.gov.uk",
                "Email2": "user2@test.gov.uk",
                "Email3": "user3@test.gov.uk",
                "Email4": "user4@test.gov.uk",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Check all users were created
        org = Organisation.objects.get(name="Test Organisation")
        for i in range(1, 5):
            email = f"user{i}@test.gov.uk"
            self.assertTrue(User.objects.filter(email=email).exists())
            user = User.objects.get(email=email)
            self.assertTrue(UserProfile.objects.filter(user=user, organisation=org, role="cyber_advisor").exists())

    def test_import_csv_skips_empty_email_fields(self):
        """Test that import_csv skips empty email fields."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user1@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Only one user should be created
        org = Organisation.objects.get(name="Test Organisation")
        self.assertEqual(UserProfile.objects.filter(organisation=org).count(), 1)

    def test_import_csv_uses_existing_user(self):
        """Test that import_csv uses existing user instead of creating duplicate."""
        User.objects.create_user(username="existing@test.gov.uk", email="existing@test.gov.uk")

        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "existing@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Should only be one user with this email
        self.assertEqual(User.objects.filter(email="existing@test.gov.uk").count(), 1)

    def test_import_csv_warns_on_duplicate_user_profile(self):
        """Test that import_csv warns when user profile already exists."""
        org = Organisation.objects.create(name="Test Organisation", reference="ORG001")
        user = User.objects.create_user("user@test.gov.uk", "user@test.gov.uk")
        UserProfile.objects.create(user=user, organisation=org, role="cyber_advisor")

        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Should still only be one profile
        self.assertEqual(UserProfile.objects.filter(user=user, organisation=org).count(), 1)

    def test_import_csv_sets_parent_organisation(self):
        """Test that import_csv correctly sets parent organisation relationships."""
        csv_data = [
            {
                "Reference": "PARENT001",
                "Type": "",
                "Organisation": "Parent Organisation",
                "Lead Government Department": "",
                "Email1": "parent@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            },
            {
                "Reference": "CHILD001",
                "Organisation": "Child Organisation",
                "Lead Government Department": "Parent Organisation",
                "Email1": "child@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            },
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        parent_org = Organisation.objects.get(name="Parent Organisation")
        child_org = Organisation.objects.get(name="Child Organisation")

        # Parent should have no parent
        self.assertIsNone(parent_org.parent_organisation)

        # Child should have parent
        self.assertEqual(child_org.parent_organisation, parent_org)

    def test_import_csv_parent_organisation_is_self(self):
        """Test that organisation does not become its own parent."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Self Organisation",
                "Lead Government Department": "Self Organisation",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        org = Organisation.objects.get(name="Self Organisation")

        # Should not be its own parent
        self.assertIsNone(org.parent_organisation)

    def test_import_csv_processes_multiple_rows(self):
        """Test that import_csv processes multiple rows correctly."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Organisation 1",
                "Lead Government Department": "",
                "Email1": "user1@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            },
            {
                "Reference": "ORG002",
                "Type": "",
                "Organisation": "Organisation 2",
                "Lead Government Department": "",
                "Email1": "user2@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            },
            {
                "Reference": "ORG003",
                "Type": "",
                "Organisation": "Organisation 3",
                "Lead Government Department": "",
                "Email1": "user3@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            },
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Check all organisations were created
        self.assertEqual(Organisation.objects.count(), 3)
        self.assertTrue(Organisation.objects.filter(name="Organisation 1").exists())
        self.assertTrue(Organisation.objects.filter(name="Organisation 2").exists())
        self.assertTrue(Organisation.objects.filter(name="Organisation 3").exists())

    def test_import_csv_strips_whitespace_from_emails(self):
        """Test that import_csv strips whitespace from email addresses."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "  user@test.gov.uk  ",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Should create user with stripped email
        self.assertTrue(User.objects.filter(email="user@test.gov.uk").exists())

    def test_find_organisation_by_reference(self):
        """Test that find_organisation finds organisation by reference."""
        org = Organisation.objects.create(name="Test Org", reference="ORG001")

        row = {"Reference": "ORG001", "Organisation": "Test Org"}
        found_org = self.admin.find_organisation(row)

        self.assertEqual(found_org, org)

    def test_find_organisation_by_name_when_no_reference(self):
        """Test that find_organisation falls back to name when reference is empty."""
        org = Organisation.objects.create(name="Test Org")

        row = {"Reference": "", "Organisation": "Test Org"}
        found_org = self.admin.find_organisation(row)

        self.assertEqual(found_org, org)

    def test_find_organisation_returns_none_when_not_found(self):
        """Test that find_organisation returns None when organisation doesn't exist."""
        row = {"Reference": "NONEXISTENT", "Organisation": "Nonexistent Org"}
        found_org = self.admin.find_organisation(row)

        self.assertIsNone(found_org)

    def test_find_organisation_prefers_reference_over_name(self):
        """Test that find_organisation prefers reference over name when both are present."""
        org_by_ref = Organisation.objects.create(name="Org By Ref", reference="ORG001")
        Organisation.objects.create(name="Org By Name")

        row = {"Reference": "ORG001", "Organisation": "Org By Name"}
        found_org = self.admin.find_organisation(row)

        # Should find by reference, not name
        self.assertEqual(found_org, org_by_ref)

    def test_import_csv_sets_organisation_type_when_provided(self):
        """Test that import_csv sets organisation_type when valid type is provided."""
        csv_data = [
            {
                "Reference": "ORG001",
                "Type": "Ministerial department",
                "Organisation": "Test Ministry",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Check organisation was created with correct type
        org = Organisation.objects.get(name="Test Ministry")
        self.assertEqual(org.organisation_type, "ministerial-department")

    def test_import_csv_ignores_invalid_organisation_type(self):
        """Test that import_csv creates organisation without type when invalid type is provided."""
        csv_data = [
            {
                "Reference": "ORG003",
                "Type": "Invalid Type",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        # Organisation should be created but with no type set
        org = Organisation.objects.get(name="Test Organisation")
        self.assertIsNone(org.organisation_type)

    def test_import_csv_handles_empty_type_field(self):
        """Test that import_csv creates organisation without type when type field is empty."""
        csv_data = [
            {
                "Reference": "ORG004",
                "Type": "",
                "Organisation": "Test Organisation",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        org = Organisation.objects.get(name="Test Organisation")
        self.assertIsNone(org.organisation_type)

    def test_import_csv_handles_whitespace_in_type(self):
        """Test that import_csv strips whitespace from type field."""
        csv_data = [
            {
                "Reference": "ORG005",
                "Type": "  Executive agency  ",
                "Organisation": "Test Agency",
                "Lead Government Department": "",
                "Email1": "user@test.gov.uk",
                "Email2": "",
                "Email3": "",
                "Email4": "",
                "Email5": "",
                "Email6": "",
            }
        ]

        csv_file = self.create_csv_file(csv_data)
        request = self.factory.post("/admin/webcaf/organisation/import-org-csv/", {"csv_file": csv_file})
        request.user = self.superuser

        self.admin.import_csv(add_middleware(request))

        org = Organisation.objects.get(name="Test Agency")
        self.assertEqual(org.organisation_type, "executive-agency")
