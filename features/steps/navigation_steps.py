import csv
import json
import os
import re
import uuid
from collections import defaultdict
from pathlib import Path
from time import sleep
from typing import Any, Literal, Optional

from behave import step, then
from behave.runner import Context
from playwright.sync_api import expect
from pypdf import PdfReader

from features.util import delete_model, exists_model, get_model, run_async_orm


@step('a button with text "{text}"')
def find_button_with_text(context: Context, text: str):
    """
    Summary: This function steps through a given scenario to find and click an element based on its text content.

    :param context: The current context object containing the necessary data for the scenario.
    :return: None
    """
    page = context.page
    expect(page.get_by_role("button", name=text)).to_be_visible()


@step('link with text "{text}"')
def find_link_with_text(context: Context, text: str):
    """
    :type context:Context
    """
    page = context.page
    expect(page.get_by_role("link", name=text)).to_be_visible()


@step('click button with text "{text}"')
def click_button_with_text(context: Context, text: str):
    """
    Summary: This function steps through a given scenario to find and click an element based on its text content.

    :param context: The current context object containing the necessary data for the scenario.
    :return: None
    """
    if "think_time" in context:
        sleep(context.think_time)
    page = context.page
    page.get_by_role("button", name=text).click()


@step('click link with text "{text}"')
def click_link_with_text(context: Context, text: str):
    """
    :type context:Context
    """
    if "think_time" in context:
        sleep(context.think_time)
    page = context.page
    page.get_by_role("link", name=text, exact=True).click()


@step('click link in summary card row "{key}" with text "{text}"')
def click_summary_card_link_with_text(context: Context, key: str, text: str):
    page = context.page
    row = page.locator(".govuk-summary-list__row", has_text=key)
    expect(row).to_be_visible()
    row.get_by_role("link", name=text).click()


@step('current organisation is set to "{current_organisation}"')
def set_current_organisation(context: Context, current_organisation: str):
    """
    Sets the current organisation in the application.
    Checks if the organisation change link is present. If not, assumes organisation is already set.
    :param context: The context object containing page and other shared data.
    :param current_organisation: The name of the organisation to be set as the current one.
    :return: None
    """
    page = context.page
    org_change_link = page.locator("#change_organisation")
    if org_change_link.is_visible():
        org_change_link.click()
        page.locator(f"tr:has(th span:has-text('{current_organisation}')) button").click()
    else:
        print(f"No organisation change link found. So assuming organisation is already set to {current_organisation}")


@step('check user is logged in against organisation "{organisation}"')
def get_current_logged_in_organisation(context: Context, organisation: str):
    """
    This can only be called from the my account page.
    :type context:Context
    """
    page = context.page
    logged_in_org_locator = page.locator("#logged-in-as-org-name")
    expect(logged_in_org_locator).to_have_text(organisation)


@step('enter text "{text}" for id "{id}"')
def enter_text(context: Context, text: str, id: str):
    """
    :type context:Context
    """
    page = context.page
    page.locator(f"#{id}").fill(text)


@step('select radio with value "{value}"')
def select_radio(context: Context, value: str):
    """
    :type context:Context
    """
    page = context.page
    page.locator(f"input[type='radio'][value='{value}']").check()


@step('select checkbox with value "{value}"')
def select_checkbox(context: Context, value: str):
    """
    :type context:Context
    """
    page = context.page
    page.locator(f"input[type='checkbox'][value='{value}']").check()


@step('select select box with value "{value}"')
def select_select(context: Context, value: str):
    page = context.page
    selector = page.locator(".govuk-select")
    expect(selector).to_be_visible()
    selector.select_option(value)


@then('they should see a summary card with header "{header}" keys "{keys}" and values "{values}"')
def summary_card_with_content(context: Context, header: str, keys: str, values: str):
    """
    This checks a summary card content in the ui against expected content
    :type context:Context
    """
    key_list = [key.strip() for key in keys.split(",")]
    value_list = [r.strip() for r in next(csv.reader([values], delimiter=",", quotechar="'"))]

    expected = {key_list[i]: value_list[i] for i in range(len(key_list))}
    page = context.page
    summary_card = page.locator(".govuk-summary-card", has_text=header)
    expect(summary_card).to_be_visible()
    rows = summary_card.locator(".govuk-summary-list__row").all()
    actual = {}
    print(f"Summary card: {summary_card.inner_html()} row count: {len(rows)}")
    for row in rows:
        expect(row).to_be_visible()
        key = row.locator(".govuk-summary-list__key").inner_text()
        value = row.locator(".govuk-summary-list__value").inner_text()

        actual[key.strip()] = value.strip()
    assert actual == expected, f"Summary card mismatch.\nExpected: {expected}\nActual: {actual}"


