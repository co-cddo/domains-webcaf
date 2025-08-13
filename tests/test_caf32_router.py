import os
import unittest

from webcaf import urls

# Test that when _create_view_and_url is called with an outcome, it has a form class as an argument.


# We test for the validity of the CAF YAML elsewhere, so this module assmes the YAML is valid
class TestFrameworkRouter(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")
        self._original_urlpatterns = list(urls.urlpatterns)
        urls.urlpatterns[:] = []
