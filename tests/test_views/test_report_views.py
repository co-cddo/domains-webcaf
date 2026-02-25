"""
Tests for webcaf/webcaf/views/assessor/review.py

This module contains tests for the review view classes, specifically:
- ShowReportView.get_template_names() - template selection based on review type
- DownloadReport - PDF generation with correct template selection
"""
import json
from pathlib import Path

from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from webcaf.webcaf.models import Assessment, Review
from webcaf.webcaf.views.assessor.review import DownloadReport

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_assessment_base.json"
REVIEW_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_review.json"


class TestDownloadReportTemplateSelection(TestCase):
    """Tests for DownloadReport template selection."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import Organisation, System, UserProfile

        cls.org = Organisation.objects.create(name="Test Organisation")
        cls.system = System.objects.create(name="Test System", organisation=cls.org)
        cls.system_2 = System.objects.create(name="Test System 2", organisation=cls.org)
        cls.user = User.objects.create_user(username="test@test.gov.uk", email="test@test.gov.uk")
        cls.user_profile = UserProfile.objects.create(user=cls.user, organisation=cls.org, role="cyber_advisor")

        with open(FIXTURE_PATH, "r") as f:
            base_assessment = json.load(f)

        with open(REVIEW_FIXTURE_PATH, "r") as f:
            base_review = json.load(f)

        # Create peer review assessment
        cls.peer_review_assessment = Assessment.objects.create(
            system=cls.system,
            status="submitted",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.peer_review = Review.objects.create(
            assessment=cls.peer_review_assessment,
            status="completed",
            review_data=base_review,
        )

        # Create independent review assessment
        cls.independent_assessment = Assessment.objects.create(
            system=cls.system_2,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.independent_review = Review.objects.create(
            assessment=cls.independent_assessment,
            status="completed",
            review_data=base_review,
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.client.force_login(self.user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()

    def test_download_report_peer_review_template(self):
        """Test DownloadReport template selection for peer review."""
        view = DownloadReport()
        view.object = self.peer_review
        request = self.factory.get(f"review/{self.peer_review.id}/<int:version>/download-report/")
        request.session = self.client.session
        view.request = request
        view.kwargs = {"pk": self.peer_review.id}

        templates = view.get_template_names()
        self.assertEqual(templates[0], "review/peer-review-report.html")

    def test_download_report_independent_review_template(self):
        """Test DownloadReport template selection for independent review."""
        view = DownloadReport()
        view.object = self.independent_review
        request = self.factory.get(f"review/{self.independent_review.id}/<int:version>/download-report/")
        request.session = self.client.session
        view.request = request
        view.kwargs = {"pk": self.independent_review.id}
        templates = view.get_template_names()
        self.assertEqual(templates[0], "review/review-report.html")


class TestDownloadExcelReportView(TestCase):
    """Tests for DownloadExcelReport view."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import Organisation, System, UserProfile

        cls.org = Organisation.objects.create(name="Test Organisation")
        cls.system = System.objects.create(name="Test System", organisation=cls.org)
        cls.user = User.objects.create_user(username="test@test.gov.uk", email="test@test.gov.uk")
        cls.user_profile = UserProfile.objects.create(user=cls.user, organisation=cls.org, role="cyber_advisor")

        with open(FIXTURE_PATH, "r") as f:
            base_assessment = json.load(f)

        with open(REVIEW_FIXTURE_PATH, "r") as f:
            base_review = json.load(f)

        # Create peer review assessment
        cls.peer_review_assessment = Assessment.objects.create(
            system=cls.system,
            status="submitted",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.peer_review = Review.objects.create(
            assessment=cls.peer_review_assessment,
            status="completed",
            review_data=base_review,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()

    def test_download_excel_report_peer_review(self):
        """Test downloading Excel report for peer review."""
        url = reverse("download-excel-report", kwargs={"pk": self.peer_review.id, "version": 1})
        response = self.client.get(url)

        # Should return Excel file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("Content-Disposition", response)

    def test_download_excel_report_returns_excel_content_type(self):
        """Test that Excel download returns correct content type."""
        url = reverse("download-excel-report", kwargs={"pk": self.peer_review.id, "version": 1})
        response = self.client.get(url)

        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
