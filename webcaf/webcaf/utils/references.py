import string

CHAR_SET = string.digits + "".join([char for char in string.ascii_uppercase if char not in "AEIOUY"])

PRIMES = {
    "default": (60013, 104729),
    "assessment": (11547, 492761),
    "system": (97103, 907757),
    "organisation": (94327, 747811),
}


def generate_reference(
    pk: int, num_chars: int = 5, prime_set: str = "default", char_set: str = CHAR_SET, skip_size_check: bool = False
) -> str:
    """
    Generate a N-character alphanumeric reference for the based on a primary key.
    The index consists of uppercase letters and numbers and appears random while in
    fact being deterministic. This allows generation of memorable references from
    pk=0 onwards without the need to check for uniqueness.

    Args:
        pk: The primary key of the system
        num_chars: Number of characters in the reference (default: 5)
        prime_set: Which set of primes to use (default: "default")
        char_set: The set of characters to use (default: digits + uppercase letters minus vowels)
        skip_size_check: If True, skip the check that the pk is too large. For testing.

    Returns:
        str: An alphanumeric reference.
    """
    len_char_set = len(char_set)
    if not skip_size_check and pk >= len_char_set**num_chars:
        raise ValueError("Primary key is too large to generate a unique reference with the given number of characters.")
    prime_1 = PRIMES[prime_set][0]
    prime_2 = PRIMES[prime_set][1]
    reference_value = (pk * prime_1 + prime_2) % (len_char_set**num_chars) + len_char_set ** (num_chars - 1)
    reference_chars = []
    for _ in range(num_chars):
        char_idx = reference_value % len_char_set
        reference_chars.append(char_set[char_idx])
        reference_value //= len_char_set
    while len(reference_chars) < num_chars:
        reference_chars.append(char_set[0])
    return "".join(reference_chars)
