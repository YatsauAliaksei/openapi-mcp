"""
auth.py

Provides authentication helpers for tool functions.
Currently supports Basic Authentication using environment variables.
Provides: get_basic_auth_headers() -> dict[str, str]
"""

import base64

from src.utils.config import config
from src.utils.env_utils import get_env_var


def get_basic_auth_header(service_name: str) -> dict:
    """
    Returns HTTP headers for Basic Authentication using credentials from config.yaml.
    Falls back to environment variables for backward compatibility.
    """
    auth = config.get_openapi_authentication(service_name)
    key = None
    secret = None
    if auth:
        key = auth.get("api_key")
        secret = auth.get("api_secret")
    # Fallback to env vars if not found in config
    if not key or not secret:
        key = get_env_var(f"{service_name.upper()}_API_KEY")
        secret = get_env_var(f"{service_name.upper()}_API_SECRET")
    if not key or not secret:
        raise RuntimeError(
            f"Missing API credentials for service '{service_name}'. "
            f"Set 'api_key' and 'api_secret' in config.yaml under openapi.{service_name}.authentication, "
            f"or set {service_name.upper()}_API_KEY and {service_name.upper()}_API_SECRET in environment variables."
        )

    userpass = f"{key}:{secret}".encode("utf-8")
    b64 = base64.b64encode(userpass).decode("utf-8")
    return {"Authorization": f"Basic {b64}"}

def get_bearer_auth_header(service_name: str) -> dict:
    """
    Returns HTTP headers for Bearer Authentication using credentials from config.yaml.
    Falls back to environment variables for backward compatibility.
    """
    auth = config.get_openapi_authentication(service_name)
    api_token = None
    if auth:
        api_token = auth.get("api_token")
    # Fallback to env var if not found in config
    if not api_token:
        api_token = get_env_var(f"{service_name.upper()}_API_TOKEN")
    if not api_token:
        raise RuntimeError(
            f"Missing API token for service '{service_name}'. "
            f"Set 'api_token' in config.yaml under openapi.{service_name}.authentication, "
            f"or set {service_name.upper()}_API_TOKEN in environment variables."
        )
    return {"Authorization": f"Bearer {api_token}"}

def get_auth_header(auth_type: str, service_name: str) -> dict:
    if auth_type.lower() == "basic":
        return get_basic_auth_header(service_name)
    elif auth_type.lower() == "bearer":
        return get_bearer_auth_header(service_name)
    else:
        raise ValueError(f"Unsupported auth type: {auth_type}. Supported types are 'basic' and 'bearer'.")