from typing import Any


def calculate_outcome_status(confirmation: dict[str, Any], indicators: dict[str, Any]) -> dict[str, str | None]:
    """
    Determines the outcome status based on confirmation and indicators provided.

    :param confirmation: A dictionary containing confirmation details.
    :type confirmation: dict[str, Any]
    :param indicators: A dictionary containing various status indicators.
    :type indicators: dict[str, Any]

    :return: A dictionary with keys "outcome_status" and "override_status".
    :rtype: dict[str, str | None]
    """
    override_status: str | None = None
    if confirmation:
        if confirm_outcome := confirmation.get("confirm_outcome"):
            # Final part of the change_to indicator is the override status
            # The possible values are: achieved, partially_achieved, not_achieved, confirm
            # NOTE: Value of confirm indicates that the user has not overridden our calculated value
            override_status = confirm_outcome.replace("change_to_", "").replace("_", " ").capitalize()
            # If the value in the override is 'confirm', then the user has not overridden our calculated value
            if override_status == "Confirm":
                override_status = None

    # Filter out comment keys and get achieved responses
    achieved_responses = set(
        map(
            lambda x: x[1],
            filter(lambda x: not x[0].endswith("_comment") and x[0].startswith("achieved_"), indicators.items()),
        )
    )
    if len(achieved_responses) == 1 and "agreed" in achieved_responses:
        calculated_status = "Achieved"
    else:
        calculated_status = "Not achieved"

    return {
        "outcome_status": calculated_status,
        "override_status": override_status,
    }


def outcome_status_to_text(outcome_status: str) -> str:
    """
    Get the text representation of the given outcome status.
    :param outcome_status:
    :return:
    """
    return {
        "Achieved": """You selected 'true' to all the achieved statements.
Please confirm you agree with this status, or you can choose to change the outcome.""",
        "Not achieved": """You selected 'not true' to at least one of the achieved or partially achieved statements.
Please confirm you agree with this status, or you can choose to change the outcome.""",
        "Partially achieved": """You selected 'partially achieved'""",
    }[outcome_status]
