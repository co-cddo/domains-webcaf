import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from webcaf.webcaf.models import Assessment, UserProfile


class SessionUtil:
    logger: logging.Logger = logging.getLogger("SessionUtil")

    @staticmethod
    def get_current_user_profile(request) -> Optional["UserProfile"]:
        """
        Retrieve the current user's profile based on the session information.

        This method accesses the session to extract the current user's
        profile ID and attempts to fetch the user profile from the database.
        If the profile cannot be retrieved, an error is logged, and the method
        returns None.

        :param request: The HTTP request object containing the session with the
            "current_profile_id" key.
        :type request: HttpRequest
        :return: The UserProfile object corresponding to the current user, or None
            if the profile could not be retrieved.
        :rtype: Optional[UserProfile]
        """
        from webcaf.webcaf.models import UserProfile

        user_profile_id = request.session["current_profile_id"]
        try:
            return UserProfile.objects.get(id=user_profile_id)
        except Exception:  # type: ignore[catching-any]
            SessionUtil.logger.error(f"Unable to retrieve user profile with id {user_profile_id}")
        return None

    @staticmethod
    def get_current_assessment(request, status_to_get: str | None = "draft") -> Optional["Assessment"]:
        """
        Retrieve the current assessment for the user based on session data and the given status.

        This function fetches the assessment linked to the user's profile
        and organisation, using the `assessment_id` and `current_profile_id`
        stored in the session. It ensures the assessment belongs to the user's
        organisation and is in the 'status_to_get' state.

        :param request: HTTP request object containing session data used to
            identify the assessment and user profile.
        :return: Assessment object matching the specified session data.
        :rtype: Assessment
        """
        from webcaf.webcaf.models import Assessment

        id_: int | None = None
        # We will have the assessment in the session only if the user is logged in and
        # working on an assessment.
        if "assessment_id" in request.session.get("draft_assessment", {}):
            try:
                id_ = int(request.session["draft_assessment"]["assessment_id"])
                user_profile = SessionUtil.get_current_user_profile(request)
                if user_profile and user_profile.organisation:
                    assessment = Assessment.objects.get(
                        status=status_to_get, id=id_, system__organisation_id=user_profile.organisation.id
                    )
                    return assessment
            except Exception:  # type: ignore[catching-any]
                SessionUtil.logger.error(
                    f"Unable to retrieve assessment with id {id_} for user {request.user.username}"
                )
        return None
