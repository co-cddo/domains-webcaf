"""
Tests for SortedOrganisationFilter in admin.py

This module contains tests for the SortedOrganisationFilter class which is used
to filter and sort querysets by Organisation in Django admin.
"""
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from webcaf.webcaf.admin import SortedOrganisationFilter
from webcaf.webcaf.models import Assessment, Organisation, Review, System, UserProfile


class TestSortedOrganisationFilter(TestCase):
    """Tests for the SortedOrganisationFilter admin filter."""

    def setUp(self):
        self.factory = RequestFactory()
        self.filter = SortedOrganisationFilter(None, {}, None, None)

        # Create test organisations
        self.org_a = Organisation.objects.create(name="Alpha Organisation")
        self.org_b = Organisation.objects.create(name="Beta Organisation")
        self.org_c = Organisation.objects.create(name="Gamma Organisation")

        # Create test users
        self.user_a = User.objects.create_user(username="user_a@test.gov.uk", email="user_a@test.gov.uk")
        self.user_b = User.objects.create_user(username="user_b@test.gov.uk", email="user_b@test.gov.uk")

        # Create test systems
        self.system_a = System.objects.create(name="System A", organisation=self.org_a)
        self.system_b = System.objects.create(name="System B", organisation=self.org_b)

        # Create test assessments
        self.assessment_a = Assessment.objects.create(
            system=self.system_a, status="submitted", assessment_period="25/26", review_type="independent"
        )
        self.assessment_b = Assessment.objects.create(
            system=self.system_b, status="submitted", assessment_period="25/26", review_type="peer_review"
        )

        # Create test reviews
        self.review_a = Review.objects.create(assessment=self.assessment_a)
        self.review_b = Review.objects.create(assessment=self.assessment_b)

        # Create user profiles
        UserProfile.objects.create(user=self.user_a, organisation=self.org_a, role="cyber_advisor")
        UserProfile.objects.create(user=self.user_b, organisation=self.org_b, role="organisation_lead")

    def test_lookups_returns_sorted_organisations(self):
        """Test that lookups returns organisations sorted alphabetically by name."""
        request = self.factory.get("/admin/")
        result = self.filter.lookups(request, None)

        # Should return all organisations sorted by name
        expected = [
            (self.org_a.id, "Alpha Organisation"),
            (self.org_b.id, "Beta Organisation"),
            (self.org_c.id, "Gamma Organisation"),
        ]
        self.assertEqual(result, expected)

    def test_lookups_organisations_are_sorted(self):
        """Test that the organisations returned by lookups are sorted alphabetically."""
        request = self.factory.get("/admin/")
        result = self.filter.lookups(request, None)

        # Extract just the names
        names = [name for _, name in result]
        self.assertEqual(names, sorted(names))

    def test_queryset_filter_by_organisation_direct(self):
        """Test filtering queryset with direct organisation foreign key (UserProfile)."""
        request = self.factory.get("/admin/", query_params={"organisation": self.org_a.id})
        model_admin = admin.site._registry[UserProfile]
        self.filter = SortedOrganisationFilter(
            request, {"organisation": [str(self.org_a.id)]}, UserProfile, model_admin
        )

        queryset = UserProfile.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().organisation, self.org_a)

    def test_queryset_filter_by_system_organisation(self):
        """Test filtering queryset with system__organisation relationship (System)."""
        request = self.factory.get("/admin/", query_params={"organisation": self.org_b.id})
        model_admin = admin.site._registry[System]
        self.filter = SortedOrganisationFilter(request, {"organisation": [str(self.org_b.id)]}, System, model_admin)

        queryset = System.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().organisation, self.org_b)

    def test_queryset_filter_by_assessment_system_organisation(self):
        """Test filtering queryset with assessment__system__organisation relationship (Assessment)."""
        request = self.factory.get("/admin/", {"organisation": self.org_a.id})
        model_admin = admin.site._registry[Assessment]
        self.filter = SortedOrganisationFilter(request, {"organisation": [str(self.org_a.id)]}, Assessment, model_admin)

        queryset = Assessment.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().system.organisation, self.org_a)

    def test_queryset_filter_by_review_assessment_system_organisation(self):
        """Test filtering queryset with assessment__system__organisation relationship (Review)."""
        request = self.factory.get("/admin/", query_params={"organisation": self.org_b.id})
        model_admin = admin.site._registry[Review]
        self.filter = SortedOrganisationFilter(request, {"organisation": [str(self.org_b.id)]}, Review, model_admin)

        queryset = Review.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().assessment.system.organisation, self.org_b)

    def test_queryset_no_filter_value_returns_all(self):
        """Test that when no filter value is provided, all records are returned."""
        request = self.factory.get("/admin/")
        model_admin = admin.site._registry[UserProfile]
        self.filter = SortedOrganisationFilter(request, {}, UserProfile, model_admin)

        queryset = UserProfile.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), UserProfile.objects.count())

    def test_queryset_invalid_filter_value_returns_none(self):
        """Test that when an invalid filter value is provided, all records are returned."""
        request = self.factory.get("/admin/", query_params={"organisation": "999"})
        model_admin = admin.site._registry[UserProfile]
        self.filter = SortedOrganisationFilter(request, {"organisation": "999"}, UserProfile, model_admin)

        queryset = UserProfile.objects.all()
        filtered = self.filter.queryset(request, queryset)

        # Should return 0 since the ID doesn't exist
        self.assertEqual(filtered.count(), 0)

    def test_queryset_filter_multiple_records(self):
        """Test filtering returns multiple records from the same organisation."""
        # Create another user profile for org_a
        user_c = User.objects.create_user(username="user_c@test.gov.uk", email="user_c@test.gov.uk")
        UserProfile.objects.create(user=user_c, organisation=self.org_a, role="assessor")
        model_admin = admin.site._registry[UserProfile]
        request = self.factory.get("/admin/", query_params={"organisation": self.org_a.id})
        self.filter = SortedOrganisationFilter(
            request, {"organisation": [str(self.org_a.id)]}, UserProfile, model_admin
        )

        queryset = UserProfile.objects.all()
        filtered = self.filter.queryset(request, queryset)

        self.assertEqual(filtered.count(), 2)
        for profile in filtered:
            self.assertEqual(profile.organisation, self.org_a)


