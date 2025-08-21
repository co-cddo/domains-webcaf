from behave import step

from features.util import run_async_orm


@step("Organisation {organisation_name} has started an assessment for the system {system_name}")
def step_crate_assessment(context, organisation_name, system_name):
    """
    :type context: behave.runner.Context
    """
    from webcaf.webcaf.models import Assessment, System

    def create_system():
        return Assessment.objects.create(
            status="draft",
            assessment_period="25/26",
            system=System.objects.get(name=system_name, organisation__name=organisation_name),
            version="v3.2",
            caf_profile="baseline",
        )

    assessment = run_async_orm(create_system)
    print("Assessment {} for system {} started.".format(assessment, system_name))
