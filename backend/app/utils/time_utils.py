"""
Duration formatting utilities.
"""


def format_seconds(seconds: int | None) -> str:
    """Convert raw seconds to a human-readable duration string.

    Examples:
        3720 → "1h 2m"
        540  → "9m"
        None → "0m"
    """
    if seconds is None:
        return "0m"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
