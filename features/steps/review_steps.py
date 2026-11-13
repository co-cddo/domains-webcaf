import json
from datetime import datetime
from pathlib import Path

import behave.runner
from behave import *
from deepdiff import DeepDiff

from features.util import get_model
from navigation_steps import click_link_with_text


@step("Enter IAR period")
def step_impl(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    current_date = datetime.now()
    six_months_ago = current_date.replace(month=current_date.month - 6)
    click_link_with_text(context, "Enter Independent Assurance Review (IAR) period")
    textarea = page.locator(f"input[id^='id_start_date_day']")
    textarea.fill(str(six_months_ago.day))
    textarea = page.locator(f"input[id^='id_start_date_month']")
    textarea.fill(str(six_months_ago.month))
    textarea = page.locator(f"input[id^='id_start_date_year']")
    textarea.fill(str(six_months_ago.year))
    textarea = page.locator(f"input[id^='id_end_date_day']")
    textarea.fill(str(six_months_ago.day))
    textarea = page.locator(f"input[id^='id_end_date_month']")
    textarea.fill(str(six_months_ago.month))
    textarea = page.locator(f"input[id^='id_end_date_year']")
    textarea.fill(str(six_months_ago.year))

    page.get_by_role("button", name="Save and continue").click()


@step("Add company details")
def step_impl(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Add company details")
    textarea = page.locator(f"input[id^='id_company_name']")
    textarea.fill("Test Company")
    textarea = page.locator(f"input[id^='id_lead_assessor_name']")
    textarea.fill("Test Lead Assessor")
    textarea = page.locator(f"input[id^='id_lead_assessor_email']")
    textarea.fill("test.lead.assessor@example.com")

    page.get_by_role("button", name="Save and continue").click()


@step("Add review method")
def step_impl(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Describe review method")
    textarea = page.locator(f"textarea[id^='id_text']")
    textarea.fill("There is no method for my review :)")

    page.get_by_role("button", name="Save and continue").click()


@step("Add quality of self assessment")
def step_impl(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Describe the quality of the self-assessment")
    textarea = page.locator(f"textarea[id^='id_text']")
    textarea.fill("Top quality :)")

    page.get_by_role("button", name="Save and continue").click()


@step('add review recommendation for "{igp}" with "{recommendation}"')
def add_review_recommendation(context: behave.runner.Context, igp: str, recommendation: str):
    """
    :type context: behave.runner.Context
    :type igp: str
    :type recommendation: str
    """
    page = context.page
    page.goto(
        f"{context.config.userdata.get('base_url')}/review/{context.current_review_id}/recommendations/{igp[0]}/{igp[:4]}")
    page.locator("#id_form-0-title").fill(f"Title {igp}")
    page.locator("#id_form-0-text").fill(recommendation)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Save and return").click()


@then("Navigate back to the review summary page")
def navigate_back_to_review_summary(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    page.goto(f"{context.config.userdata.get('base_url')}/review/{context.current_review_id}/")


@then("Navigate to review history page")
def step_impl(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    page.goto(f"{context.config.userdata.get('base_url')}/review/{context.current_review_id}/revisions")


@step('confirm review data has expected data "{data_file}"')
def step_impl(context: behave.runner.Context, data_file: str):
    """
    :type context: behave.runner.Context
    :type data_file: str
    """
    from webcaf.webcaf.models import Review
    with (open(Path(__file__).parent.parent / "data" / data_file, "r") as f):
        json_data = f.read()
        expected = json.loads(json_data)
        actual = get_model(Review, id=context.current_review_id).review_data
        diff = DeepDiff(
            expected,
            actual,
            ignore_order=True,
            # Ignore the following paths as they are dynamic and will change with each test run
            exclude_paths={"root['assessor_response_data']['additional_information']['iar_period'][*]",
                           "root['assessor_response_data']['system_and_scope']['completed_data']['review_details']['self_assessment_reference_number']",
                           "root['review_completion']['review_completed_at']",
                           "root['review_finalised']['review_finalised_at']", }
        )

        assert diff == {}, f"JSON differences found: {diff}"
