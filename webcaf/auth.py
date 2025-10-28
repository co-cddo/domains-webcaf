"""
Authentication module for webcaf application.

This module provides OpenID Connect (OIDC) authentication backend and middleware
for enforcing authentication requirements across the application.
"""

import logging

from django.shortcuts import redirect
from django.urls import reverse
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


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
        self.logger.info(f"Create user for {claims.get('email')}")
        user = super().create_user(claims)
        user.email = claims.get("email")
        user.username = claims.get("email")
        user.first_name = claims.get("given_name", claims.get("name", ""))
        user.last_name = claims.get("family_name", "")
        user.save()
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
        self.logger.info(f"User  {user.username} logged in to the system")
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
            "/assets/",
            "/static/",
            "/media",
            "/public/",
            "/session-expired/",
        ]
        self.exempt_exact_urls = [
            # index page
            "/"
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
            not request.user.is_authenticated
            and not any(request.path.startswith(url) for url in self.exempt_url_prefixes)
            and request.path not in self.exempt_exact_urls
        ):
            self.logger.debug("Force authentication for %s", request.path)
            return redirect("oidc_authentication_init")
        self.logger.debug("Allowing access to %s, authenticated %s", request.path, request.user.is_authenticated)
        return self.get_response(request)
