from django.core.exceptions import ValidationError
from django.test import TestCase

from webcaf.webcaf.models import Organisation
from webcaf.webcaf.utils.council_codes import official_council_gss_codes


class OrganisationTest(TestCase):
    def test_offers_only_council_mhclg_and_independent_assurer_types(self):
        self.assertEqual(
            Organisation.ORGANISATION_TYPE_CHOICES,
            [("council", "Council"), ("mhclg", "MHCLG"), ("independent-assurer", "Independent assurer")],
        )

    def test_requires_gss_code_only_for_councils(self):
        self.assertEqual(Organisation.GSS_CODE_REQUIRED_ORGANISATION_TYPES, frozenset({"council"}))

    def test_saves_valid_gss_code(self):
        organisation = Organisation.objects.create(
            name="Test Council",
            organisation_type="council",
            gss_code="E06000001",
        )

        self.assertEqual(organisation.gss_code, "E06000001")

    def test_rejects_invalid_gss_code_format(self):
        invalid_codes = ["06000001", "EE0600001", "E0600000", "E060000001", "e06000001", "E0600000A"]

        for invalid_code in invalid_codes:
            with self.subTest(gss_code=invalid_code):
                with self.assertRaises(ValidationError) as context:
                    Organisation.objects.create(name=f"Council {invalid_code}", gss_code=invalid_code)

                self.assertIn(
                    "Enter a valid GSS code: one uppercase letter followed by eight digits (for example, E06000001).",
                    context.exception.message_dict["gss_code"],
                )

    def test_rejects_duplicate_gss_code(self):
        Organisation.objects.create(name="First Council", gss_code="E06000001")

        with self.assertRaises(ValidationError) as context:
            Organisation.objects.create(name="Second Council", gss_code="E06000001")

        self.assertEqual(
            context.exception.message_dict["gss_code"],
            ["Organisation with this GSS code already exists."],
        )

    def test_requires_gss_code_for_councils(self):
        for organisation_type in Organisation.GSS_CODE_REQUIRED_ORGANISATION_TYPES:
            with self.subTest(organisation_type=organisation_type):
                with self.assertRaises(ValidationError) as context:
                    Organisation.objects.create(
                        name=f"Organisation {organisation_type}",
                        organisation_type=organisation_type,
                    )

                self.assertEqual(
                    context.exception.messages,
                    ["Councils must have a GSS code."],
                )

    def test_allows_mhclg_and_independent_assurers_without_gss_code(self):
        for organisation_type in ["mhclg", "independent-assurer"]:
            with self.subTest(organisation_type=organisation_type):
                organisation = Organisation.objects.create(
                    name=f"Organisation {organisation_type}",
                    organisation_type=organisation_type,
                )

                self.assertIsNone(organisation.gss_code)

    def test_rejects_existing_council_without_gss_code_on_next_save(self):
        organisation = Organisation(name="Existing Council", organisation_type="council")
        Organisation.objects.bulk_create([organisation])

        organisation.name = "Renamed Existing Council"

        with self.assertRaises(ValidationError) as context:
            organisation.save()

        self.assertEqual(
            context.exception.messages,
            ["Councils must have a GSS code."],
        )

    def test_partial_save_requires_gss_code_to_be_saved_with_unrelated_changes(self):
        organisation = Organisation(name="Existing Council", organisation_type="council")
        Organisation.objects.bulk_create([organisation])

        organisation.name = "Renamed Existing Council"
        organisation.gss_code = "E06000001"

        with self.assertRaises(ValidationError) as context:
            organisation.save(update_fields=["name"])

        self.assertEqual(
            context.exception.messages,
            ["Councils must save their GSS code in the same operation."],
        )
        organisation.refresh_from_db()
        self.assertEqual(organisation.name, "Existing Council")
        self.assertIsNone(organisation.gss_code)

        organisation.name = "Renamed Existing Council"
        organisation.gss_code = "E06000001"
        organisation.save(update_fields=["name", "gss_code"])

        organisation.refresh_from_db()
        self.assertEqual(organisation.name, "Renamed Existing Council")
        self.assertEqual(organisation.gss_code, "E06000001")

    def test_stores_empty_optional_gss_codes_as_null(self):
        first = Organisation.objects.create(name="First Organisation", gss_code="")
        second = Organisation.objects.create(name="Second Organisation", gss_code="")

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertIsNone(first.gss_code)
        self.assertIsNone(second.gss_code)

    def test_records_gss_code_in_history(self):
        organisation = Organisation.objects.create(name="Test Organisation", gss_code="E06000001")

        self.assertEqual(organisation.history.latest().gss_code, "E06000001")


