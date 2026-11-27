import importlib

from django.apps import apps
from django.test import TestCase

from webcaf.webcaf.models import Organisation

migration = importlib.import_module(
    "webcaf.webcaf.migrations.0040_organisation_types_council_mhclg_independent_assurer"
)


class OrganisationTypeMigrationTest(TestCase):
    """
    Exercises the data step of migration 0040 against the current models.
    Organisation.objects.create() validates only the GSS code, so rows with a
    removed type can still be created here, as they exist in databases that
    were not reset.
    """

    def create_organisation(self, name, organisation_type, **kwargs):
        return Organisation.objects.create(name=name, organisation_type=organisation_type, **kwargs)

    def test_moves_combined_authorities_to_council(self):
        organisation = self.create_organisation("Test Combined Authority", "combined-authority", gss_code="E47000001")

        migration.replace_organisation_types(apps, None)

        organisation.refresh_from_db()
        self.assertEqual(organisation.organisation_type, "council")
        self.assertEqual(organisation.gss_code, "E47000001")

    def test_clears_every_removed_type(self):
        for index, removed_type in enumerate(sorted(migration.REMOVED_ORGANISATION_TYPES)):
            self.create_organisation(f"Organisation {index}", removed_type)

        migration.replace_organisation_types(apps, None)

        self.assertSetEqual(set(Organisation.objects.values_list("organisation_type", flat=True)), {None})

    def test_keeps_new_and_empty_types(self):
        council = self.create_organisation("Test Council", "council", gss_code="E06000001")
        mhclg = self.create_organisation("MHCLG", "mhclg")
        assurer = self.create_organisation("Test Assurer", "independent-assurer")
        no_type = self.create_organisation("Untyped Organisation", None)

        migration.replace_organisation_types(apps, None)

        for organisation, expected_type in [
            (council, "council"),
            (mhclg, "mhclg"),
            (assurer, "independent-assurer"),
            (no_type, None),
        ]:
            with self.subTest(organisation=organisation.name):
                organisation.refresh_from_db()
                self.assertEqual(organisation.organisation_type, expected_type)
                self.assertFalse(
                    organisation.history.filter(
                        history_change_reason__startswith=migration.CHANGE_REASON_PREFIX
                    ).exists()
                )

    def test_records_the_old_type_in_history(self):
        organisation = self.create_organisation("Cabinet Office", "ministerial-department")

        migration.replace_organisation_types(apps, None)

        latest = organisation.history.latest()
        self.assertIsNone(latest.organisation_type)
        self.assertEqual(latest.history_type, "~")
        self.assertEqual(latest.history_change_reason, "CS-680 removed organisation type: ministerial-department")
        self.assertEqual(organisation.history.earliest().organisation_type, "ministerial-department")

    def test_keeps_other_fields(self):
        organisation = self.create_organisation("Cabinet Office", "ministerial-department", gss_code="E06000001")
        before = Organisation.objects.values().get(pk=organisation.pk)

        migration.replace_organisation_types(apps, None)

        after = Organisation.objects.values().get(pk=organisation.pk)
        self.assertEqual(after, {**before, "organisation_type": None})

    def test_reverse_restores_old_types_and_removes_its_history(self):
        combined_authority = self.create_organisation(
            "Test Combined Authority", "combined-authority", gss_code="E47000001"
        )
        ministry = self.create_organisation("Cabinet Office", "ministerial-department")
        migration.replace_organisation_types(apps, None)

        migration.restore_organisation_types(apps, None)

        for organisation, expected_type in [
            (combined_authority, "combined-authority"),
            (ministry, "ministerial-department"),
        ]:
            with self.subTest(organisation=organisation.name):
                organisation.refresh_from_db()
                self.assertEqual(organisation.organisation_type, expected_type)
                self.assertFalse(
                    organisation.history.filter(
                        history_change_reason__startswith=migration.CHANGE_REASON_PREFIX
                    ).exists()
                )

    def test_reverse_keeps_a_type_changed_after_the_migration(self):
        organisation = self.create_organisation("Cabinet Office", "ministerial-department")
        migration.replace_organisation_types(apps, None)
        Organisation.objects.filter(pk=organisation.pk).update(organisation_type="mhclg")

        migration.restore_organisation_types(apps, None)

        organisation.refresh_from_db()
        self.assertEqual(organisation.organisation_type, "mhclg")
