import re

EMAIL_RE = re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")


def mask_email(text: str):
    """
    Replace email addresses with a masked version.

    This function identifies email addresses in the input text and replaces them
    with a masked version where only the first two characters of the email username
    are preserved, followed by "***". The domain part of the email remains unchanged.

    :param text: The input text containing email addresses to be masked.
    :type text: str
    :return: The text with email addresses masked.
    :rtype: str
    """
    """Replace email addresses with a masked version"""
    return EMAIL_RE.sub(lambda m: f"{m.group(1)[:2]}***@{m.group(2)}", text)