@step('click link in table row containing value "{value}" with text "{link_text}"')
def click_link_in_table_role_with_value(context: Context, link_text: str, value: str):
    """
    Clicks a link on a specific row of a table with given text
    """
    page = context.page
    row = page.locator("tr").filter(has_text=value)
    expect(row).to_be_visible()
    row.get_by_role("link", name=link_text).click()


@then('they should see a table including value "{value}"')
def table_with_value(context: Context, value: str):
    """
    Checks a table contains a value
    """
    page = context.page
    table = page.locator(".govuk-table")
    expect(table).to_be_visible()
    value_cell = table.get_by_text(value)
    expect(value_cell).to_be_visible()


@then('they should see a table without value "{value}" in any row')
def table_without_value(context: Context, value: str):
    """
    Checks a table does not contain a value
    """
    page = context.page
    table = page.locator(".govuk-table")
    expect(table).to_be_visible()
    value_cell = table.get_by_text(value)
    expect(value_cell).to_have_count(0)


@step('System "{existence_type}" exist with name "{system_name}" for organisation "{org_name}"')
def check_system_exists(context: Context, existence_type: Literal["does", "does not"], system_name: str, org_name: str):
    """
    Checks if a system with the given name and organization exists or does not exist.
    Assertion is based on the existence_type parameter
    :param context:
    :param existence_type: Literal["does", "does not"] - Indicates whether the system should exist or not.
    :param system_name: str - Name of the system to check.
    :param org_name: str - Name of the organization associated with the system.
    :return: None
    """
    from webcaf.webcaf.models import System

    model_exists = exists_model(System, name=system_name, organisation__name=org_name)
    if existence_type == "does":
        assert model_exists, f"System {system_name} for organisation {org_name} does not exist"
    else:
        assert not model_exists, f"System {system_name} for organisation {org_name} exists"


@step('there is no system with name "{system_name}" for organisation "{org_name}"')
def make_sure_no_system(context: Context, system_name: str, org_name: str):
    """ """
    from webcaf.webcaf.models import System

    if exists_model(System, name=system_name, organisation__name=org_name):
        print(f"Deleting system {system_name} for organisation {org_name}")
        model = get_model(System, name=system_name, organisation__name=org_name)
        delete_model(model)


@step(
    'there is a "{caf_profile}" profile assessment  for "{system_name}", "{organisation_name}", for the period "{period}" in "{status}" status and data "{data_file}"'
)
def create_new_assessment(
    context: Context,
    caf_profile: str,
    system_name: str,
    organisation_name: str,
    period: str,
    status: str,
    data_file: Optional[str],
):
    """
    :type context: behave.runner.Context
    """
    from webcaf.webcaf.models import Assessment, Review, System

    def create_assessment() -> Assessment:
        initial_assessment_data = {}
        if data_file and data_file.strip():
            with open(Path(__file__).parent.parent / "data" / data_file, "r") as f:
                initial_assessment_data = json.loads(f.read())
        assessment = Assessment.objects.create(
            system=System.objects.get(name=system_name, organisation__name=organisation_name),
            caf_profile=caf_profile,
            assessment_period=period,
            status=status,
            review_type="peer_review",
            framework="caf32",
            assessments_data=initial_assessment_data,
        )
        assessment.save()
        if assessment.status == "submitted":
            # Simulate the submission of the assessment by creating a review
            Review.objects.create(
                assessment=assessment,
            )

        return assessment

    assessment_created = run_async_orm(create_assessment)
    context.current_assessment_id = assessment_created.id
    print(f"Assessment {assessment_created.id} created")


@step('page has heading "{heading}"')
def confirm_heading_on_page(context: Context, heading: str):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    heading_element = page.locator("h1").filter(has_text=heading)
    expect(heading_element).to_be_visible()


