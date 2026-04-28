"""
Transformations for assessment, review, organisation, and system data into
standardised outcome formats suitable for analytics export.

Each public function accepts raw model data and returns a flat dictionary
ready for JSON serialisation and upload to S3.
"""

from typing import Any, Callable, Tuple

# Type alias for the callback used to evaluate whether an outcome meets
# its minimum CAF profile requirement.  The callback receives an outcome
# code (e.g. "A1.a") and an optional status string, and returns a
# (profile_met, min_requirement) tuple or ``None``.
ProfileMetCallback = Callable[[str, str | None], Tuple[str, str] | None]

# Human-readable labels for raw review-decision keys stored in the database.
_REVIEW_DECISION_LABELS: dict[str, str] = {
    "achieved": "Achieved",
    "not-achieved": "Not achieved",
    "partially-achieved": "Partially achieved",
    "N/A": "N/A",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_indicators(
    indicators_data: dict[str, Any],
    *,
    coerce_to_bool: bool = False,
) -> list[dict[str, Any]]:
    """Parse raw indicator key/value pairs into a normalised list.

    Indicator keys follow the pattern ``<category>_<indicator_id>`` (e.g.
    ``achieved_A1.a.1``).  Companion ``*_comment`` keys are folded into
    the same entry.

    Args:
        indicators_data: Raw indicator dict from assessment or review data.
        coerce_to_bool: When ``True`` string values ``"yes"``/``"no"`` are
            converted to ``bool`` (used for review indicators).

    Returns:
        A list of dicts, each with keys ``indicator_id``, ``indicator_category``
        (or ``category``), ``value``, and ``comment``.
    """
    indicators: list[dict[str, Any]] = []

    for key, value in indicators_data.items():
        if key.endswith("_comment"):
            continue

        parts = key.split("_", 1)
        if len(parts) != 2:
            continue

        category, indicator_id = parts
        comment = indicators_data.get(f"{key}_comment", "")

        if coerce_to_bool:
            indicators.append(
                {
                    "indicator_id": indicator_id,
                    "category": category,
                    "value": value.lower() == "yes",
                    "comment": comment,
                }
            )
        else:
            indicators.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_category": category,
                    "value": value,
                    "comment": comment,
                }
            )

    return indicators


def _evaluate_profile(
    callback: ProfileMetCallback,
    outcome_code: str,
    status: str | None,
) -> tuple[str, str]:
    """Invoke *callback* unless the status is ``"N/A"``, returning defaults.

    Returns:
        A ``(profile_met, min_requirement)`` tuple.  Both values default to
        ``""`` when the status is ``"N/A"`` or the callback returns ``None``.
    """
    if status == "N/A":
        return "", ""
    result = callback(outcome_code, status)
    if result:
        return "Met" if result[0] == "Yes" else result[0], result[1]
    return "", ""


# ---------------------------------------------------------------------------
# Public transform functions
# ---------------------------------------------------------------------------


def transform_assessment(
    assessment: dict[str, Any],
    metadata: dict[str, Any],
    profile_met_callback: ProfileMetCallback,
) -> dict[str, Any]:
    """Transform raw assessment data into the standardised outcome format.

    Each top-level key in *assessment* (e.g. ``"A1.a"``) becomes an outcome
    entry containing its confirmation status, profile-met evaluation, and a
    parsed list of indicators.

    Args:
        assessment: The ``assessments_data`` JSON field from the
            :class:`~webcaf.webcaf.models.Assessment` model.
        metadata: A flat dict of contextual fields produced by
            :func:`~webcaf.webcaf.management.commands.export_data.extract_metadata`.
        profile_met_callback: Evaluates whether an outcome meets its minimum
            CAF profile requirement.

    Returns:
        A dict with top-level keys ``self_assessment``, ``assessment_details``,
        ``organisation_id``, and ``system_id``.
    """
    outcomes: list[dict[str, Any]] = []

    for outcome_code, data in assessment.items():
        confirmation = data.get("confirmation", {})
        outcome_status = confirmation.get("outcome_status", "")

        profile_met, min_requirement = _evaluate_profile(
            profile_met_callback,
            outcome_code,
            outcome_status,
        )

        outcomes.append(
            {
                "outcome_id": outcome_code,
                "outcome_status": outcome_status,
                "outcome_profile_met": profile_met,
                "outcome_min_profile_requirement": min_requirement,
                "outcome_status_message": confirmation.get("outcome_status_message", ""),
                "outcome_confirm_comment": confirmation.get("confirm_outcome_confirm_comment", ""),
                "indicators": _parse_indicators(data.get("indicators", {})),
                "supplementary_questions": data.get("supplementary_questions", []),
            }
        )

    return {
        "app_version": metadata["app_version"],
        "organisation_id": metadata["organisation_id"],
        "system_id": metadata["system_id"],
        "assessment_id": metadata["assessment_id"],
        "outcomes": outcomes,
        "metadata": {
            "last_updated": metadata.get("assessment_last_updated"),
            "created": metadata.get("assessment_created_on"),
            "completed": metadata.get("assessment_status_changed_to_submtd"),
        },
        "assessment_details": {
            "caf_version": metadata["caf_version"],
            "caf_description": metadata["caf_description"],
            "government_caf_profile": (
                metadata.get("system_profile", "").capitalize() if metadata.get("system_profile") else None
            ),
            "review_type": metadata.get("review_type"),
            "assessment_period": metadata.get("assessment_period"),
        },
    }


