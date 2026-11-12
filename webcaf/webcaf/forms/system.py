from django.forms import ChoiceField, ModelForm

from webcaf.webcaf.models import System


class SystemForm(ModelForm):

    action = ChoiceField(
        choices=[("change", "Change"), ("confirm", "Confirm")],
        required=True,
    )

    class Meta:
        model = System
        fields = [
            "name",
            "system_type",
            "last_assessed",
            "system_owner",
            "hosting_type",
            "corporate_services",
            "corporate_services_other",
        ]

        labels = {
            "name": "System name",
            "system_type": "System description",
            "last_assessed": "Previous GovAssure self-assessments",
            "system_owner": "System ownership",
            "hosting_type": "Hosting and connectivity",
            "corporate_services": "Corporate services",
            "corporate_services_other": "Other corporate services",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, field in self.fields.items():
            if key not in ["corporate_services_other"]:
                field.required = True

    def clean(self):
        cleaned_data = super().clean()
        corporate_services = cleaned_data.get("corporate_services")
        corporate_services_other = cleaned_data.get("corporate_services_other")
        if corporate_services and corporate_services[0] == "other":
            if not corporate_services_other:
                self.add_error("corporate_services_other", "Please enter a description of the corporate services.")
        else:
            # No need to keep the other corporate services description.
            cleaned_data["corporate_services_other"] = ""
        return cleaned_data
