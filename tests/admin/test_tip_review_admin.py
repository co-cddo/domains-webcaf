"""
Tests for the admin changes in ``webcaf/webcaf/admin.py`` covering:

* ``TipAdmin`` history restore gating — only a superuser may restore a Tip from
  its history; users holding ``can_approve_tip`` / ``can_reject_tip`` can view a
  Tip but must not be able to restore it, and a restore attempt is refused.
* ``ReviewAdmin`` "_reopen" handling — posting ``_reopen`` rolls a completed
  review back to ``in_progress`` and drops the finalise data, and only a
  superuser is allowed to do so.

These tests exercise the admin classes directly with ``RequestFactory`` (fast,
deterministic, no reliance on admin templates) and add a couple of end-to-end
checks against the real history view for the visible "Revert" affordance.
"""

import freezegun
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase

from webcaf.webcaf.admin import ReviewAdmin, TipAdmin
from webcaf.webcaf.models import Assessment, Organisation, Review, System, Tip


def _reload_user(user: User) -> User:
    """Re-fetch a user so the per-instance permission cache is rebuilt.

    ``User.has_perm`` memoises the permission set on the instance, so after
    granting a permission we must reload to see it.
    """
    return User.objects.get(pk=user.pk)


@freezegun.freeze_time("2025-01-01")
class TipAdminHistoryRestoreTests(TestCase):
    """Only superusers may restore a Tip from history (admin.py revert gating)."""

    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(name="Test Organisation")
        cls.system = System.objects.create(name="Test System", organisation=cls.organisation)
        cls.assessment = Assessment.objects.create(
            system=cls.system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )
        cls.review = Review.objects.create(assessment=cls.assessment, status="in_progress")
        cls.tip = Tip.objects.create(review=cls.review)

        # Superuser: full rights, including history restore.
        cls.superuser = User.objects.create_superuser(
            username="admin@test.gov.uk",
            email="admin@test.gov.uk",
            password="pw",  # pragma: allowlist secret
        )

        # Staff user that can approve tips but is NOT a superuser.
        cls.approver = User.objects.create_user(
            username="approver@test.gov.uk", email="approver@test.gov.uk", is_staff=True
        )
        cls.approver.user_permissions.add(Permission.objects.get(codename="can_approve_tip"))
        cls.approver = _reload_user(cls.approver)

        # Staff user that can reject tips but is NOT a superuser.
        cls.rejecter = User.objects.create_user(
            username="rejecter@test.gov.uk", email="rejecter@test.gov.uk", is_staff=True
        )
        cls.rejecter.user_permissions.add(Permission.objects.get(codename="can_reject_tip"))
        cls.rejecter = _reload_user(cls.rejecter)

        # Plain staff user with neither permission.
        cls.plain_staff = User.objects.create_user(
            username="staff@test.gov.uk", email="staff@test.gov.uk", is_staff=True
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.admin = TipAdmin(Tip, AdminSite())

    def _request(self, user, method="get", data=None):
        request = getattr(self.factory, method)("/", data or {})
        request.user = user
        return request

    # --- revert_disabled: the switch that hides the "Revert" button --------

    def test_superuser_can_restore_history(self):
        """A superuser has revert enabled (revert_disabled is False)."""
        request = self._request(self.superuser)
        self.assertFalse(self.admin.revert_disabled(request, self.tip))

    def test_approver_cannot_restore_history(self):
        """A can_approve_tip user has revert disabled."""
        request = self._request(self.approver)
        self.assertTrue(self.admin.revert_disabled(request, self.tip))

    def test_rejecter_cannot_restore_history(self):
        """A can_reject_tip user has revert disabled."""
        request = self._request(self.rejecter)
        self.assertTrue(self.admin.revert_disabled(request, self.tip))

    def test_plain_staff_cannot_restore_history(self):
        """A non-superuser without approve/reject perms has revert disabled."""
        request = self._request(self.plain_staff)
        self.assertTrue(self.admin.revert_disabled(request, self.tip))

    # --- has_change_history_permission mirrors revert_disabled -------------

    def test_has_change_history_permission_follows_revert_disabled(self):
        """``has_change_history_permission`` delegates to ``revert_disabled``."""
        for user in (self.superuser, self.approver, self.rejecter, self.plain_staff):
            with self.subTest(user=user.username):
                request = self._request(user)
                self.assertEqual(
                    self.admin.has_change_history_permission(request, self.tip),
                    self.admin.revert_disabled(request, self.tip),
                )

    # --- the "permission error" a restore POST would hit ------------------

    def test_approver_restore_post_is_denied_by_change_permission(self):
        """
        A history restore is a change POST without ``_approve``/``_reject``.
        For an approve/reject user that POST is refused by
        ``has_change_permission`` — the permission error described in the spec.
        """
        for user in (self.approver, self.rejecter):
            with self.subTest(user=user.username):
                post = self._request(user, method="post", data={"_save": "Revert"})
                self.assertFalse(self.admin.has_change_permission(post, self.tip))

    def test_approver_may_still_view_tip(self):
        """The approve/reject users retain view access to the Tip admin."""
        for user in (self.approver, self.rejecter):
            with self.subTest(user=user.username):
                request = self._request(user)
                self.assertTrue(self.admin.has_view_permission(request, self.tip))

    def test_superuser_restore_post_is_allowed(self):
        """A superuser is not blocked from a restore/change POST."""
        post = self._request(self.superuser, method="post", data={"_save": "Revert"})
        self.assertTrue(self.admin.has_change_permission(post, self.tip))


@freezegun.freeze_time("2025-01-01")
class ReviewAdminReopenTests(TestCase):
    """``ReviewAdmin.save_model`` "_reopen" rollback behaviour (admin.py)."""

    assessment: Assessment

    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(name="Reopen Organisation")
        cls.system = System.objects.create(name="Reopen System", organisation=cls.organisation)
        cls.assessment = Assessment.objects.create(
            system=cls.system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )
        cls.superuser = User.objects.create_superuser(
            username="reopen-admin@test.gov.uk",
            email="reopen-admin@test.gov.uk",
            password="pw",  # pragma: allowlist secret
        )
        cls.staff = User.objects.create_user(
            username="reopen-staff@test.gov.uk", email="reopen-staff@test.gov.uk", is_staff=True
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.admin = ReviewAdmin(Review, AdminSite())

    def _completed_finalised_review(self) -> Review:
        """Create a review that is completed and finalised.

        Creating with ``status="completed"`` on a fresh instance is allowed —
        the model's "cannot change after completed" guard only fires on update.
        """
        return Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "review_completion": {"review_completed": "yes", "review_completed_at": "2026-01-01T00:00:00"},
                "review_finalised": {"review_finalised_by": "Someone"},
                "assessor_response_data": {"A": {}},
            },
        )

    def _post(self, user, data):
        request = self.factory.post("/admin/webcaf/review/1/change/", data)
        request.user = user
        return request

    def test_superuser_reopen_rolls_back_to_in_progress(self):
        """Posting ``_reopen`` as a superuser reopens the review and drops finalise data."""
        review = self._completed_finalised_review()
        request = self._post(self.superuser, {"_reopen": "Reopen"})

        self.admin.save_model(request, review, form=None, change=True)

        review.refresh_from_db()
        self.assertEqual(review.status, "in_progress")
        self.assertNotIn("review_finalised", review.review_data)
        self.assertNotIn("review_completion", review.review_data)
        # Assessor answers are preserved — only the finalise/completion markers go.
        self.assertIn("assessor_response_data", review.review_data)
        self.assertEqual(review.last_updated_by, self.superuser)

    def test_non_superuser_reopen_raises_permission_denied(self):
        """A non-superuser posting ``_reopen`` is refused and the review is untouched."""
        review = self._completed_finalised_review()
        request = self._post(self.staff, {"_reopen": "Reopen"})

        with self.assertRaises(PermissionDenied):
            self.admin.save_model(request, review, form=None, change=True)

        review.refresh_from_db()
        self.assertEqual(review.status, "completed")
        self.assertIn("review_finalised", review.review_data)

    def test_rollback_requires_completed_status(self):
        """The model guard rejects reopening a review that is not completed."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress")
        with self.assertRaises(ValidationError):
            review.rollback_to_in_progress()
