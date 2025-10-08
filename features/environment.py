import os

import django
from django.db.models import F, Value
from django.db.models.functions import Lower, Replace
from playwright.sync_api import sync_playwright

from features.util import ORM_EXECUTOR, run_async_orm


def before_all(context):
    print("Starting Django")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webcaf.settings")
    django.setup()

    # Start Playwright
    context.playwright = sync_playwright().start()
    headless_testing = context.config.userdata.get("headless_testing", "True").lower() == "true"
    context.browser = context.playwright.chromium.launch(headless=headless_testing)
    context.browser.new_context()
    context.page = context.browser.new_page()


def before_scenario(context, scenario):
    context.page.context.clear_cookies()
    context.page.context.clear_permissions()
    if "think_time" in context:
        delattr(context, "think_time")

    # Also clear storage for all origins
    context.page.context.add_cookies([])  # Wipe all cookies

    def clear_db():
        print("****************** Clearing DB *****************************")
        from webcaf.webcaf.models import Assessment, Organisation, UserProfile

        Assessment.objects.filter(
            created_by__email__in=[email.strip() for email in context.config.userdata.get("user_emails", "").split(",")]
        ).delete()

        Assessment.objects.filter(
            system__organisation__name__in=[
                org.strip() for org in context.config.userdata.get("organisation_names", "").split(",")
            ]
        ).delete()

        UserProfile.objects.filter(
            user__email__in=[email.strip() for email in context.config.userdata.get("user_emails", "").split(",")]
        ).delete()

        UserProfile.objects.filter(
            user__email__in=[email.strip() for email in context.config.userdata.get("user_emails", "").split(",")]
        ).delete()

        Organisation.objects.annotate(normalized_name=Replace(Lower(F("name")), Value(" "), Value(""))).filter(
            normalized_name__in=[
                org.lower().replace(" ", "").strip()
                for org in context.config.userdata.get("organisation_names", "").split(",")
            ]
        ).delete()

    run_async_orm(clear_db)


def after_scenario(context, scenario):
    pass


def after_all(context):
    context.browser.close()
    context.playwright.stop()
    ORM_EXECUTOR.shutdown(wait=True)
