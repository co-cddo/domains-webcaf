import unittest

from crispy_forms_gds.layout import Button, Fieldset
from django import forms
from django.test import TestCase

from webcaf.webcaf.caf32_field_providers import FieldProvider
from webcaf.webcaf.form_factory import create_form


class MockProvider(FieldProvider):
    def __init__(self, metadata=None, field_defs=None, layout=None):
        self.metadata = metadata or {"id": "test_form"}
        self.field_defs = field_defs or []
        self.layout = layout or {"header": {}, "groups": []}

    def get_metadata(self):
        return self.metadata

    def get_field_definitions(self):
        return self.field_defs

    def get_layout_structure(self):
        return self.layout


class FormFactoryTestCase(TestCase):
    def test_boolean_field_has_correct_field_type_and_attributes(self):
        provider = MockProvider(
            field_defs=[{"name": "test_checkbox", "label": "Test Checkbox", "type": "boolean", "required": True}]
        )
        form_class = create_form(provider)
        form = form_class()
        self.assertIn("test_checkbox", form.fields)
        self.assertIsInstance(form.fields["test_checkbox"], forms.BooleanField)
        self.assertEqual(form.fields["test_checkbox"].label, "Test Checkbox")
        self.assertTrue(form.fields["test_checkbox"].required)
        self.assertIsInstance(form.fields["test_checkbox"].widget, forms.CheckboxInput)

    def test_choice_field_has_correct_field_type_and_attributes(self):
        choices = [("a", "Option A"), ("b", "Option B")]
        provider = MockProvider(
            field_defs=[
                {
                    "name": "test_choice",
                    "label": "Test Choice",
                    "type": "choice",
                    "choices": choices,
                    "initial": "a",
                    "widget": "radio",
                }
            ]
        )
        form_class = create_form(provider)
        form = form_class()

        self.assertIn("test_choice", form.fields)
        self.assertIsInstance(form.fields["test_choice"], forms.ChoiceField)
        self.assertEqual(form.fields["test_choice"].label, "Test Choice")
        self.assertEqual(form.fields["test_choice"].choices, choices)
        self.assertEqual(form.fields["test_choice"].initial, "a")
        self.assertIsInstance(form.fields["test_choice"].widget, forms.RadioSelect)

    def test_text_field_has_correct_field_type_and_attributes(self):
        provider = MockProvider(
            field_defs=[
                {
                    "name": "test_text",
                    "label": "Test Text",
                    "type": "text",
                    "required": True,
                    "widget_attrs": {"rows": 5, "maxlength": 200},
                }
            ]
        )
        form_class = create_form(provider)
        form = form_class()
        self.assertIn("test_text", form.fields)
        self.assertIsInstance(form.fields["test_text"], forms.CharField)
        self.assertEqual(form.fields["test_text"].label, "Test Text")
        self.assertTrue(form.fields["test_text"].required)
        self.assertIsInstance(form.fields["test_text"].widget, forms.Textarea)
        self.assertEqual(form.fields["test_text"].widget.attrs["rows"], 5)
        self.assertEqual(form.fields["test_text"].widget.attrs["maxlength"], 200)

    def test_header_is_included_in_form_html(self):
        provider = MockProvider(
            layout={
                "header": {
                    "title": "Test Form Title",
                    "description": "Test form description",
                    "status_message": "<p>Status message</p>",
                    "help_text": "<p>Help text</p>",
                },
                "groups": [],
            }
        )
        form_class = create_form(provider)
        form = form_class()
        layout_components = form.helper.layout.fields
        html_content = [component.html for component in layout_components if hasattr(component, "html")]
        self.assertTrue(any("Test Form Title" in content for content in html_content))
        self.assertTrue(any("Test form description" in content for content in html_content))
        self.assertTrue(any("Status message" in content for content in html_content))
        self.assertTrue(any("Help text" in content for content in html_content))

    def test_field_groups_are_included_in_form_html(self):
        provider = MockProvider(
            field_defs=[
                {"name": "field1", "label": "Field 1", "type": "boolean"},
                {"name": "field2", "label": "Field 2", "type": "boolean"},
                {"name": "status", "label": "Status", "type": "choice", "choices": [("a", "A")], "widget": "radio"},
            ],
            layout={
                "header": {},
                "groups": [{"title": "Group 1", "fields": ["field1"]}, {"fields": ["field2", "status"]}],
            },
        )
        form_class = create_form(provider)
        form = form_class()
        fieldsets = [f for f in form.helper.layout.fields if isinstance(f, Fieldset)]
        self.assertEqual(len(fieldsets), 2)
        first_fieldset_fields = fieldsets[0].fields

        html_content = [field.html for field in first_fieldset_fields if hasattr(field, "html")]
        self.assertTrue(any("Group 1" in content for content in html_content))

        field_names = []
        for fieldset in fieldsets:
            for item in fieldset.fields:
                # item could be html or a crispy_forms_gds.layout.fields.Field
                # which unhelpfully has an attribute called 'fields'
                if hasattr(item, "fields") and item.fields:
                    field_names.extend(item.fields)

        self.assertIn("field1", field_names)
        self.assertIn("field2", field_names)
        self.assertIn("status", field_names)

    def test_button_is_created_with_correct_attributes(self):
        provider = MockProvider(layout={"header": {}, "groups": [], "button_text": "Custom Submit"})
        form_class = create_form(provider)
        form = form_class()
        buttons = [f for f in form.helper.layout.fields if isinstance(f, Button)]
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].value, "Custom Submit")
        self.assertIn("govuk-button", buttons[0].field_classes)

    def test_multiple_field_types_each_have_correct_type(self):
        provider = MockProvider(
            field_defs=[
                {"name": "checkbox", "label": "Checkbox", "type": "boolean"},
                {"name": "choice", "label": "Choice", "type": "choice", "choices": [("a", "A"), ("b", "B")]},
                {"name": "text", "label": "Text", "type": "text"},
            ]
        )
        form_class = create_form(provider)
        form = form_class()

        self.assertIn("checkbox", form.fields)
        self.assertIn("choice", form.fields)
        self.assertIn("text", form.fields)

        self.assertIsInstance(form.fields["checkbox"], forms.BooleanField)
        self.assertIsInstance(form.fields["choice"], forms.ChoiceField)
        self.assertIsInstance(form.fields["text"], forms.CharField)


if __name__ == "__main__":
    unittest.main()
