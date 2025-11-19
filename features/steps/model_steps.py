import json
from pathlib import Path

from behave import step, then
from behave.runner import Context
from playwright.sync_api import expect

from features.util import create_model, exists_model, get_model, run_async_orm


@then('User model with email "{email}" should exist with "{user_role}" user role')
def check_user_with_profile_exists(context, email, user_role):
    from django.contrib.auth.models import User

    from webcaf.webcaf.models import UserProfile

    user_exists = exists_model(User, **{"email": email})

    # Assert that the user was found
    assert user_exists, f"User with email '{email}' was not found in the database."

    user = get_model(User, **{"email": email})
    user_profile = get_model(UserProfile, **{"user": user})
    assert user_profile.role == user_role


@then('User profile model with email "{email}" should not exist')
def check_user_does_not_exist(context, email):
    from django.contrib.auth.models import User

    from webcaf.webcaf.models import UserProfile

    user = get_model(User, **{"email": email})
    user_profile_exists = exists_model(UserProfile, **{"user": user})

    # Assert that the user was not found
    assert (
        not user_profile_exists
    ), f"User profile with email '{email}' was found in the database but should have been removed."


@then('check organisation "{org_name}" has type "{type}" and contact details "{name}" "{role}" and "{email}"')
def check_saved_org_has_expected_fields(context, org_name, type, name, role, email):
    from webcaf.webcaf.models import Organisation

    organisation = get_model(
        Organisation,
        **{
            "name": org_name,
        },
    )
    assert organisation.organisation_type == type, f"organisation  {org_name} type is not {type} as expected"
    assert organisation.contact_name == name, f"organisation {org_name} contact name is not {name} as expected"
    assert organisation.contact_role == role, f"organisation {org_name} contact role is not {role} as expected"
    assert organisation.contact_email == email, f"organisation {org_name} contact email is not {email} as expected"


@step('confirm the current assessment has expected data "{data_file_name}"')
def check_assessment_data(context: Context, data_file_name: str):
    """
    :type context: behave.runner.Context
    """
    from webcaf.webcaf.models import Assessment

    with open(Path(__file__).parent.parent / "data" / data_file_name, "r") as f:
        json_data = f.read()
        assert json.loads(json_data) == get_model(Assessment, id=context.current_assessment_id).assessments_data


@step('confirm current assessment is in "{expected_state}" state')
def confirm_assessment_status(context: Context, expected_state: str):
    """
    :type context: behave.runner.Context
    """
    from webcaf.webcaf.models import Assessment

    assessment = get_model(Assessment, id=context.current_assessment_id, last_updated_by__email=context.current_email)
    assessment.state = expected_state
    page = context.page
    # Confirm we have the correct reference displayed on the page.
    expect(page.locator("strong#reference_number").filter(has_text=assessment.reference)).to_be_visible()


@then(
    'confirm initial assessment has system "{system_name}" caf profile "{caf_profile}" and review type "{review_type}"'
)
def check_assessment_initial_setup(context: Context, system_name: str, caf_profile: str, review_type: str):
    """
    checks the initial persisted assessment has the expected values for system, caf profile
    and review type
    """
    from webcaf.webcaf.models import Assessment, System

    assessment = get_model(Assessment, id=context.current_assessment_id)
    system = get_model(System, id=assessment.system_id)
    assert system.name == system_name, f"System name persisted as '{system.name}' not expect '{system_name}'"
    assert (
        assessment.caf_profile == caf_profile
    ), f"Caf profile  persisted as '{assessment.caf_profile}' not expect '{caf_profile}'"
    assert (
        assessment.review_type == review_type
    ), f"Caf profile  persisted as '{assessment.review_type}' not expect '{review_type}'"


@step('there is an assessor registered in the system named "{assessor_name}"')
def add_assessor(context: Context, assessor_name: str):
    """
    :param assessor_name:
    :param context: Context
    """
    from webcaf.webcaf.models import Assessor

    if not exists_model(Assessor, name=assessor_name):
        assessor = create_model(
            Assessor,
            organisation=context.organisation,
            name=assessor_name,
            contact_name=assessor_name,
            email=f"{assessor_name.lower().replace(' ', '.')}@example.com",
            address="Test Address",
            assessor_type="peer_review",
        )
        print(f"Created assessor: {assessor.name}")
    else:
        print(f"Assessor {assessor_name} already exists")


@step('the user "{assessor_user}" belongs to the assessor "{assessor}"')
def add_assessor_user_to_company(context: Context, assessor_user: str, assessor: str):
    """
    :param assessor:
    :param assessor_user:
    :param context: Context
    """
    from django.contrib.auth.models import User

    from webcaf.webcaf.models import Assessor, UserProfile

    def add_user_to_assessor():
        user = User.objects.get(username=assessor_user)
        user_profile = UserProfile.objects.get(user=user)
        assessor_obj = Assessor.objects.get(name=assessor)

        if user_profile not in assessor_obj.members.all():
            assessor_obj.members.add(user_profile)
            assessor_obj.save()
            print(f"Added user {assessor_user} to assessor {assessor}")
        else:
            print(f"User {assessor_user} already belongs to assessor {assessor}")

    run_async_orm(add_user_to_assessor)


@step('the "{assessor}" is assigned to "{organisation}"')
def assign_assessor(context: Context, assessor: str, organisation: str):
    """
    :param assessor:
    :param organisation:
    :param context: Context
    """

    def assign_assessor():
        from webcaf.webcaf.models import Assessor, Organisation

        assessor_ = Assessor.objects.filter(name=assessor).get()
        organisation_ = Organisation.objects.filter(name=organisation).get()
        organisation_.assessors.add(assessor_)
        organisation_.save()

    run_async_orm(assign_assessor)


@step('the current assessment is assigned for review to the "{review_by}"')
def set_review_by(context: Context, review_by: str):
    """
    :param review_by:
    :param context: Context
    """

    def assign_review_by():
        from webcaf.webcaf.models import Assessment, Assessor, Review

        assessment = Assessment.objects.get(id=context.current_assessment_id)
        assessor = Assessor.objects.get(name=review_by)
        review = Review.objects.get_or_create(assessment=assessment, assessed_by=assessor)[0]
        review.save()

    run_async_orm(assign_review_by)
