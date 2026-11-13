from pathlib import Path

from django.conf import settings
from weasyprint import URLFetcher


class CustomURLFetcher(URLFetcher):
    """
    Custom URL fetcher for WeasyPrint PDF generation.
    Intercepts URLs containing static assets (matching 'assets/') to resolve
    and load them directly from the local filesystem via ``settings.STATIC_ROOT``,
    All other URLs fall back to the default URLFetcher implementation.
    """

    def fetch(self, url, headers=None):
        if "assets/" in url:
            # Need to set the absolute path to the static files as pdf generation does not work with relative paths
            asset_relative_path = url.split("assets/")[-1]
            asset_path = Path(settings.STATIC_ROOT) / asset_relative_path
            local_uri = asset_path.as_uri()
            return super().fetch(local_uri, headers=headers)

        return super().fetch(url, headers=headers)
