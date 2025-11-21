from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Assessor, Organisation, Review, System


class ReviewModelTests(BaseViewTest):
    """
    Verifies that Review.save() correctly populates initial system_details and
    assessor_details in review_data when a Review is created in status "to_do".

    Also verifies that when status is not "to_do":
    - no automatic population occurs, and
    - any pre-existing review_data is preserved unchanged, and
    - subsequent saves do not mutate previously populated details.
    """

    @classmethod
    def setUpTestData(cls):
        # Reuse the shared test data setup pattern from views tests
        BaseViewTest.setUpTestData()

        # Organisation
        cls.org = Organisation.objects.create(name="Test Org")

        # System (include fields referenced by Review.save)
        cls.system = System.objects.create(
            name="Core Payroll",
            description="Handles payroll",
            organisation=cls.org,
            last_assessed="assessed_in_2425",
            hosting_type=["hosted_on_cloud"],
            corporate_services=["payroll"],
        )

        # Assessment with values used in Review.save
        cls.assessment = Assessment.objects.create(
            system=cls.system,
            assessment_period="2024/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

        # Assessor
        cls.assessor = Assessor.objects.create(
            name="Acme Assurance Ltd",
            contact_name="Jane Doe",
            email="assessor@example.com",
            address="1 High St, London",
            phone_number="0123456789",
        )

    def test_review_save_populates_initial_system_and_assessor_details(self):
        # Review in 'to_do' status so initial data is populated on save
        review = Review.objects.create(
            assessment=self.assessment,
            status="to_do",
            assigned_to=self.assessor,
        )

        # Refresh from DB to ensure JSON saved
        review.refresh_from_db()

        # Expected system details
        expected_system_details = {
            "reference": self.assessment.reference,
            "organisation": self.org.name,
            "assessment_period": self.assessment.assessment_period,
            "name": self.system.name,
            "description": self.system.description,
            "prev_assessments": self.system.last_assessed,
            "hosting_and_connectivity": self.system.hosting_type,
            "corporate_services": self.system.corporate_services,
        }

        self.assertIn("system_details", review.review_data)
        self.assertEqual(review.review_data["system_details"], expected_system_details)

        # Assessor details
        assessor_details = review.review_data.get("assessor_details", {})

        self.assertEqual(assessor_details.get("review_type"), self.assessment.review_type)
        self.assertEqual(assessor_details.get("framework"), self.assessment.framework)
        self.assertEqual(assessor_details.get("profile"), self.assessment.caf_profile)

        # The 'assessor' value is a multi-line string; verify key identifiers are present
        assessor_str = assessor_details.get("assessor") or ""
        # Normalize whitespace for robust comparison
        normalized = " ".join(assessor_str.split())
        self.assertIn("Acme Assurance Ltd", normalized)
        self.assertIn("Jane Doe", normalized)
        self.assertIn("0123456789", normalized)
        self.assertIn("assessor@example.com", normalized)

    def test_no_population_when_status_not_to_do_on_create(self):
        # Create a review with a non-"to_do" status
        review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            assigned_to=self.assessor,
        )
        review.refresh_from_db()

        # Ensure review_data remains empty and has no populated sections
        self.assertIsInstance(review.review_data, dict)
        self.assertNotIn("system_details", review.review_data)
        self.assertNotIn("assessor_details", review.review_data)

    def test_preserve_review_data_when_status_not_to_do(self):
        initial_data = {
            "custom": {"a": 1},
            "system_details": {"name": "ShouldNotBeOverwritten"},
            "assessor_details": {"framework": "caf40"},
        }
        review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            assigned_to=self.assessor,
            review_data=initial_data,
        )
        review.refresh_from_db()
        # Should be exactly what we set
        self.assertEqual(review.review_data, initial_data)

    def test_subsequent_saves_do_not_change_details_when_status_changes_from_to_do(self):
        # First, create as to_do so fields are populated
        review = Review.objects.create(
            assessment=self.assessment,
            status="to_do",
            assigned_to=self.assessor,
        )
        review.refresh_from_db()
        original_data = dict(review.review_data)  # shallow copy is fine for equality checks

        # Now mutate related models to simulate changes after initial population
        self.system.name = "Core Payroll v2"
        self.system.save()
        self.assessment.framework = "caf40"
        self.assessment.caf_profile = "enhanced"
        self.assessment.assessment_period = "2025/26"
        self.assessment.save()

        # Change review status away from to_do and save
        review.status = "in_progress"
        review.save()
        review.refresh_from_db()

        # Ensure the previously populated details remain unchanged
        self.assertEqual(review.review_data, original_data)
