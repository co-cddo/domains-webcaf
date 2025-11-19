from time import sleep

from behave import given, step, then
from behave.runner import Context
from django.db import connection
from playwright.sync_api import Page, expect

from features.util import run_async_orm


@step("the application is running")
def go_to_landing_page(context):
    context.page.goto(context.config.userdata["base_url"])
    expect(context.page).to_have_title("Start page  - Complete a WebCAF self-assessment - GOV.UK")


@step("the user is on the admin login page")
def go_to_admin_landing_page(context):
    context.page.goto(context.config.userdata["base_url"] + "/admin/")
    expect(context.page).to_have_title("Log in | Django site admin")


@given("Think time {time} seconds")
def set_think_time(context, time):
    context.think_time = int(time)


@given('the user "{user_name}" exists')
def confirm_user_exists(context, user_name):
    from django.contrib.auth.models import User

    print(f"Creating user {user_name}")
    user, _ = run_async_orm(User.objects.get_or_create, email=user_name, username=user_name)
    print(f"user = {user} is in the system now")


@step('no login attempt blocks for the user "{user_name}"')
def clear_login_attempt_blocks(context, user_name):
    def reset_user():
        with connection.cursor() as cursor:
            cursor.execute("delete from axes_accessattempt where username = %s", [user_name])
            print(f"Deleted {cursor.rowcount} rows")
            cursor.execute("delete from axes_accessfailurelog where username = %s", [user_name])
            print(f"Deleted {cursor.rowcount} rows")

    run_async_orm(reset_user)


@given('the user "{user_name}" with the "{password}" exists in the backend')
def confirm_backend_user_exists(context, user_name, password):
    from django.contrib.auth.models import User

    print(f"Creating user {user_name}")

    def create_user():
        the_user, _ = User.objects.get_or_create(
            username=user_name,
        )
        the_user.set_password(password)
        the_user.is_active = True
        the_user.is_superuser = True
        the_user.is_staff = True
        the_user.save()
        return the_user

    user = run_async_orm(create_user)
    print(f"user = {user} is in the system now")


@given('Organisation "{organisation_name}" of type "{organisation_type}" exists with systems "{systems}"')
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
            System.objects.get_or_create(
                name=system_name.strip(),
                organisation=organisation,
            )
            for system_name in systems.split(",")
        ]
    )
    context.organisation = organisation


@given('User "{user_name}" has the profile "{role}" assigned in "{organisation_name}"')
def assign_user_profile(context, user_name, role, organisation_name):
    """
    :type context: behave.runner.Context
    """

    def create_profile():
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import Organisation, UserProfile

        return UserProfile.objects.get_or_create(
            user=User.objects.get(email=user_name),
            organisation=Organisation.objects.get(name=organisation_name),
            role=UserProfile.get_role_id(role),
        )

    run_async_orm(create_profile)


@step('the user logs in with username  "{user_name}" and password "{password}"')
def user_logging_in(context, user_name, password):
    page = context.page
    page.get_by_text("Sign in").click()
    if "think_time" in context:
        sleep(context.think_time)
    expect(page.get_by_role("heading")).to_contain_text("Log in to Your Account")

    page.get_by_placeholder("email address").fill(user_name)
    page.get_by_placeholder("password").fill(password)
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_role("heading")).to_contain_text("Grant Access")
    page.get_by_role("button", name="Grant Access").click()
    context.current_email = user_name


@then('they should see page title "{page_title}"')
def check_page_title(context, page_title):
    if "think_time" in context:
        sleep(context.think_time)
    page = context.page
    expect(page).to_have_title(page_title)


@then('page contains text "{page_text}" in banner')
def check_page_message(context: Context, page_text: str):
    """
    :type context: behave.runner.Context
    :type page_text: str
    """
    page: Page = context.page
    expect(page.locator("p.govuk-notification-banner__heading")).to_contain_text(page_text)
