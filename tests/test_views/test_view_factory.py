from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from webcaf.webcaf.views.view_factory import create_form_view


class ViewFactoryFormValidTests(SimpleTestCase):
    def test_form_valid_saves_assessment_data_with_indicator_keys(self):
        """
        Tests whether the `form_valid` method of a dynamically created view correctly saves
        assessment data with specific indicator keys and associates it with a given class
        identifier.

        This test ensures that:
        - Data formatted with keys indicating assessment indicators is processed and stored correctly.
        - The data is saved under the specified `class_id` within the `assessments_data` attribute.
        - The parent `form_valid` implementation is still invoked properly after data handling.
        - The relevant helper methods and attributes are utilized appropriately during the process.

        :uses:
            - `cleaned_data`: Simulating submitted form data containing indicator keys along with
              their associated values.
            - `class_id`: A unique identifier used to categorize the saved assessment data.
            - `request`: A mock object mimicking an HTTP request instance with session data.
            - `fake_assessment`: A mock object representing an assessment that stores data and
              mimics save operation functionality.
            - `form`: A mock form carrying the `cleaned_data` required for processing.
        """
        # Prepare cleaned_data with the required key format.
        # Only the ticked indicators are included in the form submission.
        cleaned_data = {
            "not-achieved_A1.a.1": True,
            "not-achieved_A1.a.2": True,
            "achieved_A1.a.2": True,
        }

        # Class id to associate the saved data with
        class_id = "my-section"

        # Fake request and assessment
        request = SimpleNamespace(session={})
        fake_assessment = MagicMock()
        fake_assessment.assessments_data = {}
        fake_assessment.save = MagicMock()

        fake_user_profile = SimpleNamespace(
            id=123,
            organisation=SimpleNamespace(id=456, name="dummy-org"),
            role="organisation_user",
            user=MagicMock(username="mock-user"),
        )

        # A dummy form carrying cleaned_data
        form = SimpleNamespace(cleaned_data=cleaned_data)

        # Create the dynamic view class; patch reverse_lazy to avoid URL resolution
        with patch("webcaf.webcaf.views.view_factory.reverse_lazy", return_value="/success/"), patch(
            "webcaf.webcaf.views.view_factory.SessionUtil.get_current_assessment", return_value=fake_assessment
        ) as mock_get_assessment, patch(
            "webcaf.webcaf.views.view_factory.SessionUtil.get_current_user_profile", return_value=fake_user_profile
        ) as mock_get_current_user_profile, patch(
            "webcaf.webcaf.views.view_factory.FormView.form_valid", return_value="OK"
        ) as mock_super_form_valid:
            ViewClass = create_form_view(
                success_url_name="ignored",
                class_id=class_id,
                stage="indicator",
                class_prefix="OutcomeIndicatorsView.A1",
            )
            view = ViewClass()
            view.request = request

            # Exercise
            result = view.form_valid(form)

        # Verify data saved under the correct class_id
        self.assertIn(class_id, fake_assessment.assessments_data)

        self.assertEqual(
            fake_assessment.assessments_data[class_id],
            {
                "indicator": cleaned_data,
            },
        )

        # Ensure save called and control passed to parent implementation
        fake_assessment.save.assert_called_once()
        mock_get_assessment.assert_called_once_with(request)
        mock_super_form_valid.assert_called_once()

        mock_get_current_user_profile.assert_called_once_with(request)

        self.assertEqual(result, "OK")
