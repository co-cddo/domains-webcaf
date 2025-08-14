from django import forms
from django.test import TestCase

from webcaf.webcaf.caf_loader.caf32_field_providers import FieldProvider
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
