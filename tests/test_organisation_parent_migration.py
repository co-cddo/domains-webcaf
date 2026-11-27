from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = ("webcaf", "0040_organisation_types_council_mhclg_independent_assurer")
AFTER = ("webcaf", "0042_remove_organisation_parent_organisation")


class RemoveParentOrganisationMigrationTest(TransactionTestCase):
    """
    Runs migrations 0041 and 0042 forwards and backwards on organisations created in the
    0040 schema, where the parent organisation field still exists.
    """

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def setUp(self):
        old_apps = self.migrate(BEFORE)
        Organisation = old_apps.get_model("webcaf", "Organisation")
        self.parent = Organisation.objects.create(name="Cabinet Office", reference="ORG01", organisation_type="mhclg")
        self.child = Organisation.objects.create(
            name="Government Digital Service",
            reference="ORG02",
            organisation_type="mhclg",
            parent_organisation=self.parent,
        )
        self.without_parent = Organisation.objects.create(name="Test Company", reference="ORG03")

    def tearDown(self):
        # Return to the latest migration so later tests run on the current schema.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_removes_the_field_and_records_the_parent_in_history(self):
        new_apps = self.migrate(AFTER)
        Organisation = new_apps.get_model("webcaf", "Organisation")
        HistoricalOrganisation = new_apps.get_model("webcaf", "HistoricalOrganisation")

        field_names = {field.name for field in Organisation._meta.get_fields()}
        self.assertNotIn("parent_organisation", field_names)

        history = HistoricalOrganisation.objects.filter(id=self.child.id)
        self.assertEqual(
            list(history.values_list("history_change_reason", flat=True)),
            [f"CS-680 removed parent organisation: {self.parent.id} Cabinet Office"],
        )
        self.assertEqual(history.get().reference, "ORG02")
        self.assertFalse(
            HistoricalOrganisation.objects.filter(id__in=[self.parent.id, self.without_parent.id]).exists()
        )

    def test_keeps_organisations_and_references(self):
        new_apps = self.migrate(AFTER)
        Organisation = new_apps.get_model("webcaf", "Organisation")

        self.assertEqual(
            dict(Organisation.objects.values_list("name", "reference")),
            {"Cabinet Office": "ORG01", "Government Digital Service": "ORG02", "Test Company": "ORG03"},
        )

    def test_reverse_restores_the_parent(self):
        self.migrate(AFTER)

        old_apps = self.migrate(BEFORE)
        Organisation = old_apps.get_model("webcaf", "Organisation")
        HistoricalOrganisation = old_apps.get_model("webcaf", "HistoricalOrganisation")

        self.assertEqual(Organisation.objects.get(pk=self.child.pk).parent_organisation_id, self.parent.id)
        self.assertIsNone(Organisation.objects.get(pk=self.without_parent.pk).parent_organisation_id)
        self.assertFalse(
            HistoricalOrganisation.objects.filter(history_change_reason__startswith="CS-680 removed parent").exists()
        )
