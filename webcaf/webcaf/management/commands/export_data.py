import json
import logging
from datetime import datetime
from functools import partial
from typing import Any, Tuple, cast

import boto3
from django.core.management.base import BaseCommand
from django.db.models import Min

from webcaf import settings
from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Assessment, Organisation, Review
from webcaf.webcaf.templatetags.form_extras import (
    generate_assessment_progress_indicators,
)
from webcaf.webcaf.utils.data_analysis import (
    transform_assessment,
    transform_organisation,
    transform_review,
    transform_system,
)


def extract_metadata(
    assessment: Assessment,
    submitted_dates: dict[int, datetime],
    in_progress_dates: dict[int, datetime],
) -> dict[str | Any, str | datetime | Any]:
    """
    Build the metadata dict for a single assessment.

    Status-change timestamps are looked up from pre-fetched dicts rather than
    querying the database per assessment, keeping this function free of DB calls.

    Args:
        assessment: The Assessment instance to extract metadata from.
        submitted_dates: Mapping of assessment ID to the earliest datetime the
            assessment history recorded a ``"submitted"`` status.
        in_progress_dates: Mapping of assessment ID to the earliest datetime a
            related Review history record was in ``"in_progress"`` status.

    Returns:
        A flat dict of metadata fields ready to be embedded in the export payload.
    """
    submitted_date = submitted_dates.get(assessment.id)
    in_progress_date = in_progress_dates.get(assessment.id)
    # Fail fast if we do not have the caf version we are looking for
    # we do not want to export if the version is not there
    caf_version = {"caf32": "3.2", "caf40": "4.0"}[assessment.framework]
    return {
        "system_profile": assessment.get_caf_profile_display(),
        "review_type": assessment.review_type,
        "organisation_type_description": assessment.system.organisation.get_organisation_type_display(),
        "assessment_status_description": assessment.get_status_display(),
        "assessment_version": assessment.get_framework_display(),
        # First datetime a related review entered "in_progress" (assessing started)
        "assessment_status_changed_to_aseing": str(in_progress_date) if in_progress_date else "",
        # First datetime the assessment status changed to "submitted"
        "assessment_status_changed_to_submtd": str(submitted_date) if submitted_date else "",
        "assessment_last_updated": str(assessment.last_updated),
        "assessment_progress_organisation": generate_assessment_progress_indicators(assessment)["percentage"],
        "organisation_id": assessment.system.organisation.id,
        "system_id": assessment.system.id,
        "assessment_id": assessment.id,
        "assessment_created_on": str(assessment.created_on),
        "assessment_period": assessment.assessment_period,
        "app_version": "webcaf-2",
        "caf_version": caf_version,
        "caf_description": assessment.get_framework_display(),
    }


