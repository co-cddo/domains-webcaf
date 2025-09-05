import os


def variable_page_content(_request):
    """
    Provide environment-dependent values for rendering pages
    (e.g. header text for the phase banner)
    :param _request: not used
    :return:
    """
    phase = os.getenv("ENVIRONMENT")
    if phase not in ["prod", "stage"]:
        context = {
            "PHASE_CLASS": "govuk-tag--pink",
            "PHASE_HEADER": "Prototype",
            "PHASE_CONTENT": "This is not a full service. It is not production code and you might experience problems.",
        }
    else:
        context = {
            "PHASE_CLASS": "",
            "PHASE_HEADER": "Beta",
            "PHASE_CONTENT": "<div class='govuk-phase-banner__text'>This is a new service. Help us improve it, <a class='govuk-link' href='https://surveys.domains.gov.uk/s/VCVZSB/' target='_blank'>report a problem or give your feedback (opens in new tab)</a>.</div>",
        }

    # Google Tag Manager ID for inclusion in the HTML markup
    google_analytics_id = os.getenv("GOOGLE_ANALYTICS_ID", "")
    context["GOOGLE_ANALYTICS_ID"] = google_analytics_id if google_analytics_id[:4].upper() == "GTM-" else ""

    return context
