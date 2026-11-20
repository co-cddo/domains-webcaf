import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import behave.runner
from behave import step, then
from deepdiff import DeepDiff
from navigation_steps import click_link_with_text

from features.util import create_model, get_model, update_model


@step("Enter IAR period")
def enter_review_period(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    current_date = datetime.now()
    six_months_ago = current_date.replace(month=current_date.month - 6)
    click_link_with_text(context, "Enter Independent Assurance Review (IAR) period")
    textarea = page.locator("input[id^='id_start_date_day']")
    textarea.fill(str(six_months_ago.day))
    textarea = page.locator("input[id^='id_start_date_month']")
    textarea.fill(str(six_months_ago.month))
    textarea = page.locator("input[id^='id_start_date_year']")
    textarea.fill(str(six_months_ago.year))
    textarea = page.locator("input[id^='id_end_date_day']")
    textarea.fill(str(six_months_ago.day))
    textarea = page.locator("input[id^='id_end_date_month']")
    textarea.fill(str(six_months_ago.month))
    textarea = page.locator("input[id^='id_end_date_year']")
    textarea.fill(str(six_months_ago.year))

    page.get_by_role("button", name="Save and continue").click()


@step("Add company details")
def add_company_details(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Add company details")
    textarea = page.locator("input[id^='id_company_name']")
    textarea.fill("Test Company")
    textarea = page.locator("input[id^='id_lead_assessor_name']")
    textarea.fill("Test Lead Assessor")
    textarea = page.locator("input[id^='id_lead_assessor_email']")
    textarea.fill("test.lead.assessor@example.com")

    page.get_by_role("button", name="Save and continue").click()


@step("Add review method")
def add_review_method(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Describe review method")
    textarea = page.locator("textarea[id^='id_text']")
    textarea.fill("There is no method for my review :)")

    page.get_by_role("button", name="Save and continue").click()


@step("Add quality of self assessment")
def add_quality_of_assessment(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    click_link_with_text(context, "Describe the quality of the self-assessment")
    textarea = page.locator("textarea[id^='id_text']")
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
        f"{context.config.userdata.get('base_url')}/review/{context.current_review_id}/recommendations/{igp[0]}/{igp[:4]}"
    )
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
def review_history(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    page.goto(f"{context.config.userdata.get('base_url')}/review/{context.current_review_id}/revisions")


@step('confirm review data has expected data "{data_file}"')
def check_review_data(context: behave.runner.Context, data_file: str):
    """
    :type context: behave.runner.Context
    :type data_file: str
    """
    from webcaf.webcaf.models import Review

    with open(Path(__file__).parent.parent / "data" / data_file, "r") as f:
        json_data = f.read()
        expected = json.loads(json_data)
        actual = get_model(Review, id=context.current_review_id).review_data
        diff = DeepDiff(
            expected,
            actual,
            ignore_order=True,
            # Ignore the following paths as they are dynamic and will change with each test run
            exclude_paths={
                "root['assessor_response_data']['additional_information']['iar_period'][*]",
                "root['assessor_response_data']['system_and_scope']['completed_data']['review_details']['self_assessment_reference_number']",
                "root['review_completion']['review_completed_at']",
                "root['review_finalised']['review_finalised_at']",
            },
        )

        assert diff == {}, f"JSON differences found: {diff}"


@step('there is a review assigned to the current assessment with the data "{data_file}" and status "{status}"')
def update_review_data(context: behave.runner.Context, data_file: str, status: str):
    """
    :type context: behave.runner.Context
    :type data_file: str
    :type status: str
    """
    from webcaf.webcaf.models import Assessment, Review

    if data_file and data_file.strip():
        with open(Path(__file__).parent.parent / "data" / data_file, "r") as f:
            initial_review_data = json.loads(f.read())
    assessment = get_model(Assessment, uid=context.current_assessment_id)
    review = get_model(
        Review,
        assessment=assessment,
    )
    if not review:
        review = create_model(
            Review,
            assessment=assessment,
            review_data=initial_review_data if "initial_review_data" in locals() else {},
            status=status,
        )
        review.save()
    else:
        update_model(
            review,
            review_data=initial_review_data if "initial_review_data" in locals() else {},
            status=status,
        )
    context.current_review_id = review.id


@then('the user should be able to download the "{file_type}" report "{path_}" and save as "{attachment_id}"')
def download_file(context: behave.runner.Context, file_type: str, path_: str, attachment_id: str):
    """
    :type context: behave.runner.Context
    """
    parent_path = Path(__file__).parent.parent.parent / "artifacts"

    for token, value in (
        ({"<tip_id>": str(context.current_tip_id)} if hasattr(context, "current_tip_id") else {})
        | ({"<review_id>": str(context.current_review_id)} if hasattr(context, "current_review_id") else {})
    ).items():
        path_ = path_.replace(token, value)

    _url = context.config.userdata["base_url"] + path_
    page = context.page
    print(f"Using {file_type} url: ", _url)
    response = page.request.get(_url)
    assert response.status == 200
    pdf_bytes = response.body()
    os.makedirs(parent_path / file_type, exist_ok=True)
    file_path = Path(parent_path / f"{file_type}/{attachment_id}-{uuid.uuid4()}.{file_type}")
    file_path.write_bytes(pdf_bytes)
    context.use_or_assign_param(attachment_id, file_path)
    print(f"Downloaded {file_type} to {parent_path}")


@step("store current tip id from the url")
def save_current_tip_id(context: behave.runner.Context):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    tip_id = page.url.strip("/").split("/")[-1]
    context.current_tip_id = tip_id
