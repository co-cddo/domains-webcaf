from time import sleep

from behave import given, step, then, when
from playwright.sync_api import expect

from features.util import get_model, run_async_orm


@given("the application is running")
def go_to_landing_page(context):
    context.page.goto(context.config.userdata["base_url"])
    expect(context.page).to_have_title("Start page  - Submit a CAF self-assessment for a system")


@given("Think time {time} seconds")
def set_think_time(context, time):
    context.think_time = int(time)


@given("the user {user_name} exists")
def confirm_user_exists(context, user_name):
    from django.contrib.auth.models import User

    print(f"Creating user {user_name}")
    user, _ = run_async_orm(User.objects.get_or_create, email=user_name, username=user_name)
    print(f"user = {user} is in the system now")


@given("Organisation {organisation_name} of type {organisation_type} exists with systems {systems}")
def create_org_and_systems(context, organisation_name, organisation_type, systems):
    """
    :type context: behave.runner.Context
    """

    from webcaf.webcaf.models import Organisation, System

    print(f"Creating organisation {organisation_name}")
    organisation, _ = run_async_orm(
        Organisation.objects.get_or_create,
        name=organisation_name,
        organisation_type=Organisation.get_type_id(organisation_type),
    )
    run_async_orm(
        lambda: [
            System.objects.get_or_create(name=system_name.strip(), organisation=organisation)
            for system_name in systems.split(",")
        ]
    )


@given("User {user_name} has the profile {role} assigned in {organisation_name}")
def assign_user_profile(context, user_name, role, organisation_name):
    """
    :type context: behave.runner.Context
    """

    from django.contrib.auth.models import User

    from webcaf.webcaf.models import Organisation, UserProfile

    organisation = get_model(Organisation, name=organisation_name)
    users = run_async_orm(lambda: list(User.objects.all()))
    for user in users:
        print(f"user name = {user.username} email={user.email}")
    print(f"Looking for the user {user_name}")
    user = get_model(User, email=user_name)
    run_async_orm(
        UserProfile.objects.get_or_create, user=user, organisation=organisation, role=UserProfile.get_role_id(role)
    )


@when("the user logs in with username {user_name} and password {password}")
def user_logging_in(context, user_name, password):
    page = context.page
    page.get_by_text("Sign in").click()
    sleep(context.think_time)
    expect(page.get_by_role("heading")).to_contain_text("Log in to Your Account")

    page.get_by_placeholder("email address").fill(user_name.strip())
    page.get_by_placeholder("password").fill(password.strip())
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_role("heading")).to_contain_text("Grant Access")
    page.get_by_role("button", name="Grant Access").click()


@then("they should see page title {page_title}")
def check_page_title(context, page_title):
    sleep(context.think_time)
    page = context.page
    expect(page).to_have_title(page_title)


@step("page contains text {page_text} in banner")
def check_page_message(context, page_text):
    """
    :type context: behave.runner.Context
    :type page_text: str
    """
    page = context.page
    expect(page.locator("p.govuk-notification-banner__heading")).to_contain_text(page_text)


@step("page contains text {page_text} in paragraph")
def check_page_paragraph(context, page_text):
    """
    :type context: behave.runner.Context
    :type page_text: str
    """
    page = context.page
    expect(page.locator("p.govuk-body:not(.govuk-hint)")).to_contain_text(page_text)


@step("clck the link with the text {link_text}")
def click_link_with_text(context, link_text):
    page = context.page
    page.get_by_text(link_text).click()


@step("confirm element {element_selector} with the text {text} exists")
def confirm_element_exists_with_text(context, element_selector, text):
    page = context.page
    expect(page.locator(element_selector)).to_contain_text(text)