def transform_review(
    review: dict[str, Any],
    metadata: dict[str, Any],
    profile_met_callback: ProfileMetCallback,
) -> dict[str, Any]:
    """Transform raw review data into the standardised outcome format.

    Iterates over the top-level objective groups (A-D) in *review*.  For
    each outcome within a group the review decision is label-mapped, the
    self-assessment status is looked up from *assessment*, and indicators
    are parsed with ``"yes"``/``"no"`` values coerced to booleans.

    Args:
        review: A subset of ``assessor_response_data`` containing only the
            A-D sections.
        metadata: Contextual fields from
            :func:`~webcaf.webcaf.management.commands.export_data.extract_metadata`,
            augmented with review-specific entries (``additional_information``,
            ``review_completion``, ``review_finalised``).
        profile_met_callback: Evaluates whether an outcome meets its minimum
            CAF profile requirement.

    Returns:
        A dict with top-level keys ``review_details``, ``outcomes``,
        ``metadata``, and ``review_commentary``.
    """
    outcomes: list[dict[str, Any]] = []
    review_commentary: list[dict[str, Any]] = []

    for group, group_data in review.items():
        review_commentary.append(
            {
                "objective_code": group,
                "areas_for_improvement": group_data.get("objective-areas-of-improvement"),
                "areas_of_good_practice": group_data.get("objective-areas-of-good-practice"),
            }
        )

        # Only iterate over outcome keys that belong to this group (e.g. "A1.a" starts with "A").
        outcome_entries = {k: v for k, v in group_data.items() if k.startswith(group)}

        for outcome_code, outcome_data in outcome_entries.items():
            review_data = outcome_data.get("review_data", {})
            review_decision = _REVIEW_DECISION_LABELS.get(
                review_data.get("review_decision", "N/A"),
            )
            review_comment = review_data.get("review_comment", "")
            indicators_list = _parse_indicators(
                outcome_data.get("indicators", {}),
                coerce_to_bool=True,
            )

            review_profile_met, min_requirement = _evaluate_profile(
                profile_met_callback,
                outcome_code,
                review_decision,
            )

            recommendations = _build_recommendations(
                outcome_data.get("recommendations", []),
                outcome_code,
                review_profile_met,
            )

            outcomes.append(
                {
                    "outcome_id": outcome_code,
                    "review_decision": review_decision,
                    "outcome_min_profile_requirement": min_requirement,
                    "review_profile_met": review_profile_met,
                    "review_comment": review_comment,
                    "indicators": indicators_list,
                    "recommendations": recommendations,
                }
            )

    additional_information = metadata.get("additional_information", {})

    return {
        "app_version": metadata["app_version"],
        "assessment_id": metadata["assessment_id"],
        "review_details": {
            "review_period": additional_information.get("iar_period", {}),
            "company_name": additional_information.get("company_details", {}).get("company_name"),
            "review_method": additional_information.get("review_method"),
            "quality_self_assessment": additional_information.get("quality_of_evidence"),
        },
        "outcomes": outcomes,
        "metadata": {
            "review_last_updated": metadata.get("review_last_updated"),
            "review_created": metadata.get("review_created"),
            "review_completed": metadata.get("review_completion", {}).get("review_completed_at"),
            "review_finalised": metadata.get("review_finalised", {}).get("review_finalised_at"),
        },
        "review_commentary": {
            "objective_level": review_commentary,
            "overall": {
                "areas_for_improvement": additional_information.get("areas_for_improvement"),
                "areas_of_good_practice": additional_information.get("areas_of_good_practice"),
            },
        },
    }


