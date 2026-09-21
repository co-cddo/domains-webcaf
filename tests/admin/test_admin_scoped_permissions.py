"""
Tests for the role-based scoped visibility and permission changes in
``webcaf/webcaf/admin.py``.

These tests verify that ``get_organisations`` and the various Admin
``get_queryset`` overrides return the correct records for:
- superusers (everything),
- "admin" group members (everything),
- "cyber advisor" group members (only their associated organisation(s)),
- users with no matching role (nothing).
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.test import RequestFactory, TestCase

from webcaf.webcaf.admin import (
    AssessmentAdmin,
    OrganisationAdmin,
    ReviewAdmin,
    ScopedUserAdmin,
    SystemAdmin,
    TipAdmin,
    get_organisations,
)
from webcaf.webcaf.models import (
    Assessment,
    Organisation,
    Review,
    System,
    Tip,
    UserAssociation,
    UserProfile,
)


def create_role_user(group_name: str, is_superuser: bool = False) -> User:
    """Create (or reuse) a staff user in the given role group.

    For ``is_superuser=True`` a superuser is returned.
    The group is created if it does not already exist.
    """
    if is_superuser:
        try:
            return User.objects.get(username="super")
        except User.DoesNotExist:
            return User.objects.create_superuser(
                username="super",
                email="super@test.gov.uk",
                password="pw",  # pragma: allowlist secret
            )

    group, _ = Group.objects.get_or_create(name=group_name)

    if group_name == "cyber advisor":
        model_list: list[type[Model]] = [Review, Assessment, Organisation, System, User, Tip]
        for m in model_list:
            content_type = ContentType.objects.get_for_model(m)
            permission = Permission.objects.get(
                content_type=content_type,
                codename=f"view_{m.__name__.lower()}",
            )
            group.permissions.add(permission)

    username = {
        "admin": "admin",
        "cyber advisor": "cyber_backend",
    }[group_name]

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            email=username,
            is_staff=True,
            password="pw",  # pragma: allowlist secret
        )
    user.groups.add(group)
    return user


def create_sample_data() -> dict:
    """Create two full sets of test data (org, system, assessment, review, tip)
    plus a cyber-advisor UserProfile + UserAssociation pair.

    Returns a dict of the created objects so callers can attach them to
    their class if desired.
    """
    org1 = Organisation.objects.create(name="Test Org 1")
    org2 = Organisation.objects.create(name="Test Org 2")

    system1 = System.objects.create(name="Test System 1", organisation=org1)
    system2 = System.objects.create(name="Test System 2", organisation=org2)

    assessment1 = Assessment.objects.create(
        system=system1,
        assessment_period="24/25",
        framework="caf32",
        caf_profile="baseline",
        review_type="independent",
    )
    assessment2 = Assessment.objects.create(
        system=system2,
        assessment_period="24/25",
        framework="caf32",
        caf_profile="baseline",
        review_type="independent",
    )

    review1 = Review.objects.create(assessment=assessment1, status="in_progress")
    review2 = Review.objects.create(assessment=assessment2, status="in_progress")

    tip1 = Tip.objects.create(review=review1)
    tip2 = Tip.objects.create(review=review2)

    # Cyber-advisor association data (backend user will be linked in role tests)
    frontend_user = User.objects.create_user(
        username="frontend_cyber@test.gov.uk",
        email="frontend_cyber@test.gov.uk",
    )
    cyber_profile = UserProfile.objects.create(user=frontend_user, organisation=org1, role="cyber_advisor")
    # A placeholder backend user for the association (real cyber role user created per test)
    cyber_backend = User.objects.create_user(
        username="cyber_backend",
        email="cyber_backend@test.gov.uk",
        is_staff=True,
    )
    association = UserAssociation.objects.create(backend_user=cyber_backend, frontend_user=frontend_user)

    return {
        "org1": org1,
        "org2": org2,
        "system1": system1,
        "system2": system2,
        "assessment1": assessment1,
        "assessment2": assessment2,
        "review1": review1,
        "review2": review2,
        "tip1": tip1,
        "tip2": tip2,
        "cyber_profile": cyber_profile,
        "cyber_association": association,
        "cyber_frontend": frontend_user,
        "cyber_backend": cyber_backend,
    }


class AdminScopedPermissionTests(TestCase):
    """Base class providing the role-user and sample-data helpers."""

    @classmethod
    def setUpTestData(cls):
        cls.sample = create_sample_data()
        # Attach sample objects as direct class attributes for convenience
        for key, value in cls.sample.items():
            setattr(cls, key, value)

    @classmethod
    def create_role_user(cls, role: str, is_superuser: bool = False) -> User:
        return create_role_user(role, is_superuser)

    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()


class GetOrganisationsTests(AdminScopedPermissionTests):
    """Tests for the ``get_organisations`` helper function."""

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_returns_all_orgs(self):
        """Superuser sees both organisations."""
        user = self.create_role_user("ignored", is_superuser=True)
        request = self._request(user)
        orgs = get_organisations(request)
        self.assertEqual(orgs.count(), 2)

    def test_admin_group_returns_all_orgs(self):
        """Admin group member sees both organisations."""
        user = self.create_role_user("admin")
        request = self._request(user)
        orgs = get_organisations(request)
        self.assertEqual(orgs.count(), 2)

    def test_cyber_advisor_returns_only_associated_orgs(self):
        """Cyber advisor sees only the organisation linked via their profile."""
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        orgs = get_organisations(request)
        self.assertEqual(orgs.count(), 1)
        self.assertEqual(orgs.first()["organisation__id"], self.org1.id)

    def test_non_matching_user_returns_empty(self):
        """User with no recognised role sees no organisations."""
        user = User.objects.create_user(
            username="plain@test.gov.uk",
            email="plain@test.gov.uk",
            is_staff=True,
        )
        request = self._request(user)
        orgs = get_organisations(request)
        self.assertEqual(len(orgs), 0)


class ScopedUserAdminTests(AdminScopedPermissionTests):
    """Tests that ScopedUserAdmin.get_queryset respects role scoping."""

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_sees_all_users(self):
        user = self.create_role_user("ignored", is_superuser=True)
        request = self._request(user)
        admin = ScopedUserAdmin(User, self.site)
        qs = admin.get_queryset(request)
        # We have the role users + sample cyber users + plain ones created
        self.assertGreaterEqual(qs.count(), 2)

    def test_admin_group_sees_all_users(self):
        user = self.create_role_user("admin")
        request = self._request(user)
        admin = ScopedUserAdmin(User, self.site)
        qs = admin.get_queryset(request)
        self.assertGreaterEqual(qs.count(), 2)

    def test_cyber_advisor_sees_only_associated_users(self):
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        admin = ScopedUserAdmin(User, self.site)
        qs = admin.get_queryset(request)
        # Should see the frontend user linked to org1 (and possibly self if profile exists)
        self.assertGreaterEqual(qs.count(), 1)
        self.assertIn(self.cyber_frontend.id, qs.values_list("id", flat=True))

    def test_non_matching_user_sees_empty(self):
        user = User.objects.create_user(
            username="plain2@test.gov.uk",
            email="plain2@test.gov.uk",
            is_staff=True,
        )
        request = self._request(user)
        admin = ScopedUserAdmin(User, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), 0)


class OrganisationSystemAdminTests(AdminScopedPermissionTests):
    """Tests for OrganisationAdmin and SystemAdmin queryset scoping."""

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def _test_admin_queryset(self, admin_class, model, all_count, cyber_count, other_obj):
        # superuser
        user = self.create_role_user("ignored", is_superuser=True)
        request = self._request(user)
        admin = admin_class(model, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), all_count)
        self.assertIn(other_obj, qs)

        # admin group
        user = self.create_role_user("admin")
        request = self._request(user)
        admin = admin_class(model, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), all_count)
        self.assertIn(other_obj, qs)

        # cyber advisor (associated with org1)
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        admin = admin_class(model, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), cyber_count)
        self.assertNotIn(other_obj, qs)  # other org's object excluded

        # non-matching
        user = User.objects.create_user(
            username="plain3@test.gov.uk",
            email="plain3@test.gov.uk",
            is_staff=True,
        )
        request = self._request(user)
        admin = admin_class(model, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), 0)

    def test_organisation_admin(self):
        self._test_admin_queryset(OrganisationAdmin, Organisation, 2, 1, self.org2)

    def test_system_admin(self):
        self._test_admin_queryset(SystemAdmin, System, 2, 1, self.system2)


class AssessmentReviewTipAdminTests(AdminScopedPermissionTests):
    """Tests for AssessmentAdmin, ReviewAdmin and TipAdmin queryset scoping."""

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def _test_admin_queryset(self, admin_class, model, all_count, cyber_count, other_obj):

        with self.subTest("test superuser access"):
            # superuser
            user = self.create_role_user("ignored", is_superuser=True)
            request = self._request(user)
            admin = admin_class(model, self.site)
            qs = admin.get_queryset(request)
            self.assertEqual(qs.count(), all_count)
            self.assertIn(other_obj, qs)
        with self.subTest("test admin group access"):
            # admin group
            user = self.create_role_user("admin")
            request = self._request(user)
            admin = admin_class(model, self.site)
            qs = admin.get_queryset(request)
            self.assertEqual(qs.count(), all_count)
            self.assertIn(other_obj, qs)

        with self.subTest("test cyber advisor access"):
            # cyber advisor (associated with org1)
            user = self.create_role_user("cyber advisor")
            request = self._request(user)
            admin = admin_class(model, self.site)
            qs = admin.get_queryset(request)
            self.assertEqual(qs.count(), cyber_count)
            self.assertNotIn(other_obj, qs)

        with self.subTest("test non-matching access"):
            # non-matching
            user = User.objects.create_user(
                username="plain4@test.gov.uk",
                email="plain4@test.gov.uk",
                is_staff=True,
            )
            request = self._request(user)
            admin = admin_class(model, self.site)
            qs = admin.get_queryset(request)
            self.assertEqual(qs.count(), 0)

    def test_assessment_admin(self):
        self._test_admin_queryset(AssessmentAdmin, Assessment, 2, 1, self.assessment2)

    def test_review_admin(self):
        self._test_admin_queryset(ReviewAdmin, Review, 2, 1, self.review2)

    def test_tip_admin(self):
        self._test_admin_queryset(TipAdmin, Tip, 2, 1, self.tip2)


class CyberAdvisorReadOnlyTests(AdminScopedPermissionTests):
    """Tests that cyber-advisor users are limited to read-only on Tip (and similar)."""

    def _request(self, user, method="get", data=None):
        request = getattr(self.factory, method)("/", data or {})
        request.user = user
        return request

    def test_cyber_advisor_get_form_sets_tip_data_readonly(self):
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        admin = TipAdmin(Tip, self.site)
        form_cls = admin.get_form(request)
        form = form_cls()
        self.assertTrue(
            form.base_fields["tip_data"].widget.attrs.get("readonly"),
            "tip_data should be readonly for non-superuser cyber advisor",
        )

    def test_cyber_advisor_has_change_permission_false_for_plain_post(self):
        user = self.create_role_user("cyber advisor")
        request = self._request(user, method="post")
        admin = TipAdmin(Tip, self.site)
        self.assertFalse(admin.has_change_permission(request))

    def test_cyber_advisor_has_view_permission_true(self):
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        admin = TipAdmin(Tip, self.site)
        self.assertTrue(admin.has_view_permission(request))

    def test_cyber_advisor_can_still_list_and_view_via_get_queryset_for_their_orgs(self):
        """
        Only one tip (org1) should be visible to cyber advisor.
        :return:
        """
        user = self.create_role_user("cyber advisor")
        request = self._request(user)
        admin = TipAdmin(Tip, self.site)
        qs = admin.get_queryset(request)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.tip1)
