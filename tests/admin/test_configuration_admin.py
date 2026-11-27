from datetime import date

from django.test import TestCase

from webcaf.webcaf.admin import CustomConfigForm
from webcaf.webcaf.models import Configuration


class CustomConfigFormTests(TestCase):
    """Tests for CustomConfigForm handling of stage_4_start_date."""

    def _valid_form_data(self, **overrides):
        data = {
            "name": "test_config_26_27",
            "current_assessment_period": "26/27",
            "assessment_period_end": "2027-08-31T23:59",
            "banner_display_until": "2027-03-31T23:59",
            "default_framework": "caf32",
            "stage_4_start_date": "2027-02-01",
        }
        data.update(overrides)
        return data

    def test_populates_initial_stage_4_start_date(self):
        config = Configuration.objects.create(
            name="test_config_26_27",
            config_data={
                "current_assessment_period": "26/27",
                "assessment_period_end": "31 August 2027 11:59pm",
                "banner_display_until": "31 March 2027 11:59pm",
                "default_framework": "caf32",
                "stage_4_start_date": "01 February 2027",
            },
        )

        form = CustomConfigForm(instance=config)

        self.assertEqual(form.fields["stage_4_start_date"].initial, "2027-02-01")

    def test_older_config_without_stage_4_start_date_initialises_and_saves(self):
        config = Configuration.objects.create(
            name="test_config_25_26",
            config_data={
                "current_assessment_period": "25/26",
                "assessment_period_end": "31 August 2026 11:59pm",
                "banner_display_until": "31 March 2026 11:59pm",
                "default_framework": "caf32",
            },
        )

        initial_form = CustomConfigForm(instance=config)
        self.assertIsNone(initial_form.fields["stage_4_start_date"].initial)

        form = CustomConfigForm(
            data=self._valid_form_data(
                name="test_config_25_26", current_assessment_period="25/26", stage_4_start_date=""
            ),
            instance=config,
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertNotIn("stage_4_start_date", saved.config_data)
        self.assertIsNone(saved.get_stage_4_start_date())

    def test_saves_stage_4_start_date(self):
        form = CustomConfigForm(data=self._valid_form_data())

        self.assertTrue(form.is_valid(), form.errors)
        config = form.save()

        self.assertEqual(config.config_data["stage_4_start_date"], "01 February 2027")
        self.assertEqual(config.get_stage_4_start_date(), date(2027, 2, 1))

    def test_clears_stage_4_start_date_when_submitted_blank(self):
        config = Configuration.objects.create(
            name="test_config_clear",
            config_data={
                "current_assessment_period": "26/27",
                "assessment_period_end": "31 August 2027 11:59pm",
                "banner_display_until": "31 March 2027 11:59pm",
                "default_framework": "caf32",
                "stage_4_start_date": "01 February 2027",
            },
        )

        form = CustomConfigForm(
            data=self._valid_form_data(name="test_config_clear", stage_4_start_date=""),
            instance=config,
        )

        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertNotIn("stage_4_start_date", saved.config_data)
        self.assertIsNone(saved.get_stage_4_start_date())
