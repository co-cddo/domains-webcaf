from django.core.exceptions import ValidationError
from django.test import TestCase

from webcaf.webcaf.forms.factory import WordCountValidator


class TestWordCountValidator(TestCase):
    """
    Test the WordCountValidator used in review forms to enforce word count limits.
    """

    def test_accepts_text_within_limit(self):
        """Test that text with word count <= max_words is accepted."""
        validator = WordCountValidator(750)
        text = " ".join(["word"] * 750)
        # Should not raise ValidationError
        validator(text)

    def test_accepts_text_below_limit(self):
        """Test that text with word count < max_words is accepted."""
        validator = WordCountValidator(750)
        text = " ".join(["word"] * 500)
        # Should not raise ValidationError
        validator(text)

    def test_rejects_text_over_limit(self):
        """Test that text with word count > max_words raises ValidationError."""
        validator = WordCountValidator(750)
        text = " ".join(["word"] * 751)
        with self.assertRaises(ValidationError) as context:
            validator(text)
        self.assertIn("751", str(context.exception))
        self.assertIn("750", str(context.exception))

    def test_boundary_exactly_max_words(self):
        """Test boundary condition: exactly max_words should be accepted."""
        validator = WordCountValidator(10)
        text = " ".join(["word"] * 10)
        # Should not raise ValidationError
        validator(text)

    def test_boundary_one_over_max_words(self):
        """Test boundary condition: max_words + 1 should be rejected."""
        validator = WordCountValidator(10)
        text = " ".join(["word"] * 11)
        with self.assertRaises(ValidationError) as context:
            validator(text)
        self.assertIn("11", str(context.exception))

    def test_handles_empty_string(self):
        """Test that empty string is accepted (0 words)."""
        validator = WordCountValidator(750)
        text = ""
        # Should not raise ValidationError
        validator(text)

    def test_handles_whitespace_only(self):
        """Test that whitespace-only string is accepted (0 words after split)."""
        validator = WordCountValidator(750)
        text = "   \n\t  "
        # Should not raise ValidationError - split() will result in empty list
        validator(text)

    def test_counts_words_with_multiple_spaces(self):
        """Test that multiple spaces between words don't affect count."""
        validator = WordCountValidator(5)
        text = "word1  word2   word3    word4     word5"
        # Should not raise ValidationError - split() handles multiple spaces
        validator(text)

    def test_counts_words_with_newlines(self):
        """Test that newlines are treated as word separators."""
        validator = WordCountValidator(5)
        text = "word1\nword2\nword3\nword4\nword5"
        # Should not raise ValidationError
        validator(text)

    def test_counts_words_with_tabs(self):
        """Test that tabs are treated as word separators."""
        validator = WordCountValidator(5)
        text = "word1\tword2\tword3\tword4\tword5"
        # Should not raise ValidationError
        validator(text)

    def test_error_message_format(self):
        """Test that error message includes both limit and actual count."""
        validator = WordCountValidator(100)
        text = " ".join(["word"] * 150)
        with self.assertRaises(ValidationError) as context:
            validator(text)
        error_message = str(context.exception)
        self.assertIn("Ensure this value has at most 100 words", error_message)
        self.assertIn("it has 150", error_message)

    def test_equality_same_max_words(self):
        """Test that two validators with same max_words are equal."""
        validator1 = WordCountValidator(750)
        validator2 = WordCountValidator(750)
        self.assertEqual(validator1, validator2)

    def test_inequality_different_max_words(self):
        """Test that two validators with different max_words are not equal."""
        validator1 = WordCountValidator(750)
        validator2 = WordCountValidator(500)
        self.assertNotEqual(validator1, validator2)

    def test_inequality_different_type(self):
        """Test that validator is not equal to non-validator objects."""
        validator = WordCountValidator(750)
        self.assertNotEqual(validator, "not a validator")
        self.assertNotEqual(validator, 750)
        self.assertNotEqual(validator, None)

    def test_deconstructible(self):
        """Test that the validator can be deconstructed (for migrations)."""
        validator = WordCountValidator(750)
        # This should not raise an error
        path, args, kwargs = validator.deconstruct()
        self.assertEqual(path, "webcaf.webcaf.forms.factory.WordCountValidator")
        self.assertEqual(args, (750,))
        self.assertEqual(kwargs, {})

    def test_reconstructible(self):
        """Test that a validator can be reconstructed from its deconstruction."""
        validator1 = WordCountValidator(750)
        path, args, kwargs = validator1.deconstruct()
        # Reconstruct from the deconstructed parts
        validator2 = WordCountValidator(*args, **kwargs)
        self.assertEqual(validator1, validator2)