class Command(BaseCommand):
    """
    Django management command that exports all assessments, organisations, systems and reviews to S3.

    Each assessment is serialised to JSON in the standardised outcome format and
    uploaded to ``assessments/<period>/<reference>.json``.
    Each review is
    uploaded to ``reviews/<period>/<reference>.json``.

    Organisations and Systems are uploaded to:
    ``systems/<reference>.json``.
    ``organisations/<reference>.json``.

    Usage::

        python manage.py export_data

    The target S3 bucket is read from ``settings.AWS_STORAGE_BUCKET_NAME``.
    If the setting is absent, the command exits with a warning and no upload is
    performed.
    """

    help = "Export to the S3"

    def handle(self, *args, **options):
        """
        Entry point for the management command.

        Builds two lookup dicts from the assessment and review history tables
        using a single aggregated query each, then delegates the actual upload
        work to :meth:`export_assessments` and :meth:`export_reviews`.
        """
        print("Exporting data to S3...")
        s3 = boto3.client("s3")

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        if bucket_name:
            # Single query: earliest datetime each assessment reached "submitted"
            submitted_dates = {
                entry["id"]: entry["first_submitted"]
                for entry in Assessment.history.filter(status="submitted")
                .values("id")
                .annotate(first_submitted=Min("history_date"))
            }
            # Single query: earliest datetime a review for each assessment reached "in_progress"
            in_progress_dates = {
                entry["assessment_id"]: entry["first_in_progress"]
                for entry in Review.history.filter(status="in_progress")
                .values("assessment_id")
                .annotate(first_in_progress=Min("history_date"))
            }
            self.export_organisation_and_systems(bucket_name, s3)
            self.export_assessments(bucket_name, s3, submitted_dates, in_progress_dates)
            self.export_reviews(bucket_name, s3, submitted_dates, in_progress_dates)
            self.stdout.write(self.style.SUCCESS("Successfully uploaded to S3"))
        else:
            self.stdout.write(self.style.WARNING("S3 bucket name is not configured. Skipping export to S3."))

    def profile_met_callback(
        self, current_assessment: Assessment, outcome_code: str, status: str | None
    ) -> Tuple[str, str]:
        """
        Evaluates whether the indicator's minimum profile requirements are met based on the
        current assessment context and outcome.

        :param current_assessment: An instance of the ``Assessment`` class that contains the
            current state of the evaluation process.
        :param outcome_code: A string representing the outcome code, which is used to deduce
            the indicator's minimum profile requirements.
        :param status: A string representing the status to evaluate, or ``None`` if no status
            is provided.
        :return: A tuple containing the result of the indicator's minimum profile evaluation,
            structured as two strings.
        """
        # Casting to indicate we always return a tuple
        return cast(
            Tuple[str, str],
            IndicatorStatusChecker.indicator_min_profile_requirement_met(
                current_assessment, outcome_code.split(".")[0], outcome_code, status if status else "", True
            ),
        )

    def export_assessments(self, bucket_name: str, s3, submitted_dates: dict, in_progress_dates: dict):
        """
        Transform and upload every assessment to S3.

        Files are stored at ``assessments/<period>/<reference>.json``.

        Args:
            bucket_name: Name of the destination S3 bucket.
            s3: Boto3 S3 client.
            submitted_dates: Pre-fetched mapping of assessment ID → first submitted datetime.
            in_progress_dates: Pre-fetched mapping of assessment ID → first in-progress datetime.
        """
        assessments = Assessment.objects.select_related("system", "system__organisation").all()
        try:
            for assessment in assessments:
                metadata = extract_metadata(assessment, submitted_dates, in_progress_dates)
                transformed_data = transform_assessment(
                    assessment.assessments_data,
                    metadata,
                    # Provide assessment as the 1st argument by default
                    partial(self.profile_met_callback, assessment),
                )
                file_path = f"assessments/{assessment.assessment_period.replace('/', '-')}/{assessment.reference}.json"
                s3.put_object(
                    Bucket=bucket_name,
                    Key=file_path,
                    Body=json.dumps(transformed_data),
                )
                self.stdout.write(f"File uploaded to s3://{bucket_name}/{file_path}")
        except Exception as ex:
            logging.getLogger("AssessmentUpload").exception("Failed to upload assessments to S3")
            self.stderr.write(self.style.ERROR(f"Failed to upload assessments to S3: {ex}"))

    def export_reviews(self, bucket_name: str, s3, submitted_dates: dict, in_progress_dates: dict):
        """
        Transform and upload every review to S3.

        Only the top-level CAF sections (A–D) from ``assessor_response_data``
        are included in the export payload.  Files are stored at
        ``reviews/<period>/<reference>.json``.

        Args:
            bucket_name: Name of the destination S3 bucket.
            s3: Boto3 S3 client.
            submitted_dates: Pre-fetched mapping of assessment ID → first submitted datetime.
            in_progress_dates: Pre-fetched mapping of assessment ID → first in-progress datetime.
        """
        reviews = Review.objects.select_related(
            "assessment", "assessment__system", "assessment__system__organisation"
        ).all()
        try:
            for review in reviews:
                assessment = review.assessment
                self.stdout.write(f"Extracting review data... {review.reference}")
                metadata = extract_metadata(assessment, submitted_dates, in_progress_dates)
                metadata.update(
                    {
                        "additional_information": review.review_data.get("assessor_response_data", {}).get(
                            "additional_information", {}
                        ),
                        "review_completion": review.review_data.get("review_completion", {}),
                        "review_finalised": review.review_data.get("review_finalised", {}),
                        "review_created": str(review.created_on),
                        "review_last_updated": str(review.last_updated),
                    }
                )
                transformed_data = transform_review(
                    (
                        {
                            k: v
                            for k, v in review.review_data.get("assessor_response_data", {}).items()
                            if k in {"A", "B", "C", "D"}
                        }
                    ),
                    metadata,
                    partial(self.profile_met_callback, assessment),
                )
                file_path = f"reviews/{assessment.assessment_period.replace('/', '-')}/{assessment.reference}.json"
                s3.put_object(
                    Bucket=bucket_name,
                    Key=file_path,
                    Body=json.dumps(transformed_data),
                )
                self.stdout.write(f"File uploaded to s3://{bucket_name}/{file_path}")
        except Exception as ex:
            logging.getLogger("ReviewUpload").exception("Failed to upload reviews to S3")
            self.stderr.write(self.style.ERROR(f"Failed to review upload to S3: {ex}"))

    def export_organisation_and_systems(self, bucket_name, s3):
        """
        Exports organisation and system data to an S3 bucket in JSON format. For each
        organisation and its associated systems, this method generates JSON representations
        of their data, uploads the files to the specified S3 bucket, and logs the upload
        paths for reference.

        :param bucket_name: The name of the S3 bucket where the files will be uploaded.
        :type bucket_name: str
        :param s3: An instance of boto3 S3 client used to perform the file upload operations.
        :type s3: botocore.client.S3
        :return: None
        """
        for organisation in Organisation.objects.all():
            self.stdout.write(f"File uploaded to s3://{bucket_name}/organisations/{organisation.reference}.json")
            parent = organisation.parent_organisation
            s3.put_object(
                Bucket=bucket_name,
                Key=f"organisations/{organisation.reference}.json",
                Body=json.dumps(
                    transform_organisation(
                        {
                            "organisation_name": organisation.name,
                            "organisation_type": organisation.get_organisation_type_display(),
                            "organisation_id": organisation.id,
                            "parent_organisation_id": parent.id if parent else None,
                            "parent_organisation_name": parent.name if parent else None,
                            "app_version": "webcaf-2",
                            "legacy_organisation_id": None,
                        }
                    )
                ),
            )

            for system in organisation.systems.all():
                self.stdout.write(f"File uploaded to s3://{bucket_name}/systems/{system.reference}.json")
                s3.put_object(
                    Bucket=bucket_name,
                    Key=f"systems/{system.reference}.json",
                    Body=json.dumps(
                        transform_system(
                            {
                                "system_name": system.name,
                                "system_type": system.system_type,
                                "hosting_type": system.hosting_type,
                                "corporate_services": system.corporate_services,
                                "system_owner": system.system_owner,
                                "organisation_id": system.organisation.id,
                                "system_id": system.id,
                                "last_assessed": _transform_last_assessed(system.last_assessed),
                                "app_version": "webcaf-2",
                                "legacy_system_id": None,
                            }
                        )
                    ),
                )


# Mapping from ``System.last_assessed`` database values to the short
# period labels used in the analytics export.
_LAST_ASSESSED_TO_PERIODS: dict[str, list[str]] = {
    "assessed_in_2324": ["23/24"],
    "assessed_in_2425": ["24/25"],
    "assessed_in_2324_and_2425": ["23/24", "24/25"],
}


def _transform_last_assessed(last_assessed: str | None) -> list[str]:
    """Map a ``last_assessed`` database value to short period labels.

    Args:
        last_assessed: Raw value from the ``System.last_assessed`` field.

    Returns:
        A list of period strings (e.g. ``["23/24"]``), or an empty list
        if the value is falsy or unrecognised.
    """
    if not last_assessed:
        return []
    return list(_LAST_ASSESSED_TO_PERIODS.get(last_assessed, []))
