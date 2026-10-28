from django.test import TestCase

from webcaf.webcaf.tip.forms import TipSubmitForm


class TestTipSubmitForm(TestCase):
    def test_confirm_is_required_with_gds_message(self):
        form = TipSubmitForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["confirm"],
            [
                "Confirm that your organisation's GovAssure senior responsible officer (SRO) "
                "has signed off the contents of this TIP"
            ],
        )
        self.assertNotIn("confirm_lgd", form.errors)

    def test_valid_when_confirmed(self):
        form = TipSubmitForm(data={"confirm": "True"})
        self.assertTrue(form.is_valid())
