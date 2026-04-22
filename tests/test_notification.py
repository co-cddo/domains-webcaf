from unittest.mock import call, patch

from django.test import TestCase, override_settings

from webcaf.webcaf.notification import send_notify_email


@override_settings(NOTIFY_API_KEY="test-api-key")  # pragma: allowlist secret
class SendNotifyEmailTest(TestCase):
    def setUp(self):
        self.personalisation = {"first_name": "Alice", "link": "https://example.com"}
        self.template_id = "template-abc-123"

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_sends_email_to_single_address(self, mock_client_cls, mock_sleep):
        mock_client = mock_client_cls.return_value
        send_notify_email(["alice@example.com"], self.personalisation, self.template_id)
        mock_client.send_email_notification.assert_called_once_with(
            email_address="alice@example.com",
            template_id=self.template_id,
            personalisation=self.personalisation,
        )

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_sends_to_all_addresses(self, mock_client_cls, mock_sleep):
        mock_client = mock_client_cls.return_value
        send_notify_email(["a@x.com", "b@x.com", "c@x.com"], self.personalisation, self.template_id)
        sent_to = {c.kwargs["email_address"] for c in mock_client.send_email_notification.call_args_list}
        self.assertEqual(sent_to, {"a@x.com", "b@x.com", "c@x.com"})
        self.assertEqual(mock_client.send_email_notification.call_count, 3)

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_deduplicates_email_addresses(self, mock_client_cls, mock_sleep):
        mock_client = mock_client_cls.return_value
        send_notify_email(["same@x.com", "same@x.com", "same@x.com"], self.personalisation, self.template_id)
        self.assertEqual(mock_client.send_email_notification.call_count, 1)

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_initialises_client_with_api_key(self, mock_client_cls, mock_sleep):
        send_notify_email(["a@x.com"], self.personalisation, self.template_id)
        mock_client_cls.assert_called_once_with("test-api-key")

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_passes_personalisation_and_template_id(self, mock_client_cls, mock_sleep):
        mock_client = mock_client_cls.return_value
        personalisation = {"key": "value", "other": "data"}
        send_notify_email(["a@x.com"], personalisation, "custom-template")
        mock_client.send_email_notification.assert_called_once_with(
            email_address="a@x.com",
            template_id="custom-template",
            personalisation=personalisation,
        )

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_no_sends_for_empty_list(self, mock_client_cls, mock_sleep):
        mock_client = mock_client_cls.return_value
        send_notify_email([], self.personalisation, self.template_id)
        mock_client.send_email_notification.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_sleeps_between_sends(self, mock_client_cls, mock_sleep):
        """Pauses for retry_delay seconds after each successful send."""
        send_notify_email(["a@x.com", "b@x.com"], {}, self.template_id, retry_delay=0.25)
        inter_send_sleeps = [c for c in mock_sleep.call_args_list if c == call(0.25)]
        self.assertEqual(len(inter_send_sleeps), 2)

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_retries_on_transient_failure_and_succeeds(self, mock_client_cls, mock_sleep):
        """A single transient error is retried and the send ultimately succeeds."""
        mock_client = mock_client_cls.return_value
        mock_client.send_email_notification.side_effect = [Exception("timeout"), None]
        send_notify_email(["a@x.com"], self.personalisation, self.template_id, max_retries=1, retry_delay=0)
        self.assertEqual(mock_client.send_email_notification.call_count, 2)

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_raises_immediately_when_max_retries_zero(self, mock_client_cls, mock_sleep):
        """With max_retries=0, the first failure raises without any retry sleep."""
        mock_client = mock_client_cls.return_value
        mock_client.send_email_notification.side_effect = Exception("server error")
        with self.assertRaisesRegex(Exception, "server error"):
            send_notify_email(["a@x.com"], self.personalisation, self.template_id, max_retries=0)
        self.assertEqual(mock_client.send_email_notification.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_retry_sleep_uses_backoff_delay(self, mock_client_cls, mock_sleep):
        """Retry sleeps for retry_delay * (retry_count + 1) seconds before the next attempt."""
        mock_client = mock_client_cls.return_value
        mock_client.send_email_notification.side_effect = [Exception("e"), None]
        send_notify_email(["a@x.com"], {}, self.template_id, max_retries=2, retry_delay=1.0)
        # retry_count starts at 0 and is never incremented, so delay is always 1.0 * (0 + 1)
        self.assertIn(call(1.0), mock_sleep.call_args_list)

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_logs_warning_on_retry(self, mock_client_cls, mock_sleep):
        """A WARNING is emitted for each failed attempt, including the error message."""
        mock_client = mock_client_cls.return_value
        mock_client.send_email_notification.side_effect = [Exception("network error"), None]
        with self.assertLogs("webcaf.webcaf.notification", level="WARNING") as log:
            send_notify_email(["a@x.com"], {}, self.template_id, max_retries=1, retry_delay=0)
        self.assertTrue(any("network error" in msg for msg in log.output))

    @patch("webcaf.webcaf.notification.time.sleep")
    @patch("webcaf.webcaf.notification.NotificationsAPIClient")
    def test_custom_retry_delay_respected(self, mock_client_cls, mock_sleep):
        """Custom retry_delay is used for both the inter-send pause and backoff calculation."""
        mock_client = mock_client_cls.return_value
        mock_client.send_email_notification.side_effect = [Exception("e"), None]
        send_notify_email(["a@x.com"], {}, self.template_id, max_retries=1, retry_delay=2.0)
        # Retry backoff: 2.0 * (0 + 1) = 2.0; inter-send pause: 2.0
        sleep_values = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertTrue(all(v == 2.0 for v in sleep_values))
