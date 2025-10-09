import string
import unittest

from webcaf.webcaf.utils.references import generate_reference


class TestGenerateReferences(unittest.TestCase):
    def test_first_reference_is_fully_populated(self):
        """
        Test that the first reference does not have the pattern 00001,
        AAAAB or similar.
        """
        reference = generate_reference(0)
        self.assertEqual(reference, "ZBV31")

    def test_references_are_deterministic(self):
        references = [generate_reference(i) for i in range(5)]
        self.assertListEqual(references, ["ZBV31", "D1361", "TP981", "8DJB1", "P2RD1"])
        references = [generate_reference(i) for i in range(999, 1005)]
        self.assertListEqual(references, ["VRB4H", "9GK6H", "Q4S8H", "5T0CH", "LH7FH", "16GHH"])
        references = [generate_reference(i) for i in range(10000000, 10000005)]
        self.assertListEqual(references, ["9GWBQ", "Q44FQ", "5TBHQ", "LHKKQ", "16SMQ"])

    def test_references_are_expected_length(self):
        """
        Test that the references are the expected length.
        """
        for num_chars in range(1, 10):
            reference = generate_reference(0, num_chars=num_chars)
            self.assertEqual(len(reference), num_chars)

    def test_too_large_primary_key_raises_value_error(self):
        """
        Test that a ValueError is raised if the primary key is too large
        to generate a unique reference with the given number of characters.
        """
        # Defaults: five characters
        try:
            generate_reference(24299999)  # Max acceptable value
        except ValueError:
            self.fail("ValueError was raised and should not have been")
        with self.assertRaises(ValueError):
            generate_reference(24300000)
        with self.assertRaises(ValueError):
            generate_reference(30000000)
        # 4 characters
        try:
            generate_reference(1679615)  # Max acceptable value
        except ValueError:
            self.fail("ValueError was raised and should not have been")
        with self.assertRaises(ValueError):
            generate_reference(1679616, num_chars=4)
        with self.assertRaises(ValueError):
            generate_reference(2000000, num_chars=4)

    def test_we_get_the_first_reference_again_with_expected_pk(self):
        """
        Test that the maximum primary key that can be used is correct.
        """
        # Defaults: five characters from a set of 30
        ref_1 = generate_reference(0)
        ref_2 = generate_reference(24300000, skip_size_check=True)
        self.assertEqual(ref_1, "ZBV31")
        self.assertEqual(ref_1, ref_2)
        # 4 chars from a set of 36
        char_set = string.digits + string.ascii_uppercase
        ref_1 = generate_reference(0, num_chars=4, char_set=char_set)
        ref_2 = generate_reference(1679616, num_chars=4, char_set=char_set, skip_size_check=True)
        self.assertEqual(ref_1, "5T83")
        self.assertEqual(ref_1, ref_2)

    def test_we_get_get_a_reference_back_with_different_prime_sets(self):
        ref_1 = generate_reference(0, prime_set="assessment")
        ref_2 = generate_reference(0, prime_set="system")
        ref_3 = generate_reference(0, prime_set="organisation")
        self.assertEqual(ref_1, "CH7L1")
        self.assertEqual(ref_2, "KLL32")
        self.assertEqual(ref_3, "1WNW1")
