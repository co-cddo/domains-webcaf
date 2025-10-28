from unittest.mock import patch

from django.urls import reverse_lazy
from django_otp import DEVICE_ID_SESSION_KEY

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import GovNotifyEmailDevice


class Verify2FATokenViewTests(BaseViewTest):
    """
    Test suite for the Verify2FATokenView.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

    def setUp(self):
        """
        Set up a test user and log them in for all tests.
        """

        self.client.force_login(self.test_user)

        self.verify_url = reverse_lazy("verify-2fa-token")

        # This is the URL the view redirects to on success
        self.success_url = reverse_lazy("my-account")

    def _verify_user(self, device: GovNotifyEmailDevice):
        """
        Function to populate device as we mock otp_login we need to manually create the ocnditions required for
        request.user.is_verified() = True so the success_url rediect can be followed and return a 200 response.
        """
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    @patch("webcaf.webcaf.models.GovNotifyEmailDevice.generate_challenge")
    def test_get_creates_device_and_generates_token(self, mock_generate_challenge):
        """
        Test that a GET request creates a new device if one doesn't
        exist and calls generate_challenge.
        """
        self.assertEqual(GovNotifyEmailDevice.objects.count(), 0)

        response = self.client.get(self.verify_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/verify-2fa-token.html")

        # Check that a new device was created
        self.assertEqual(GovNotifyEmailDevice.objects.count(), 1)
        device = GovNotifyEmailDevice.objects.first()
        self.assertEqual(device.user, self.test_user)
        self.assertEqual(device.email, self.test_user.email)

        # Check that the token was generated
        mock_generate_challenge.assert_called_once()

    @patch("webcaf.webcaf.models.GovNotifyEmailDevice.generate_challenge")
    def test_get_uses_existing_device_and_generates_token(self, mock_generate_challenge):
        """
        Test that a GET request uses an existing device and calls
        generate_challenge.
        """
        # Create the device beforehand
        GovNotifyEmailDevice.objects.create(user=self.test_user, email=self.test_user.email)
        self.assertEqual(GovNotifyEmailDevice.objects.count(), 1)

        response = self.client.get(self.verify_url)

        self.assertEqual(response.status_code, 200)

        # Check that no new device was created
        self.assertEqual(GovNotifyEmailDevice.objects.count(), 1)

        # Check that the token was generated on the existing device
        mock_generate_challenge.assert_called_once()

    @patch("webcaf.webcaf.views.two_factor_auth.otp_login")
    @patch("webcaf.webcaf.models.GovNotifyEmailDevice.verify_token", return_value=True)
    def test_post_valid_token_logs_in_and_redirects(self, mock_verify_token, mock_otp_login):
        """
        Test that a POST with a valid token calls verify_token,
        calls otp_login, and redirects to the success URL.
        """
        # Device must exist to be verified against
        device = GovNotifyEmailDevice.objects.create(user=self.test_user, email=self.test_user.email)
        valid_token = "123456"

        response = self.client.post(self.verify_url, {"otp_token": valid_token})

        # Check verification was called
        mock_verify_token.assert_called_once_with(valid_token)

        # Check otp_login was called with the correct request and device
        mock_otp_login.assert_called_once()
        self.assertEqual(mock_otp_login.call_args[0][0].user, self.test_user)  # request
        self.assertEqual(mock_otp_login.call_args[0][1], device)  # device

        # need to manually verify the test user as we've mocked out the otp login
        self._verify_user(device)

        # add user profile id to the session and check for redirect to success URL
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()
        self.assertRedirects(response, expected_url=self.success_url)

    @patch("webcaf.webcaf.views.two_factor_auth.otp_login")
    @patch("webcaf.webcaf.models.GovNotifyEmailDevice.verify_token", return_value=False)
    def test_post_invalid_token_shows_error(self, mock_verify_token, mock_otp_login):
        """
        Test that a POST with an invalid token re-renders the form
        with an "Invalid token" error.
        """
        GovNotifyEmailDevice.objects.create(user=self.test_user, email=self.test_user.email)
        invalid_token = "654321"

        response = self.client.post(self.verify_url, {"otp_token": invalid_token})

        # Check verification was called
        mock_verify_token.assert_called_once_with(invalid_token)

        # Check user was NOT logged in
        mock_otp_login.assert_not_called()

        # Check page re-rendered with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/verify-2fa-token.html")
        self.assertContains(response, "Invalid token")
        self.assertIn("otp_token", response.context["form"].errors)

    @patch("webcaf.webcaf.views.two_factor_auth.otp_login")
    @patch("webcaf.webcaf.models.GovNotifyEmailDevice.verify_token")
    def test_post_empty_token_shows_error(self, mock_verify_token, mock_otp_login):
        """
        Test that a POST with an empty token shows the required field error
        and does not attempt to verify.
        """
        GovNotifyEmailDevice.objects.create(user=self.test_user, email=self.test_user.email)

        response = self.client.post(self.verify_url, {"otp_token": ""})

        # Check verification was NOT called
        mock_verify_token.assert_not_called()

        # Check user was NOT logged in
        mock_otp_login.assert_not_called()

        # Check page re-rendered with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter your 6-digit code.")
        self.assertIn("otp_token", response.context["form"].errors)
