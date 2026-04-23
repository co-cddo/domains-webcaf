import logging
import time

from django.conf import settings
from notifications_python_client import NotificationsAPIClient

logger = logging.getLogger(__name__)


def send_notify_email(
    email_addresses: list[str],
    personalisation_data: dict[str, str],
    template_id: str,
    max_retries: int = 5,
    retry_delay: float = 0.1,
):
    """
    Sends an email notification using the Gov Notify service with the specified
    template and personalisation data. It utilizes the `NotificationsAPIClient`
    to send the email to the designated recipient.
    :param retry_delay: Retry delay. Each retry will be delayed by
    retry_delay * retry (1-max_retries) seconds
    :param max_retries: How many times to retry before giving up
    :param email_addresses: A list of email addresses to send the notification to.
    :param personalisation_data: A dictionary containing key-value pairs for
        personalisation fields to be inserted into the email template.
    :param template_id: The ID of the email template to be used for the notification.
        If not provided, a default template must be predefined or handled appropriately.
    :return: None
    :raises Exception: If an error occurs during the notification process.
    """
    notify_client = NotificationsAPIClient(settings.NOTIFY_API_KEY)
    retry = True
    for email_address in set(email_addresses):
        # Send the token using the Gov Notify template
        retry_count = 0
        while retry:
            try:
                notify_client.send_email_notification(
                    # You can give only 1 email address per call
                    # https://docs.notifications.service.gov.uk/python.html#email-address-required
                    email_address=email_address,
                    template_id=template_id,
                    personalisation=personalisation_data,
                )
                break
            except Exception as e:
                if retry_count < max_retries:
                    delay_seconds = retry_delay * (retry_count + 1)
                    logger.warning(f"Failed to send email {e} retry after {delay_seconds} seconds")
                    time.sleep(delay_seconds)  # backoff before retry
                    retry_count += 1
                else:
                    raise
        # pause between each send
        time.sleep(retry_delay)
