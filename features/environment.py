import os
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import allure
import django
from behave.model_type import Status
from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Lower, Replace
from playwright.sync_api import Page, sync_playwright

from features.one_login_simulator import configure_identity
from features.util import ORM_EXECUTOR, run_async_orm


def before_all(context):
    write_report_environment(context.config)
    print("Starting Django")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webcaf.settings")
    django.setup()

    # Start Playwright
    context.playwright = sync_playwright().start()
    headless_testing = context.config.userdata.get("headless_testing", "True").lower() == "true"
    context.browser = context.playwright.chromium.launch(headless=headless_testing)
    context.browser.new_context()
    context.page = context.browser.new_page()


def write_report_environment(config):
    """Record run metadata in the selected Allure results directory."""
    metadata = {
        "Environment": os.environ.get("SSO_MODE", "unknown"),
        "Base URL": config.userdata.get("base_url", "unknown"),
        "Branch": os.environ.get("FEATURE_TEST_BRANCH", "unknown"),
        "Commit SHA": os.environ.get("FEATURE_TEST_COMMIT", "unknown"),
        "Started at (UTC)": datetime.now(UTC).isoformat(),
        "Feature/tag filter": os.environ.get("FEATURE_TEST_ARGS") or "(none)",
    }
    for formatter, output in zip(config.format, config.outputs):
        if formatter != "allure_behave.formatter:AllureFormatter" or not output.name:
            continue
        results_dir = Path(output.name)
        results_dir.mkdir(parents=True, exist_ok=True)
        with (results_dir / "environment.properties").open("w", encoding="utf-8") as properties:
            for key, value in metadata.items():
                # Java properties use backslash escapes and one property per line.
                value = value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")
                properties.write(f"{key.replace(' ', r'\ ')}={value}\n")


def before_scenario(context, scenario):
    context.page.context.clear_cookies()
    context.page.context.clear_permissions()
    simulator_url = os.environ.get("ONE_LOGIN_SIMULATOR_URL")
    if os.environ.get("SSO_MODE", "").lower() == "one-login" and simulator_url:
        configure_identity("alice@example.gov.uk", True, simulator_url)
    if "think_time" in context:
        delattr(context, "think_time")

    # Also clear storage for all origins
    context.page.context.add_cookies([])  # Wipe all cookies

    def clear_db():
        print("****************** Clearing DB *****************************")
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import (
            Assessment,
            Configuration,
            Organisation,
            UserProfile,
        )

        test_user_emails = [
            email.strip() for email in context.config.userdata.get("user_emails", "").split(",") if email.strip()
        ]

        Assessment.objects.filter(created_by__email__in=test_user_emails).delete()

        Assessment.objects.filter(
            system__organisation__name__in=[
                org.strip() for org in context.config.userdata.get("organisation_names", "").split(",")
            ]
        ).delete()

        UserProfile.objects.filter(
            user__email__in=test_user_emails,
            user__is_staff=False,
            user__is_superuser=False,
        ).delete()

        Organisation.objects.annotate(normalized_name=Replace(Lower(F("name")), Value(" "), Value(""))).filter(
            normalized_name__in=[
                org.lower().replace(" ", "").strip()
                for org in context.config.userdata.get("organisation_names", "").split(",")
            ]
        ).delete()

        User.objects.filter(email__in=test_user_emails, is_staff=False, is_superuser=False).delete()

        Configuration.objects.all().delete()
        # We need to create a default configuration for testing purposes.
        assessment_period, assessment_year = get_current_assessment_period()
        Configuration.objects.create(
            name="default",
            config_data={
                "default_framework": settings.DEFAULT_CAF_FRAMEWORK,
                "current_assessment_period": assessment_period,
                "assessment_period_end": f"31 March {assessment_year} 11:59pm",
            },
        )

    run_async_orm(clear_db)


def get_current_assessment_period() -> tuple[str, str]:
    """
    Generate the current assessment period based on the current date.
    if the date is less than 11:59pm of 31st March, then the assessment period is current year -1/current year, else
    it is current year/current year +1

    Returns:
        tuple[str, str]: A tuple containing the assessment period and the assessment year
    """
    current_date = datetime.now()
    # Determines the assessment period based on the current date
    if (
        current_date.month < 3
        or (current_date.month == 3 and current_date.day < 31)
        or (current_date.month == 3 and current_date.day == 31 and current_date.hour < 23 and current_date.minute < 59)
    ):
        return f"{current_date.year - 1}/{current_date.year}".replace("20", ""), f"{current_date.year}"
    else:
        return f"{current_date.year}/{current_date.year + 1}".replace("20", ""), f"{current_date.year + 1}"


def after_scenario(context, scenario):
    print(f"After Scenario: {scenario.status}")
    if scenario.status in [Status.failed, Status.error]:
        parent_path = Path(__file__).parent.parent
        print(f"Saving screenshot and HTML for failed scenario {parent_path} {scenario.name}")
        os.makedirs(parent_path / "artifacts", exist_ok=True)  # Folder for all failure artifacts

        if hasattr(context, "page") and isinstance(context.page, Page):
            # Keep filenames readable while distinguishing names and source locations.
            readable_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", scenario.name).strip("_")[:100] or "scenario"
            scenario_id = f"{scenario.filename}:{scenario.line}:{scenario.name}"
            safe_name = f"{readable_name}_{sha256(scenario_id.encode('utf-8')).hexdigest()[:16]}"

            # Save screenshot
            screenshot_path = f"artifacts/{safe_name}.png"
            screenshot = context.page.screenshot(path=screenshot_path, full_page=True)
            allure.attach(
                screenshot,
                name="Screenshot",
                attachment_type=allure.attachment_type.PNG,
            )

            # Save HTML
            html_path = f"artifacts/{safe_name}.html"
            html = context.page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            allure.attach(html, name="Page HTML", attachment_type=allure.attachment_type.HTML)

            print(f"📸 Screenshot saved: {screenshot_path}")
            print(f"💾 HTML saved: {html_path}")


def after_all(context):
    context.browser.close()
    context.playwright.stop()
    ORM_EXECUTOR.shutdown(wait=True)
