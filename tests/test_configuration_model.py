from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from webcaf.webcaf.models import Configuration


class ConfigurationModelTest(TestCase):
    """Tests for Configuration model methods."""

    def test_get_submission_due_date_valid_format(self):
        """Test parsing a valid date string in the expected format."""
        config = Configuration.objects.create(
            name="test_config", config_data={"assessment_period_end": "31 March 2026 11:59pm"}
        )
        result = config.get_submission_due_date()

        self.assertIsNotNone(result)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 31)
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.minute, 59)

    def test_get_submission_due_date_with_am_time(self):
        """Test parsing a date with AM time."""
        config = Configuration.objects.create(
            name="test_config_am", config_data={"assessment_period_end": "15 June 2025 09:30am"}
        )
        result = config.get_submission_due_date()

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 30)

    def test_get_submission_due_date_midnight(self):
        """Test parsing midnight (12:00am)."""
        config = Configuration.objects.create(
            name="test_config_midnight", config_data={"assessment_period_end": "01 January 2026 12:00am"}
        )
        result = config.get_submission_due_date()

        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)

    def test_get_submission_due_date_noon(self):
        """Test parsing noon (12:00pm)."""
        config = Configuration.objects.create(
            name="test_config_noon", config_data={"assessment_period_end": "15 July 2025 12:00pm"}
        )
        result = config.get_submission_due_date()

        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 12)
        self.assertEqual(result.minute, 0)

    def test_get_stage_4_start_date_valid_format(self):
        """Test parsing a valid stage_4_start_date string."""
        config = Configuration.objects.create(
            name="test_stage_4_valid", config_data={"stage_4_start_date": "01 February 2027"}
        )
        result = config.get_stage_4_start_date()

        self.assertEqual(result, date(2027, 2, 1))

    def test_get_stage_4_start_date_returns_none_when_unset(self):
        """Test older configurations without stage_4_start_date return None."""
        config = Configuration.objects.create(
            name="test_stage_4_unset", config_data={"assessment_period_end": "31 March 2026 11:59pm"}
        )

        self.assertIsNone(config.get_stage_4_start_date())

    def test_is_stage_4_open_returns_true_when_unset(self):
        """Test Stage 4 defaults to open when stage_4_start_date is not configured."""
        config = Configuration.objects.create(
            name="test_stage_4_default_open", config_data={"assessment_period_end": "31 March 2026 11:59pm"}
        )

        self.assertTrue(config.is_stage_4_open())

    @freeze_time("2027-01-31 23:59:59")
    def test_is_stage_4_open_before_start_date(self):
        """Test Stage 4 is closed before the configured start date."""
        config = Configuration.objects.create(
            name="test_stage_4_before", config_data={"stage_4_start_date": "01 February 2027"}
        )

        self.assertFalse(config.is_stage_4_open())

    @freeze_time("2027-02-01 00:00:00")
    def test_is_stage_4_open_on_start_date(self):
        """Test Stage 4 is open on the configured start date."""
        config = Configuration.objects.create(
            name="test_stage_4_on_date", config_data={"stage_4_start_date": "01 February 2027"}
        )

        self.assertTrue(config.is_stage_4_open())

    @freeze_time("2027-02-02 10:00:00")
    def test_is_stage_4_open_after_start_date(self):
        """Test Stage 4 is open after the configured start date."""
        config = Configuration.objects.create(
            name="test_stage_4_after", config_data={"stage_4_start_date": "01 February 2027"}
        )

        self.assertTrue(config.is_stage_4_open())

    @freeze_time("2027-06-30 23:30:00")
    def test_is_stage_4_open_uses_london_timezone_during_bst(self):
        """Test Stage 4 open check uses Europe/London local date (23:30 UTC on 30 June is 00:30 BST on 1 July)."""
        config = Configuration.objects.create(
            name="test_stage_4_bst", config_data={"stage_4_start_date": "01 July 2027"}
        )

        self.assertTrue(config.is_stage_4_open())


@freeze_time("2055-03-15 12:00:00")
class ConfigurationManagerTest(TestCase):
    """Tests for ConfigurationManager methods.
    Set the current time to 2055-03-15 12:00:00. So, it will not conflict with the other tests or existing data.
    """

    def test_get_default_config_returns_earliest_future_config(self):
        """Test that get_default_config returns the config with the earliest future end date."""
        now = timezone.now()

        # Create configs with different future end dates
        future_date_1 = now + timedelta(days=30)
        future_date_2 = now + timedelta(days=60)
        future_date_3 = now + timedelta(days=15)

        Configuration.objects.create(
            name="config_30_days", config_data={"assessment_period_end": future_date_1.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_60_days", config_data={"assessment_period_end": future_date_2.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_15_days", config_data={"assessment_period_end": future_date_3.strftime("%d %B %Y %I:%M%p")}
        )

        result = Configuration.objects.get_default_config()

        # Should return the earliest future date (15 days)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "config_15_days")

    def test_get_default_config_excludes_past_configs(self):
        """Test that get_default_config excludes configs with past end dates."""
        now = timezone.now()

        # Create configs with past dates
        past_date_1 = now - timedelta(days=10)
        past_date_2 = now - timedelta(days=30)

        Configuration.objects.create(
            name="config_past_1", config_data={"assessment_period_end": past_date_1.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_past_2", config_data={"assessment_period_end": past_date_2.strftime("%d %B %Y %I:%M%p")}
        )

        result = Configuration.objects.get_default_config()

        # Should return None as all configs are in the past
        self.assertIsNone(result)

    def test_get_default_config_mixed_past_and_future(self):
        """Test get_default_config with mix of past and future configs."""
        now = timezone.now()

        # Create mix of past and future configs
        past_date = now - timedelta(days=10)
        future_date_1 = now + timedelta(days=20)
        future_date_2 = now + timedelta(days=40)

        Configuration.objects.create(
            name="config_past", config_data={"assessment_period_end": past_date.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_future_near", config_data={"assessment_period_end": future_date_1.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_future_far", config_data={"assessment_period_end": future_date_2.strftime("%d %B %Y %I:%M%p")}
        )

        result = Configuration.objects.get_default_config()

        # Should return the nearest future config
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "config_future_near")

    def test_get_default_config_no_configs(self):
        """Test get_default_config when no configs exist."""
        result = Configuration.objects.get_default_config()

        self.assertIsNone(result)

    def test_get_default_config_with_same_end_date(self):
        """Test get_default_config when multiple configs have the same end date."""
        now = timezone.now()
        future_date = now + timedelta(days=30)

        Configuration.objects.create(
            name="config_a", config_data={"assessment_period_end": future_date.strftime("%d %B %Y %I:%M%p")}
        )
        Configuration.objects.create(
            name="config_b", config_data={"assessment_period_end": future_date.strftime("%d %B %Y %I:%M%p")}
        )

        result = Configuration.objects.get_default_config()

        # Should return one of them (first() will return the first one)
        self.assertIsNotNone(result)
        self.assertIn(result.name, ["config_a", "config_b"])

    def test_get_default_config_edge_case_now(self):
        """Test get_default_config with end date very close to now."""
        now = timezone.now()

        # Create config ending in 1 second (should still be considered future)
        future_date = now + timedelta(seconds=1)

        Configuration.objects.create(
            name="config_now", config_data={"assessment_period_end": future_date.strftime("%d %B %Y %I:%M%p")}
        )

        result = Configuration.objects.get_default_config()

        # Should return the config as it's technically in the future
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "config_now")