@then('navigate to "{objective_text}"')
def select_objective(context: Context, objective_text: str):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    # Confirm we are on the edit page
    page.goto(f"{context.config.userdata.get('base_url')}/edit-draft-assessment/{context.current_assessment_id}/")
    page.wait_for_load_state("load")
    objective_links = page.locator("a").filter(has_text=re.compile("Objective"))
    objective_links.last.wait_for(state="visible")
    for i in range(objective_links.count()):
        text = objective_links.nth(i).inner_text()
        if objective_text.strip() == text.strip():
            print("Found:", text)
            objective_links.nth(i).click()
            context.objective_text = text
            break


@step('Fill outcome "{outcome_text}" with "{section_keys}" with "{section_values}"')
def fill_outcome(context: Context, outcome_text: str, section_keys: str, section_values: str):
    """
    :type context: behave.runner.Context
    """
    page = context.page
    # Navigate to the section
    divs = page.locator("div.govuk-summary-list__row")
    divs.last.wait_for(state="visible")
    div = None
    div = find_div_with_text(div, divs, outcome_text, "dt")

    # Inside that div, find the <a> with "Add your answers"
    link = div.locator("a")
    link.wait_for(state="visible")
    for i in range(link.count()):
        text = link.nth(i).inner_text()
        if "Add answers to" in text.strip() and re.sub(r"[^A-Za-z0-9]", "", outcome_text) in re.sub(
            r"[^A-Za-z0-9]", "", text
        ):
            link = link.nth(i)
            link.click()
            break
    # Now fill the answers
    print("Filling answers")
    section_filling_criteria = dict(
        zip([s.strip() for s in section_keys.split(",")], [s.strip() for s in section_values.split(",")])
    )
    checkboxes = page.locator("input[class='govuk-checkboxes__input']")
    checkboxes.last.wait_for(state="visible")
    checkbox_elements_by_category = defaultdict(list)
    for i in range(checkboxes.count()):
        checkbox = checkboxes.nth(i)
        checkbox_name = checkbox.get_attribute("name")
        if checkbox_name.startswith("achieved"):
            checkbox_elements_by_category["achieved"].append(checkbox)
        elif checkbox_name.startswith("not-achieved"):
            checkbox_elements_by_category["not-achieved"].append(checkbox)
        elif checkbox_name.startswith("partially-achieved"):
            checkbox_elements_by_category["partially-achieved"].append(checkbox)

    for key, value in section_filling_criteria.items():
        elements = checkbox_elements_by_category[key]
        if value == "all":
            for element in elements:
                element.check()
        elif value == "some":
            # We only click predictable elements as otherwise we cannot compare the results in the end
            # with static test data
            if len(elements) > 0:
                elements[0].check()
            if len(elements) >= 3:
                elements[2].check()
        else:
            print(f"Not selecting any elements for {key} as {value} is set")
    context.outcome_text = outcome_text
    # Now submit the form
    page.locator("button[type='submit']").wait_for(state="visible")
    page.locator("button[type='submit']").click()


def find_div_with_text(div: Any | None, divs, child_text: str, child_container: str) -> Any:
    for i in range(divs.count()):
        text = divs.nth(i).locator(child_container).inner_text()
        print(f"Checking {text} with {child_text}")
        if child_text.strip() == replace_html_spaces(text):
            print("Found:", text)
            div = divs.nth(i)
            break
    assert div is not None, f"No div found with text {child_text} divs {divs.all_inner_texts()}"
    div.wait_for(state="visible")
    return div


def replace_html_spaces(text) -> str:
    return text.replace("&nbsp;", " ").replace("\xa0", " ").strip()


@step('Fill outcome confirm status "{outcome_status}" with "{outcome_comment}"')
def fill_outcome_confirm(context: Context, outcome_status: str, outcome_comment: str):
    page = context.page
    # We are on the confirmation page now
    heading_element = page.locator("h1").filter(has_text=f"{context.outcome_text} Outcome")
    heading_element.wait_for(state="visible")

    status_element = page.locator("h2").filter(has_text=f"Status: {outcome_status}")
    status_element.wait_for(state="visible")

    # Load all radio on the page
    radios = page.locator("input[type='radio']")
    radios.last.wait_for(state="visible")
    radio_checked = False
    for i in range(radios.count()):
        radio = radios.nth(i)
        radio_id = radio.get_attribute("id")
        label = page.locator(f"label[for='{radio_id}']")
        label_text = label.inner_text()
        if label_text == "Confirm, and write a contributing outcome summary":
            radio.check()
            radio_checked = True
            break

    assert radio_checked, "No radio button found for confirming outcome"
    enter_text(context, outcome_comment, "id_confirm_outcome_confirm_comment")
    page.locator("button[type='submit']").wait_for(state="visible")
    page.locator("button[type='submit']").click()


