# tests/test_session_utils.py
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from webcaf.webcaf.utils.session import SessionUtil


class SessionUtilTests(SimpleTestCase):
    def test_get_current_user_profile_returns_profile(self):
        request = SimpleNamespace(session={"current_profile_id": 42})
        fake_profile = MagicMock()

        with patch("webcaf.webcaf.models.UserProfile.objects.get", return_value=fake_profile) as mock_get:
            result = SessionUtil.get_current_user_profile(request)

        self.assertIs(result, fake_profile)
        mock_get.assert_called_once_with(id=42)

    def test_get_current_user_profile_logs_and_returns_none_on_exception(self):
        request = SimpleNamespace(session={"current_profile_id": 99})

        with patch("webcaf.webcaf.models.UserProfile.objects.get", side_effect=Exception("db error")):
            with self.assertLogs("SessionUtil", level="ERROR") as cm:
                result = SessionUtil.get_current_user_profile(request)

        self.assertIsNone(result)
        self.assertTrue(any("Unable to retrieve user profile with id 99" in m for m in cm.output))

    def test_get_current_assessment_returns_assessment_when_found(self):
        request = SimpleNamespace(session={"draft_assessment": {"assessment_id": 7}})

        # Fake user profile with organisation.id
        fake_org = SimpleNamespace(id=123)
        fake_profile = SimpleNamespace(organisation=fake_org)
        fake_assessment = MagicMock()

        with patch.object(
            SessionUtil, "get_current_user_profile", return_value=fake_profile
        ) as mock_get_profile, patch(
            "webcaf.webcaf.models.Assessment.objects.get", return_value=fake_assessment
        ) as mock_get_assessment:
            result = SessionUtil.get_current_assessment(request)

        self.assertIs(result, fake_assessment)
        mock_get_profile.assert_called_once_with(request)
        mock_get_assessment.assert_called_once_with(
            status="draft",
            id=7,
            system__organisation_id=123,
        )

    def test_get_current_assessment_logs_and_returns_none_on_exception(self):
        request = SimpleNamespace(session={"draft_assessment": {"assessment_id": 55}}, user=MagicMock(username="test"))
        fake_org = SimpleNamespace(id=456)
        fake_profile = SimpleNamespace(organisation=fake_org)

        with patch.object(SessionUtil, "get_current_user_profile", return_value=fake_profile), patch(
            "webcaf.webcaf.models.Assessment.objects.get", side_effect=Exception("not found")
        ):
            with self.assertLogs("SessionUtil", level="ERROR") as cm:
                result = SessionUtil.get_current_assessment(request)

        self.assertIsNone(result)
        self.assertTrue(any("Unable to retrieve assessment with id 55" in m for m in cm.output))

    def test_get_current_assessment_returns_none_when_no_user_profile(self):
        request = SimpleNamespace(session={"draft_assessment": {"assessment_id": 77}})

        with patch.object(SessionUtil, "get_current_user_profile", return_value=None) as mock_get_profile, patch(
            "webcaf.webcaf.models.Assessment.objects.get"
        ) as mock_get_assessment:
            result = SessionUtil.get_current_assessment(request)

        self.assertIsNone(result)
        mock_get_profile.assert_called_once_with(request)
        mock_get_assessment.assert_not_called()
