from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from webcaf.webcaf.models import AllowedEmailDomain, Organisation, OrganisationEmailDomain


class OrganisationEmailDomainTest(TestCase):
    def setUp(self):
        self.first_organisation = Organisation.objects.create(
            name="First Council",
            organisation_type="council",
            gss_code="E06000001",
        )
        self.second_organisation = Organisation.objects.create(
            name="Second Council",
            organisation_type="council",
            gss_code="E06000002",
        )
        self.domain = AllowedEmailDomain.objects.create(domain=" Example.GOV.UK. ")

    def test_domain_can_be_linked_to_several_organisations(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation,
            domain=self.domain,
            is_primary=True,
        )
        second_link = OrganisationEmailDomain.objects.create(
            organisation=self.second_organisation,
            domain=self.domain,
            is_primary=True,
        )

        self.assertEqual(self.domain.domain, "example.gov.uk")
        self.assertEqual(set(self.domain.organisations.all()), {self.first_organisation, self.second_organisation})
        self.assertTrue(first_link.is_primary)
        self.assertTrue(second_link.is_primary)

    def test_organisation_can_have_only_one_primary_domain(self):
        OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation,
            domain=self.domain,
            is_primary=True,
        )
        second_domain = AllowedEmailDomain.objects.create(domain="second.gov.uk")

        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganisationEmailDomain.objects.create(
                organisation=self.first_organisation,
                domain=second_domain,
                is_primary=True,
            )

    def test_domain_can_only_be_linked_to_an_organisation_once(self):
        OrganisationEmailDomain.objects.create(organisation=self.first_organisation, domain=self.domain)

        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganisationEmailDomain.objects.create(organisation=self.first_organisation, domain=self.domain)

    def test_retired_domain_cannot_be_primary(self):
        link = OrganisationEmailDomain(
            organisation=self.first_organisation,
            domain=self.domain,
            is_primary=True,
            status=OrganisationEmailDomain.Status.RETIRED,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A retired domain cannot be an organisation's primary domain.",
        ):
            link.full_clean()

    def test_retiring_association_preserves_shared_domain_and_other_association(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation,
            domain=self.domain,
        )
        second_link = OrganisationEmailDomain.objects.create(
            organisation=self.second_organisation,
            domain=self.domain,
        )

        first_link.status = OrganisationEmailDomain.Status.RETIRED
        first_link.save(update_fields=["status"])

        self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(OrganisationEmailDomain.objects.filter(pk=second_link.pk).exists())
        self.assertTrue(AllowedEmailDomain.allows_email("user@example.gov.uk"))

    def test_removing_association_preserves_shared_domain_and_other_association(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation,
            domain=self.domain,
        )
        second_link = OrganisationEmailDomain.objects.create(
            organisation=self.second_organisation,
            domain=self.domain,
        )

        first_link.delete()

        self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(OrganisationEmailDomain.objects.filter(pk=second_link.pk).exists())
        self.assertTrue(AllowedEmailDomain.allows_email("user@example.gov.uk"))

    def test_records_association_history(self):
        link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation,
            domain=self.domain,
        )
        link.status = OrganisationEmailDomain.Status.RETIRED
        link.save(update_fields=["status"])

        self.assertEqual(link.history.count(), 2)
        self.assertEqual(link.history.latest().status, OrganisationEmailDomain.Status.RETIRED)

    def test_string_representation_preserves_existing_parent_labels(self):
        link = OrganisationEmailDomain.objects.create(organisation=self.first_organisation, domain=self.domain)

        self.assertEqual(str(link), "First Council - example.gov.uk")
        self.assertEqual(str(link.history.latest().instance), "First Council - example.gov.uk")

    def test_deleting_shared_domain_is_blocked_and_preserves_primary_links_and_history(self):
        links = [
            OrganisationEmailDomain.objects.create(organisation=organisation, domain=self.domain, is_primary=True)
            for organisation in [self.first_organisation, self.second_organisation]
        ]

        for use_queryset in [False, True]:
            with self.subTest(use_queryset=use_queryset):
                with self.assertRaises(ProtectedError):
                    if use_queryset:
                        AllowedEmailDomain.objects.filter(pk=self.domain.pk).delete()
                    else:
                        self.domain.delete()

                self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
                self.assertEqual(self.domain.history.count(), 1)
                for link in links:
                    link.refresh_from_db()
                    self.assertTrue(link.is_primary)
                    self.assertEqual(link.status, OrganisationEmailDomain.Status.ACTIVE)
                    self.assertEqual(link.history.count(), 1)
                self.assertTrue(AllowedEmailDomain.allows_email("user@example.gov.uk"))

    def test_retired_association_still_protects_domain_from_deletion(self):
        link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation, domain=self.domain, status=OrganisationEmailDomain.Status.RETIRED
        )

        with self.assertRaises(ProtectedError):
            self.domain.delete()

        self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
        self.assertTrue(OrganisationEmailDomain.objects.filter(pk=link.pk).exists())

    def test_unlinked_domain_can_be_deleted_and_retains_history(self):
        domain_pk = self.domain.pk

        self.domain.delete()

        self.assertFalse(AllowedEmailDomain.objects.filter(pk=domain_pk).exists())
        self.assertEqual(AllowedEmailDomain.history.filter(id=domain_pk).count(), 2)
        self.assertEqual(AllowedEmailDomain.history.filter(id=domain_pk).latest().history_type, "-")

    def test_domain_can_be_deleted_after_all_associations_are_explicitly_removed(self):
        links = [
            OrganisationEmailDomain.objects.create(organisation=organisation, domain=self.domain, is_primary=True)
            for organisation in [self.first_organisation, self.second_organisation]
        ]
        link_ids = [link.pk for link in links]
        links[0].delete()

        with self.assertRaises(ProtectedError):
            self.domain.delete()

        links[1].delete()
        domain_pk = self.domain.pk
        self.domain.delete()

        self.assertFalse(AllowedEmailDomain.objects.filter(pk=domain_pk).exists())
        for link_id in link_ids:
            history = OrganisationEmailDomain.history.filter(id=link_id)
            self.assertEqual(history.count(), 2)
            self.assertEqual(history.latest().history_type, "-")

    def test_deleting_organisation_still_removes_only_its_links(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.first_organisation, domain=self.domain, is_primary=True
        )
        second_link = OrganisationEmailDomain.objects.create(
            organisation=self.second_organisation, domain=self.domain, is_primary=True
        )

        self.first_organisation.delete()

        self.assertFalse(OrganisationEmailDomain.objects.filter(pk=first_link.pk).exists())
        self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
        second_link.refresh_from_db()
        self.assertTrue(second_link.is_primary)
