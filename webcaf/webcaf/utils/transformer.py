"""
This module provides transformations of assessment and review data structures into a standardized outcome format.
The outcome format organizes data into outcomes with associated indicators and metadata.

Functions:
    - assessment_transform_to_outcome_format: Transforms an assessment structure into a standardized outcome format.
    - review_transform_to_outcome_format: Transforms a review structure into a standardized outcome format.
"""
from typing import Any


def assessment_transform_to_outcome_format(assessment: dict[str, Any]) -> dict[str, Any]:
    """
    Transforms an assessment structure into a standardized outcome format.
    Returns a dictionary with 'outcomes' key containing a list of outcomes with their indicators.
    Each outcome has: outcome code, outcome_status, and list of indicators.
    Each indicator has: indicator_id, category, value, and comment.
    """
    outcomes = []
    metadata = {}
    for key, data in assessment.items():
        if key == "meta_data":
            metadata = data
            continue

        # Extract outcome code (e.g., "A1.a")
        outcome_code = key

        # Get outcome status from confirmation
        confirmation = data.get("confirmation", {})
        outcome_status = confirmation.get("outcome_status", "Not achieved")
        outcome_status_message = confirmation.get("outcome_status_message", "")
        confirm_outcome_confirm_comment = confirmation.get("confirm_outcome_confirm_comment", "")
        supplementary_questions = data.get("supplementary_questions", [])

        # Process indicators
        indicators_data = data.get("indicators", {})
        indicators_list = []

        for indicator_key, indicator_value in indicators_data.items():
            # Skip comment fields
            if indicator_key.endswith("_comment"):
                continue

            # Parse indicator key to extract category and indicator_id
            # Format: "achieved_A1.a.1" or "partially-achieved_A1.a.1" or "not-achieved_A1.a.1"
            parts = indicator_key.split("_", 1)
            if len(parts) == 2:
                category = parts[0]
                indicator_id = parts[1]

                # Get corresponding comment
                comment_key = f"{indicator_key}_comment"
                comment = indicators_data.get(comment_key, "")

                indicators_list.append(
                    {"indicator_id": indicator_id, "category": category, "value": indicator_value, "comment": comment}
                )

        outcomes.append(
            {
                "outcome": outcome_code,
                "outcome_status": outcome_status,
                "outcome_status_message": outcome_status_message,
                "outcome_confirm_comment": confirm_outcome_confirm_comment,
                "indicators": indicators_list,
                "supplementary_questions": supplementary_questions,
            }
        )

    return {"outcomes": outcomes, "metadata": metadata}


def review_transform_to_outcome_format(review: dict[str, Any]) -> dict[str, Any]:
    """
    Transforms a review structure into a standardized outcome format.
    Returns a dictionary with 'outcomes' key containing a list of outcomes with their indicators.
    Each outcome has: outcome code, outcome_status, and list of indicators.
    Each indicator has: indicator_id, category, value, and comment.
    """
    outcomes = []
    metadata = {}
    for _, data in review.items():
        if _ == "meta_data":
            metadata = data
            continue
        for key, outcome in data.items():
            # Extract outcome code (e.g., "A1.a")
            outcome_code = key

            # Get outcome status from confirmation
            review_data = outcome.get("review_data", {})
            review_decision = review_data.get("review_decision", "N/A")
            review_comment = review_data.get("review_comment", "")
            outcome_status = review_data.get("outcome_status", "N/A")

            # Process indicators
            indicators_data = outcome.get("indicators", {})
            indicators_list = []

            for indicator_key, indicator_value in indicators_data.items():
                # Skip comment fields
                if indicator_key.endswith("_comment"):
                    continue

                # Parse indicator key to extract category and indicator_id
                # Format: "achieved_A1.a.1" or "partially-achieved_A1.a.1" or "not-achieved_A1.a.1"
                parts = indicator_key.split("_", 1)
                if len(parts) == 2:
                    category = parts[0]
                    indicator_id = parts[1]

                    # Get corresponding comment
                    comment_key = f"{indicator_key}_comment"
                    comment = indicators_data.get(comment_key, "")

                    indicators_list.append(
                        {
                            "indicator_id": indicator_id,
                            "category": category,
                            "value": indicator_value == "Yes",
                            "comment": comment,
                        }
                    )

            outcomes.append(
                {
                    "outcome": outcome_code,
                    "outcome_status": outcome_status,
                    "review_decision": review_decision,
                    "review_comment": review_comment,
                    "indicators": indicators_list,
                }
            )

    return {"outcomes": outcomes, "metadata": metadata}