def _build_recommendations(
    raw_recommendations: list[dict[str, Any]],
    outcome_code: str,
    review_profile_met: str,
) -> list[dict[str, Any]]:
    """Build the recommendations list for a single review outcome.

    Each recommendation is assigned a deterministic ID of the form
    ``REC-<OUTCOME>N`` (e.g. ``REC-A1A1``, ``REC-A1A2``).

    Args:
        raw_recommendations: List of recommendation dicts from the review data,
            each expected to have ``text`` and ``title`` keys.
        outcome_code: The outcome this recommendation belongs to (e.g. ``"A1.a"``).
        review_profile_met: The profile-met string for the review decision;
            used to derive the ``priority_recommendation`` flag.

    Returns:
        A list of normalised recommendation dicts.
    """
    rec_id_prefix = f"REC-{outcome_code}".replace(".", "").upper()
    recommendations: list[dict[str, Any]] = []

    for idx, recommendation in enumerate(raw_recommendations):
        recommendations.append(
            {
                "recommendation_id": f"{rec_id_prefix}{idx + 1}",
                "recommendation_text": recommendation.get("text"),
                "risk_text": recommendation.get("title"),
                "priority_recommendation": (review_profile_met.lower() != "yes" if review_profile_met else ""),
            }
        )

    return recommendations


def transform_organisation(org_data: dict[str, Any]) -> dict[str, Any]:
    """
    Transforms the input dictionary containing organisation data into a standardized format.

    This function extracts specific keys from the given dictionary and includes them in
    a new dictionary. It also attempts to retrieve optional keys from the input data,
    ensuring their presence in the resulting dictionary only if they exist in the
    input. This utility is useful for standardizing the output format for organisation
    data across various systems.

    :param org_data: A dictionary representing the organisation's details. The input
        must include keys such as "organisation_name", "organisation_id", and
        "app_version". Optional keys such as "organisation_type",
        "parent_organisation_id", "parent_organisation_name", and
        "legacy_organisation_id" are also processed.
    :type org_data: dict[str, Any]
    :return: Transformed dictionary containing standardised organisation data. Keys
        included in the output are "organisation_name", "organisation_id",
        "app_version", "organisation_type", "parent_organisation_id",
        "parent_organisation_name", and "legacy_organisation_id".
    :rtype: dict[str, Any]
    """
    return {
        "organisation_name": org_data["organisation_name"],
        "organisation_id": org_data["organisation_id"],
        "app_version": org_data["app_version"],
        "organisation_type": org_data.get("organisation_type"),
        "parent_organisation_id": org_data.get("parent_organisation_id"),
        "parent_organisation_name": org_data.get("parent_organisation_name"),
        "legacy_organisation_id": org_data.get("legacy_organisation_id"),
    }


def transform_system(system_data: dict[str, Any]) -> dict[str, Any]:
    """
    Transforms a system data dictionary into a specific structure with key mappings and optional attributes.

    The `transform_system` function takes an input dictionary representing
    system data and restructures it into a standardized format. The input
    dictionary is expected to contain certain mandatory keys, while some
    optional keys may also be included. The function maps these keys to
    their corresponding output keys and ensures consistency in data
    representation.

    :param system_data: The input dictionary containing information about the system. The dictionary should
                        include mandatory keys such as "system_name", "system_id", and "app_version".
                        Optional keys like "system_type", "hosting_type", "corporate_services",
                        "system_owner", "organisation_id", "last_assessed", and "legacy_system_id" may
                        also be present.
    :type system_data: dict[str, Any]

    :return: A transformed dictionary containing the system data fields with their respective mappings.
    :rtype: dict[str, Any]
    """
    return {
        "system_name": system_data["system_name"],
        "system_id": system_data["system_id"],
        "app_version": system_data["app_version"],
        "system_type": system_data.get("system_type"),
        "hosting_type": system_data.get("hosting_type"),
        "corporate_services": system_data.get("corporate_services"),
        "system_owner": system_data.get("system_owner"),
        "organisation_id": system_data.get("organisation_id"),
        "last_assessed": system_data.get("last_assessed"),
        "legacy_system_id": system_data.get("legacy_system_id"),
    }
