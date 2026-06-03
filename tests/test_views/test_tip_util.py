from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    Review,
    System,
    Tip,
    UserProfile,
)
from webcaf.webcaf.tip.util import BaseTipMixin


class TestGetTipForUserIntegration(TestCase):
    def setUp(self):
        self.mixin = BaseTipMixin()
        self.org1 = Organisation.objects.create(name="Org 1")
        self.org2 = Organisation.objects.create(name="Org 2")

        self.user1 = User.objects.create_user(username="user1@org1.com")
        self.profile1 = UserProfile.objects.create(user=self.user1, organisation=self.org1, role="organisation_lead")

        self.config = Configuration.objects.create(name="Default Config")

        # System and Assessment for Org 1 (Submitted and Finalised)
        self.system1 = System.objects.create(name="System 1", organisation=self.org1)
        self.assessment1 = Assessment.objects.create(system=self.system1, status="submitted", assessment_period="25/26")
        self.review1 = Review.objects.create(assessment=self.assessment1, status="completed")
        self.review1.review_data = {"review_finalised": {"review_finalised_at": "2026-05-14T11:15:00"}}
        self.review1.save()
        self.tip1 = Tip.objects.create(review=self.review1, reference="TIP001")

        # System and Assessment for Org 1 (Submitted but Not Finalised)
        self.assessment_not_finalised = Assessment.objects.create(
            system=self.system1, status="submitted", assessment_period="24/25"
        )
        self.review_not_finalised = Review.objects.create(assessment=self.assessment_not_finalised)
        # review_data is empty by default, so review_finalised_at will be None
        self.tip_not_finalised = Tip.objects.create(review=self.review_not_finalised, reference="TIP003")

        # System and Assessment for Org 2
        self.system2 = System.objects.create(name="System 2", organisation=self.org2)
        self.assessment2 = Assessment.objects.create(system=self.system2, status="submitted", assessment_period="25/26")
        self.review2 = Review.objects.create(assessment=self.assessment2)
        self.review2.review_data = {"review_finalised": {"review_finalised_at": "2026-05-14T11:15:00"}}
        self.review2.save()
        self.tip2 = Tip.objects.create(review=self.review2, reference="TIP004")

    def test_get_tip_for_user_filters_correctly(self):
        """
        Test that get_tip_for_user returns only finalised tips for the user's organisation.
        """
        tips = self.mixin.get_tip_for_user(self.profile1, self.config)

        # Should include tip1 (Org 1, Submitted, Finalised)
        self.assertIn(self.tip1, tips)

        # Should NOT include tip_not_finalised (Not Finalised)
        self.assertNotIn(self.tip_not_finalised, tips)

        # Should NOT include tip2 (Different Org)
        self.assertNotIn(self.tip2, tips)

        self.assertEqual(tips.count(), 1)

    def test_get_tip_for_user_no_profile(self):
        """
        Test that get_tip_for_user raises PermissionDenied if user_profile is None.
        """
        with self.assertRaisesMessage(PermissionDenied, "User profile not found"):
            self.mixin.get_tip_for_user(None, self.config)
