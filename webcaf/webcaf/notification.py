from django.conf import settings
from notifications_python_client import NotificationsAPIClient


def send_notify_email(email_addresses: list[str], personalisation_data: dict[str, str], template_id: str | None = None):
    """
    Sends an email notification using the Gov Notify service with the specified
    template and personalisation data. It utilizes the `NotificationsAPIClient`
    to send the email to the designated recipient.
    :param email_addresses: A list of email addresses to send the notification to.
    :param personalisation_data: A dictionary containing key-value pairs for
        personalisation fields to be inserted into the email template.
    :param template_id: The ID of the email template to be used for the notification.
        If not provided, a default template must be predefined or handled appropriately.
    :return: None
    :raises Exception: If an error occurs during the notification process.
    """
    notify_client = NotificationsAPIClient(settings.NOTIFY_API_KEY)
    # Send the token using the Gov Notify template
    notify_client.send_email_notification(
        email_address=",".join(email_addresses),
        template_id=template_id,
        personalisation=personalisation_data,
    )
