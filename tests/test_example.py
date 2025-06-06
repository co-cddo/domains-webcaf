from django.test import SimpleTestCase
from django.urls import reverse


class TestViewsBasic(SimpleTestCase):
    def test_index_page_status(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
