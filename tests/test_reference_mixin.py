from unittest.mock import patch

from django.db import models
from django.test import TestCase

from webcaf.webcaf.models import ReferenceGeneratorMixin


class DummyModel(ReferenceGeneratorMixin, models.Model):
    reference = models.CharField(max_length=20, null=False, unique=True)

    class Meta:
        app_label = "testapp"
        managed = False

    def __init__(self, pk=None, reference=None):
        super().__init__()
        self._pk_val = pk
        self.reference = reference

    @property
    def pk(self):
        return self._pk_val

    @pk.setter
    def pk(self, value):
        self._pk_val = value


class ReferenceGeneratorMixinTest(TestCase):
    def setUp(self):
        self.gen_ref_patcher = patch("webcaf.webcaf.models.generate_reference", return_value="AAAAA")
        self.mock_generate = self.gen_ref_patcher.start()
        self.save_patcher = patch.object(models.Model, "save")
        self.mock_save = self.save_patcher.start()

    def tearDown(self):
        self.gen_ref_patcher.stop()
        self.save_patcher.stop()

    def test_reference_generated_on_save_with_no_reference(self):
        obj = DummyModel(pk=1, reference=None)
        obj.__class__.__name__ = "Dummy"
        obj.save()
        self.mock_generate.assert_called_with(1, prime_set="dummy")
        self.assertEqual(obj.reference, "AAAAA")

    def test_reference_not_overwritten_if_already_set(self):
        obj = DummyModel(pk=1, reference="BBBBB")
        obj.__class__.__name__ = "Dummy"
        obj.save()
        self.mock_generate.assert_not_called()
        self.assertEqual(obj.reference, "BBBBB")

    def test_model_name_passed_to_generate_reference(self):
        obj = DummyModel(pk=42, reference=None)
        obj.__class__.__name__ = "Blah"
        obj.save()
        self.mock_generate.assert_called_with(42, prime_set="blah")
