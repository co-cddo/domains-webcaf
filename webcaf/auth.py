"""
Authentication module for webcaf application.

This module provides OpenID Connect (OIDC) authentication backend and middleware
for enforcing authentication requirements across the application.
"""

import logging

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from webcaf.webcaf.utils import mask_email


class OIDCBackend(OIDCAuthenticationBackend):
    """
    Custom OIDC authentication backend for creating and updating local user representations.

    This backend extends mozilla_django_oidc's OIDCAuthenticationBackend to handle
    user creation and updates based on claims received from the OIDC provider during
    SSO authentication.

    Attributes:
        logger: Logger instance for tracking authentication events.
    """

    logger = logging.getLogger("OIDCBackend")

    def create_user(self, claims):
        """
        Create a new local user based on OIDC claims.

        Extracts user information from the OIDC claims and creates a Django user
        with email as the username. The user's first and last names are populated
        from the claims if available.

        Args:
            claims (dict): Dictionary of OIDC claims containing user information.
                Expected keys include 'email', 'given_name', 'family_name', and 'name'.

        Returns:
            User: The newly created Django user instance.

        Example claims structure:
            {
                'email': 'user@example.com',
                'given_name': 'John',
                'family_name': 'Doe',
                'name': 'John Doe'
            }
        """
        self.logger.info(mask_email(f"Create user for {claims.get('email')}"))
        user = super().create_user(claims)
        user.email = claims.get("email")
        user.username = claims.get("email")
        user.first_name = claims.get("given_name", claims.get("name", ""))
        user.last_name = claims.get("family_name", "")
        user.save()
        self.logger.info(mask_email(f"Created user {user.pk} {user.email}"))
        return user

    def update_user(self, user, claims):
        """
        Update an existing user's information based on OIDC claims.

        Synchronizes the local user record with any changes from the OIDC provider.
        This method is called during login to ensure user information remains up-to-date.

        Args:
            user (User): The Django user instance to update.
            claims (dict): Dictionary of OIDC claims containing updated user information.
                Expected keys include 'given_name', 'family_name', and 'name'.

        Returns:
            User: The updated Django user instance.

        Note:
            Falls back to existing user values if claims are missing or empty.
        """
        self.logger.info(mask_email(f"User  {user.id} {user.email} logged in to the system"))
        user.first_name = claims.get("given_name", user.first_name) or claims.get("name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()
        return user


class LoginRequiredMiddleware:
    """
    Django middleware that enforces authentication for all requests except exempted URLs.

    This middleware redirects unauthenticated users to the OIDC authentication
    initialization endpoint, with exceptions for authentication-related URLs,
    static assets, and public pages.

    Attributes:
        logger: Logger instance for tracking middleware events.
        exempt_url_prefixes (list): URL path prefixes that don't require authentication.
        exempt_exact_urls (list): Exact URL paths that don't require authentication.
    """

    logger = logging.getLogger("LoginRequiredMiddleware")

    def __init__(self, get_response):
        """
        Initialize the middleware with exempted URLs.

        Args:
            get_response (callable): The next middleware or view in the chain.
        """
        self.get_response = get_response
        self.exempt_url_prefixes = [
            reverse("oidc_authentication_init"),
            reverse("oidc_authentication_callback"),
            reverse("oidc_logout"),
            # Admin authentication is done separately
            "/admin/",
            # public pages and static assets
            "/assets/",
            "/static/",
            "/media",
            "/public/",
            "/session-expired/",
            "/logout/",
        ]
        self.exempt_exact_urls = [
            # index page
            "/",
            "/review/",
            "/review",
        ]

    def __call__(self, request):
        """
        Process the request and enforce authentication requirements.

        Checks if the user is authenticated or if the requested path is exempted.
        Unauthenticated requests to non-exempted paths are redirected to the
        OIDC authentication flow.

        Args:
            request: Django HTTP request object.

        Returns:
            HttpResponse: Either the response from the next middleware/view or
                a redirect to the authentication initialization endpoint.
        """
        if (
            not any(request.path.startswith(url) for url in self.exempt_url_prefixes)
            and request.path not in self.exempt_exact_urls
        ):
            # you need to be authenticated to access any page outside the non secure list
            if not request.user.is_authenticated or request.user.is_anonymous:
                if request.path == reverse("verify-2fa-token") and request.method == "POST":
                    # The only possibility of this happening is that the session timing out
                    # while the user is trying to submit the 2FA token.
                    # So, reset the flow and get a new token
                    self.logger.info("Session expired while submitting 2FA token. Redirecting to session-expired")
                    return redirect("session-expired")
                self.logger.debug("Force authentication for %s", request.path)
                return redirect("oidc_authentication_init")

            # If the user is authenticated, check if they're verified'
            if not settings.ENABLED_2FA:
                # handle the local dev for when 2FA is disabled
                self.logger.debug("Allowing access for local development or testing")
                return self.get_response(request)
            elif not request.user.is_verified():
                if not request.user.is_staff:
                    # No varification support yet for the staff users
                    # Allow access to the verification page
                    if request.path == reverse("verify-2fa-token"):
                        return self.get_response(request)
                    # Any other unverified user access to urls is redirected to the verification page
                    verify_url = reverse("verify-2fa-token")
                    return redirect(verify_url)

        self.logger.debug(
            "Allowing access to %s, authenticated %s is_staff %s",
            request.path,
            request.user.is_authenticated,
            request.user.is_staff,
        )
        return self.get_response(request)
