import os


def get_env_var(key, default=None):
    """
    Get an environment variable value case-insensitively.
    - Checks for both upper and lower case variants.
    - Raises ValueError if both are set.
    - Returns the value if one is set, or the default.
    """
    upper = key.upper()
    lower = key.lower()
    has_upper = upper in os.environ
    has_lower = lower in os.environ

    if has_upper and has_lower:
        raise ValueError(
            f"Ambiguous environment variable: both '{upper}' and '{lower}' are set. Please set only one."
        )
    if has_upper:
        return os.environ[upper]
    if has_lower:
        return os.environ[lower]
    return default
