import logging

from django.shortcuts import redirect
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class OIDCBackend(OIDCAuthenticationBackend):
    """
    Create the local user representation for the SSO authenticated user
    This holds only the basic information.
    """

    logger = logging.getLogger("OIDCBackend")

    def create_user(self, claims):
        self.logger.info("Create user for claims", claims)
        user = super().create_user(claims)
        user.email = claims.get("email")
        user.username = claims.get("email")
        user.first_name = claims.get("given_name", claims.get("name", ""))
        user.last_name = claims.get("family_name", "")
        user.save()
        return user

    def update_user(self, user, claims):
        """
        Sync any changes previously saved.
        :param user:
        :param claims:
        :return:
        """
        self.logger.info("Update user", claims)
        user.first_name = claims.get("given_name", user.first_name) or claims.get("name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()
        return user


class LoginRequiredMiddleware:
    logger = logging.getLogger("LoginRequiredMiddleware")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Let admin and static/media go through without redirecting to OIDC
        if (
            request.path == "/"
            or request.path == "/"
            or request.path.startswith("/admin/")
            or request.path.startswith("/assets/")
            or request.path.startswith("/oidc/")
            or request.user.is_authenticated
        ):
            self.logger.debug("Allowing access to %s, authenticated %s", request.path, request.user.is_authenticated)
            return self.get_response(request)

        self.logger.info("Redirecting to OIDC login for %s", request.path)
        # For everything else, redirect to OIDC login
        return redirect("/oidc/authenticate/")