@step("get assessment id from url and add to context")
def add_assessment_id_to_context(context: Context):
    url = context.page.url
    assessment_id = url.strip("/").split("/")[-1]
    context.current_assessment_id = assessment_id


@then('should see an error summary with error link text "{text}"')
def error_summary_with_link_text(context: Context, text: str):
    page = context.page
    error_summary = page.locator(".govuk-error-summary")
    expect(error_summary).to_be_visible()
    error_link = error_summary.locator("a", has_text=text)
    expect(error_link).to_be_visible()


@then('should see an error message with text "{text}"')
def error_message_with_text(context: Context, text: str):
    page = context.page
    error_message = page.locator(".govuk-error-message", has_text=text)
    expect(error_message).to_be_visible()


@step('navigate to page "{target_page}"')
def navigate_to_given_page(context: Context, target_page: str):
    context.page.goto(context.config.userdata["base_url"] + target_page)
    context.page.wait_for_load_state("load")


@step('download file by clicking button "{button_text}"')
def download_by_clicking_button(context: Context, button_text: str):
    page = context.page
    parent_path = Path(__file__).parent.parent.parent / "artifacts"
    # download the PDF in a tab. It is not possible to directly access the content with playwright
    with page.expect_popup() as popup_info:
        button = page.get_by_role("button", name=button_text)
        button.first.wait_for(state="visible")
        button.first.click()
    popup = popup_info.value
    popup.wait_for_load_state("networkidle")

    # Download the PDF directly and save it to the artefacts folder
    # This is necessary as the PDF is not available in the browser directly (it is inlined)
    pdf_url = context.config.userdata["base_url"] + f"/download-submitted-assessment/{context.current_assessment_id}"
    print("Using pdf url: ", pdf_url)
    response = page.request.get(pdf_url)
    pdf_bytes = response.body()
    os.makedirs(parent_path / "pdfs", exist_ok=True)
    file_path = Path(parent_path / f"pdfs/{uuid.uuid4()}.pdf")
    file_path.write_bytes(pdf_bytes)
    popup.close()
    context.pdf_file_path = file_path
    print(f"Downloaded PDF to {parent_path}")


@step("confirm current assessment information is on the downloaded pdf")
def check_pdf_contains_text(context: Context):
    pdf_file_path = context.pdf_file_path
    from webcaf.webcaf.models import Assessment

    with open(pdf_file_path, "rb") as f:
        pdf_reader = PdfReader(f)
        page = pdf_reader.pages[0]
        text = page.extract_text()
        print(text)
        current_assessment_id = context.current_assessment_id
        current_assessment = get_model(Assessment, id=current_assessment_id)
        assert current_assessment.reference in text, "Expecting {current_assessment.reference} in PDF"


@step('cookies have been "{cookie_choice}"')
def step_impl(context: Context, cookie_choice: str):
    """
    :type context: behave.runner.Context
    """
    if cookie_choice == "accepted":
        button = context.page.get_by_role("button", name="Accept analytics cookies")

    else:
        button = context.page.get_by_role("button", name="Reject analytics cookies")
    if button.is_visible():
        button.click()
    hide_message_button = context.page.get_by_role("button", name="Hide this message")
    if hide_message_button.is_visible():
        hide_message_button.click()


@then('should see "{options}" in select box options')
def expected_options_in_select_box(context: Context, options: str):
    page = context.page
    options_locator = page.locator("#system_id > option")
    options_list = options.split(",")
    expect(options_locator).to_have_text(options_list)


@then('text with "{text}"')
def page_contains_text(context: Context, text: str):
    """
    Assert that the current page contains the given visible text anywhere.
    """
    page = context.page
    expect(page.get_by_text(text)).to_be_visible()


@then('they should see a table with header "{header}"')
def table_with_header(context: Context, header: str):
    """
    Assert that a GOV.UK styled table is visible and contains the given column header text.
    """
    page = context.page
    table = page.locator(".govuk-table")
    expect(table).to_be_visible()
    header_cell = table.locator("th").filter(has_text=header)
    expect(header_cell).to_be_visible()
