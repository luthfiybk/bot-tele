import re

def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.
    """
    if not text:
        return ""
    # Characters that must be escaped in MarkdownV2
    special_chars = r"_*[]()~`>#+-=|{}.!\\"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped
