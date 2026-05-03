import phonenumbers
import re


def normalize_phone(raw: str) -> str | None:
    """
    Normalize a phone number input to international format (+62xxx).
    Supports spaces, dashes, parentheses, and various prefixes.
    """
    if not raw:
        return None

    # Step 1: Remove all characters except digits and the '+' sign
    cleaned = re.sub(r"[^\d+]+", "", raw.strip())

    # Step 2: Handle prefixes for Indonesia
    # Case 08xxx -> +628xxx
    if cleaned.startswith("0"):
        cleaned = "+62" + cleaned[1:]
    # Case 628xxx -> +628xxx
    elif cleaned.startswith("62") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    # Case +08xxx -> +628xxx
    elif cleaned.startswith("+0"):
        cleaned = "+62" + cleaned[2:]
    # Case 8xxx (no prefix) -> +628xxx
    elif not cleaned.startswith("+"):
        cleaned = "+62" + cleaned

    # If no country code at all, assume +62
    if not cleaned.startswith("+"):
        cleaned = "+62" + cleaned

    try:
        parsed = phonenumbers.parse(cleaned, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        return None
    except phonenumbers.NumberParseException:
        return None


def format_display_number(e164: str) -> str:
    """Format E.164 number for display purposes."""
    try:
        parsed = phonenumbers.parse(e164, None)
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
    except phonenumbers.NumberParseException:
        return e164
