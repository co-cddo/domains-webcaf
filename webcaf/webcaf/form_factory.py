from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import (
    HTML,
    Button,
    Field,
    Fieldset,
    Layout,
    TabPanel,
    Tabs,
)
from django import forms

from webcaf.webcaf.caf32_field_providers import FieldProvider


def create_form(provider: FieldProvider) -> type[forms.Form]:  # noqa: C901
    """
    Creates a Django form class based on the fields specified by the
    FieldProvider. This decouples the form creation from the
    specifics of the assessment framework (or other document) being
    represented.
    """
    metadata = provider.get_metadata()
    field_defs = provider.get_field_definitions()
    layout_structure = provider.get_layout_structure()

    form_fields = {}
    for field_def in field_defs:
        if field_def["type"] == "boolean":
            form_fields[field_def["name"]] = forms.BooleanField(
                label=field_def["label"], required=field_def.get("required", False), widget=forms.CheckboxInput()
            )
        elif field_def["type"] == "choice":
            widget = None
            if field_def.get("widget") == "radio":
                widget = forms.RadioSelect
            form_fields[field_def["name"]] = forms.ChoiceField(  # type: ignore
                label=field_def["label"],
                choices=field_def["choices"],
                required=field_def.get("required", True),
                initial=field_def.get("initial"),
                widget=widget,
            )
        elif field_def["type"] == "text":
            widget_attrs = field_def.get("widget_attrs", {})
            form_fields[field_def["name"]] = forms.CharField(  # type: ignore
                label=field_def["label"],
                required=field_def.get("required", True),
                widget=forms.Textarea(attrs=widget_attrs) if widget_attrs else None,
            )

    form_class_name = f"Form_{metadata.get('id', 'dynamic')}"
    FormClass = type(form_class_name, (forms.Form,), form_fields)

    def form_init(self, *args, **kwargs) -> None:
        """
        The __init__ method of the form class created in create_form is set to
        this function. It instanitates a FormHelper and uses the arguments
        passed to create_form to generate the form's layout (hence it's
        declared within it).
        """
        super(FormClass, self).__init__(*args, **kwargs)  # type: ignore
        self.helper = FormHelper()
        self.helper.form_tag = True
        layout_components = []
        header = layout_structure.get("header", {})
        if "title" in header:
            layout_components.append(HTML(f"<h2 class='govuk-heading-l'>{header['title']}</h2>"))
        if "description" in header:
            layout_components.append(HTML(f"<p class='govuk-body'>{header['description']}</p>"))
        if "status_message" in header:
            layout_components.append(HTML(header["status_message"]))
        if "help_text" in header:
            layout_components.append(HTML(header["help_text"]))

        # Once we settle on a design we can remove one of the following two blocks.
        # The first covers the tabbed form design...
        if layout_structure.get("use_tabs", False) and layout_structure.get("tabs", []):
            tab_panels = []
            for tab in layout_structure["tabs"]:
                tab_fields = []
                for field_name in tab.get("fields", []):
                    if (
                        field_name == "status"
                        and "status" in form_fields
                        and isinstance(form_fields["status"], forms.ChoiceField)
                    ):
                        tab_fields.append(Field.radios(field_name))
                    else:
                        tab_fields.append(Field(field_name))

                if tab_fields:
                    tab_panel = TabPanel(tab.get("label", "Tab"), *tab_fields, css_id=tab.get("id"))
                    tab_panels.append(tab_panel)

            if tab_panels:
                layout_components.append(Tabs(*tab_panels))
        else:
            # ...and the original, non-tabbed design
            for group in layout_structure.get("groups", []):
                group_fields = []
                if "title" in group:
                    group_fields.append(HTML(f"<h3 class='govuk-heading-m'>{group['title']}</h3>"))

                for field_name in group.get("fields", []):
                    if (
                        field_name == "status"
                        and "status" in form_fields
                        and isinstance(form_fields["status"], forms.ChoiceField)
                    ):
                        group_fields.append(Field.radios(field_name))
                    else:
                        group_fields.append(Field(field_name))
                if group_fields:
                    layout_components.append(Fieldset(*group_fields))

        button_text = layout_structure.get("button_text", "Save and Continue")
        layout_components.append(Button("submit", button_text, css_class="govuk-button"))
        self.helper.layout = Layout(*layout_components)

    FormClass.__init__ = form_init  # type: ignore

    return FormClass