class TestSortedOrganisationFilterWithAdmin(TestCase):
    """Integration tests for SortedOrganisationFilter with actual admin classes."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create test organisations
        self.org_a = Organisation.objects.create(name="Alpha Organisation")
        self.org_b = Organisation.objects.create(name="Beta Organisation")

        # Create test users
        self.user = User.objects.create_user(username="admin@test.gov.uk", email="admin@test.gov.uk")

        # Create test systems
        self.system_a = System.objects.create(name="System A", organisation=self.org_a)
        self.system_b = System.objects.create(name="System B", organisation=self.org_b)

        # Create test assessments with different review types
        self.assessment_a = Assessment.objects.create(
            system=self.system_a, status="submitted", assessment_period="25/26", review_type="independent"
        )
        self.assessment_b = Assessment.objects.create(
            system=self.system_b, status="submitted", assessment_period="25/26", review_type="peer_review"
        )

        # Create user profiles
        UserProfile.objects.create(user=self.user, organisation=self.org_a, role="cyber_advisor")
        UserProfile.objects.create(user=self.user, organisation=self.org_b, role="organisation_lead")

    def test_user_profile_admin_uses_sorted_organisation_filter(self):
        """Test that UserProfileAdmin uses SortedOrganisationFilter."""

        model_admin = admin.site._registry[UserProfile]
        filter_classes = model_admin.list_filter

        # Check that SortedOrganisationFilter is in the list filters
        self.assertIn(SortedOrganisationFilter, filter_classes)

    def test_system_admin_uses_sorted_organisation_filter(self):
        """Test that SystemAdmin uses SortedOrganisationFilter."""

        model_admin = admin.site._registry[System]
        filter_classes = model_admin.list_filter

        # Check that SortedOrganisationFilter is in the list filters
        self.assertIn(SortedOrganisationFilter, filter_classes)

    def test_assessment_admin_uses_sorted_organisation_filter(self):
        """Test that AssessmentAdmin uses SortedOrganisationFilter."""

        model_admin = admin.site._registry[Assessment]
        filter_classes = model_admin.list_filter

        # Check that SortedOrganisationFilter is in the list filters
        self.assertIn(SortedOrganisationFilter, filter_classes)

    def test_review_admin_uses_sorted_organisation_filter(self):
        """Test that ReviewAdmin uses SortedOrganisationFilter."""

        model_admin = admin.site._registry[Review]
        filter_classes = model_admin.list_filter

        # Check that SortedOrganisationFilter is in the list filters (as string reference or class)
        filter_names = [f if isinstance(f, str) else f.__name__ for f in filter_classes]
        self.assertIn("SortedOrganisationFilter", filter_names)