class OrganisationCouncilSubtypeTest(TestCase):
    def test_works_out_subtype_from_gss_prefix(self):
        for prefix, subtype in Organisation.COUNCIL_SUBTYPES_BY_GSS_PREFIX.items():
            with self.subTest(prefix=prefix):
                organisation = Organisation(
                    name=f"Council {prefix}", organisation_type="council", gss_code=f"{prefix}000001"
                )

                self.assertEqual(organisation.council_subtype, subtype)

    def test_combined_authority_council_has_combined_authority_subtype(self):
        organisation = Organisation.objects.create(
            name="West Yorkshire Combined Authority", organisation_type="council", gss_code="E47000003"
        )

        self.assertEqual(organisation.council_subtype, "Combined authority")

    def test_has_no_subtype_for_an_unknown_prefix(self):
        organisation = Organisation(name="Council", organisation_type="council", gss_code="E99000001")

        self.assertIsNone(organisation.council_subtype)

    def test_has_no_subtype_for_organisations_that_are_not_councils(self):
        for organisation_type in ["mhclg", "independent-assurer", None]:
            with self.subTest(organisation_type=organisation_type):
                organisation = Organisation(
                    name="Organisation", organisation_type=organisation_type, gss_code="E06000001"
                )

                self.assertIsNone(organisation.council_subtype)


class OrganisationRemovedFieldsTest(TestCase):
    def test_contact_parent_and_reference_fields_are_removed_from_the_model_and_its_history(self):
        removed_fields = ["contact_name", "contact_email", "contact_role", "parent_organisation", "reference"]

        for model in [Organisation, Organisation.history.model]:
            field_names = {field.name for field in model._meta.get_fields()}
            for field_name in removed_fields:
                with self.subTest(model=model.__name__, field_name=field_name):
                    self.assertNotIn(field_name, field_names)


class OrganisationOfficialGssCodeTest(TestCase):
    def test_accepts_an_official_code_for_each_council_prefix(self):
        for gss_code in ["E06000014", "E07000110", "E08000035", "E09000033", "E10000016", "E47000003"]:
            with self.subTest(gss_code=gss_code):
                organisation = Organisation.objects.create(
                    name=f"Council {gss_code}", organisation_type="council", gss_code=gss_code
                )

                self.assertIsNotNone(organisation.council_subtype)

    def test_rejects_a_council_code_with_an_unsupported_prefix(self):
        with self.assertRaises(ValidationError) as context:
            Organisation.objects.create(name="Unknown Council", organisation_type="council", gss_code="E99000001")

        self.assertEqual(
            context.exception.message_dict["gss_code"],
            [
                "E99000001 is not the GSS code of an English council or combined authority in the ONS list. Check the code."
            ],
        )

    def test_rejects_an_unassigned_council_code_with_a_supported_prefix(self):
        with self.assertRaises(ValidationError) as context:
            Organisation.objects.create(name="Unassigned Council", organisation_type="council", gss_code="E08000099")

        self.assertIn("E08000099 is not the GSS code", context.exception.message_dict["gss_code"][0])

    def test_partial_save_cannot_store_an_unassigned_code_on_a_saved_council(self):
        organisation = Organisation.objects.create(name="Leeds", organisation_type="council", gss_code="E08000035")
        organisation.organisation_type = "mhclg"
        organisation.gss_code = "E08000099"

        with self.assertRaises(ValidationError) as context:
            organisation.save(update_fields=["gss_code"])

        self.assertIn("E08000099 is not the GSS code", context.exception.message_dict["gss_code"][0])
        stored = Organisation.objects.values_list("organisation_type", "gss_code").get(pk=organisation.pk)
        self.assertEqual(stored, ("council", "E08000035"))

    def test_rejects_a_council_code_from_outside_england(self):
        with self.assertRaises(ValidationError):
            Organisation.objects.create(name="Welsh Council", organisation_type="council", gss_code="W06000015")

    def test_every_official_code_has_a_council_subtype(self):
        official_codes = official_council_gss_codes()

        self.assertEqual(len(official_codes), 332)
        for gss_code in official_codes:
            with self.subTest(gss_code=gss_code):
                self.assertIn(gss_code[:3], Organisation.COUNCIL_SUBTYPES_BY_GSS_PREFIX)
