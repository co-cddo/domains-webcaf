import logging

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django_otp import login as otp_login

from webcaf.webcaf.models import GovNotifyEmailDevice
from webcaf.webcaf.utils import mask_email

# Get an instance of a logger for this module
logger = logging.getLogger(__name__)


class TokenForm(forms.Form):
    """
    A simplified form for 2FA token verification.

    It provides a single 'otp_token' field. This form is used by
    `Verify2FATokenView` as part of a simplified flow where the token is
    sent to the user upon page load.
    """

    otp_token = forms.CharField(
        label="Token",
        max_length=6,
        min_length=6,
        required=False,  # Set to False to allow custom error in the view
        widget=forms.TextInput(
            attrs={
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "autofocus": "autofocus",
                "class": "govuk-input govuk-input--width-5 govuk-input--extra-letter-spacing",
            }
        ),
    )


class Verify2FATokenView(LoginRequiredMixin, FormView):
    """
    Handles the 2FA token verification process via email.

    This view uses the simple `TokenForm` to capture the OTP token.
    The `dispatch` method is overridden to send a new token via email
    every time the page is loaded (GET or POST).

    The `form_valid` method handles the actual token verification.
    """

    template_name = "users/verify-2fa-token.html"
    form_class = TokenForm
    success_url = reverse_lazy("my-account")

    def get(self, request, *args, **kwargs):
        """
        Overrides get to send an OTP token on every page load.

        This method ensures that a `GovNotifyEmailDevice` exists for the
        user (creating one if necessary) and then calls
        `device.generate_challenge()` to send a new token. This effectively
        sends a new code every time the user visits or refreshes the page.
        """
        try:
            device, created = GovNotifyEmailDevice.objects.get_or_create(user=request.user, email=request.user.email)
            if created:
                logger.info(mask_email(f"Created new GovNotifyEmailDevice for user {request.user.email}"))

            device.generate_challenge()
            logger.info(mask_email(f"Generated new 2FA token challenge for user {request.user.email}"))

        except Exception as e:
            logger.error(
                mask_email(f"Error in Verify2FATokenView.dispatch for user {request.user.email}: {e}"), exc_info=True
            )

        return super().get(request, *args, **kwargs)

    def form_invalid(self, form):
        """
        Handles invalid form submissions.

        This is called if the form's `clean` methods fail or if
        `form_valid` returns `self.form_invalid(form)`.
        """
        logger.warning(
            mask_email(
                f"Invalid 2FA form submission for user {self.request.user.email}. " f"Errors: {form.errors.as_json()}"
            )
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        """
        Validates the submitted OTP token.

        This method is called after the form's basic validation passes.
        It retrieves the user's device, verifies the token, and either
        logs them into the OTP session or adds a form error.
        """
        token = form.cleaned_data.get("otp_token")
        if not token:
            # Handle empty token submission as 'required=False'
            logger.warning(mask_email(f"Empty 2FA token submitted for user {self.request.user.email}"))
            form.add_error("otp_token", "Please enter your 6-digit code.")
            return self.form_invalid(form)

        try:
            device = GovNotifyEmailDevice.objects.get(user=self.request.user, email=self.request.user.email)
        except GovNotifyEmailDevice.DoesNotExist:
            logger.error(
                mask_email(
                    f"CRITICAL: GovNotifyEmailDevice not found for user {self.request.user.email} during form_valid."
                )
            )
            form.add_error(None, "An unexpected error occurred. Please try again.")
            return self.form_invalid(form)

        allow_access = device.verify_token(token)
        if not allow_access:
            logger.warning(mask_email(f"Invalid 2FA token attempt for user {self.request.user.email}"))
            form.add_error("otp_token", "Invalid token")
            return self.form_invalid(form)

        logger.info(f"Successful 2FA verification for user {self.request.user.email}")
        otp_login(self.request, device)
        return super().form_valid(form)
