from django.core.exceptions import ValidationError
from django.test import TestCase

from webcaf.webcaf.models import AllowedEmailDomain


class AllowedEmailDomainTest(TestCase):
    def test_normalises_domain_before_storing(self):
        allowed_domain = AllowedEmailDomain.objects.create(domain=" Example.COM. ")

        self.assertEqual(allowed_domain.domain, "example.com")
        self.assertTrue(AllowedEmailDomain.allows_email("USER@EXAMPLE.COM"))

    def test_requires_an_exact_domain_match(self):
        AllowedEmailDomain.objects.create(domain="example.com")

        self.assertFalse(AllowedEmailDomain.allows_email("user@service.example.com"))
        self.assertFalse(AllowedEmailDomain.allows_email("user@notexample.com"))

    def test_mixed_case_spelling_does_not_create_duplicate_domain(self):
        AllowedEmailDomain.objects.create(domain="kent.gov.uk")

        with self.assertRaises(ValidationError):
            AllowedEmailDomain.objects.create(domain="Kent.Gov.UK")

    def test_empty_allowlist_rejects_new_email_domains(self):
        self.assertFalse(AllowedEmailDomain.allows_email("user@example.com"))

    def test_rejects_invalid_domains(self):
        with self.assertRaises(ValidationError):
            AllowedEmailDomain.objects.create(domain="https://example.com")

    def test_records_history(self):
        allowed_domain = AllowedEmailDomain.objects.create(domain="example.com")

        self.assertEqual(allowed_domain.history.count(), 1)
