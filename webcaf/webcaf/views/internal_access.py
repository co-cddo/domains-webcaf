import logging

from django.contrib.auth import logout
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView
from requests import RequestException

from webcaf.auth import EMAIL_DOMAIN_REJECTED_SESSION_KEY


class InternalAccessCallbackView(OIDCAuthenticationCallbackView):
    """Handle provider failures without logging tokens or provider response bodies."""

    logger = logging.getLogger("InternalAccessCallbackView")

    def login_failure(self):
        domain_rejected = self.request.session.get(EMAIL_DOMAIN_REJECTED_SESSION_KEY, False)
        logout(self.request)
        if domain_rejected:
            self.request.session[EMAIL_DOMAIN_REJECTED_SESSION_KEY] = True
        self.logger.warning("Internal Access authentication failed")
        return super().login_failure()

    def login_success(self):
        response = super().login_success()
        self.logger.info("Internal Access authentication succeeded for WebCAF user %s", self.user.pk)
        return response

    def get(self, request):
        try:
            return super().get(request)
        except RequestException:
            # RequestException text can contain provider URLs, headers or bodies.
            # State and token validation errors retain their normal secure handling.
            return self.login_failure()
