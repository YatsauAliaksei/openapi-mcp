import os
from dataclasses import dataclass
from typing import List

import yaml

from src.utils.env_utils import get_env_var


def load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv is optional

load_dotenv_if_available()

def _load_yaml_config():
    """
    Load the YAML config file.
    Priority:
      1. If the environment variable OPENAPI_MCP_CONFIG is set, use its value as the config path.
      2. Otherwise, use the default config.yaml in the project root.
    """
    env_config_path = os.environ.get("OPENAPI_MCP_CONFIG")
    print(f"Environment variable OPENAPI_MCP_CONFIG: {env_config_path}")
    if env_config_path:
        config_path = os.path.abspath(env_config_path)
    else:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config.yaml")
        config_path = os.path.abspath(config_path)
    
    print(f"Loading config from: {config_path}")
    if not os.path.exists(config_path):
        from src.utils.logging_utils import setup_logging
        setup_logging().error(f"Config file not found: {config_path}")
        return {}
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


@dataclass
class OpenAPISpec:
    service_name: str
    file_location: str
    prefix: str
    auth_type: str = None
    base_url: str = None
    include_tags: list = None
    exclude_tags: list = None
    include_paths: list = None
    exclude_paths: list = None

class Config:
    def __init__(self):
        self._yaml = _load_yaml_config()

    def _get(self, *keys, env=None, default=None):
        # 1. Check environment variable first
        if env:
            env_val = get_env_var(env, None)
            if env_val is not None:
                return env_val
        # 2. Try YAML (nested keys)
        d = self._yaml
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                d = None
                break
        if d is not None:
            return d
        # 3. Default
        return default

    @property
    def openapi_services(self):
        """Return a list of available OpenAPI service names (e.g., sms, message_media)."""
        openapi = self._get("openapi", default={})
        if isinstance(openapi, dict):
            return list(openapi.keys())
        return []

    def get_openapi_file_location(self, service):
        """Get the file_location for a given OpenAPI service."""
        return self._get("openapi", service, "file_location")

    def get_openapi_base_url(self, service):
        """Get the base_url for a given OpenAPI service."""
        return self._get("openapi", service, "base_url")

    def get_openapi_authentication(self, service):
        """
        Get the full authentication dict for a given OpenAPI service.
        Returns None if not present.
        """
        return self._get("openapi", service, "authentication", default=None)

    def get_openapi_auth_type(self, service):
        """
        Get the auth_type for a given OpenAPI service.
        Looks under the authentication section if present.
        """
        auth = self.get_openapi_authentication(service)
        if auth and "auth_type" in auth:
            return auth["auth_type"]
        # Fallback to legacy location for backward compatibility
        return self._get("openapi", service, "auth_type")

    @property
    def DEBUG(self):
        val = self._get("debug", env="DEBUG", default="0")
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("1", "true", "yes")

    @property
    def LOG_FILE(self):
        return self._get("log_file", env="LOG_FILE", default="")

    @property
    def openapi_specs(self) -> List[OpenAPISpec]:
        """
        Return a list of OpenAPISpec objects for all openapi services.
        If no config file is present, supports fallback to environment variables:
            - OPENAPI_SPEC_PATH: Path or URL to the OpenAPI spec (required)
            - OPENAPI_BASE_URL: Base URL for the API (required)
            - OPENAPI_AUTH_TYPE: "Bearer" or "Basic" (optional, default: None)
            - OPENAPI_BEARER_TOKEN: Bearer token (if using Bearer auth)
            - OPENAPI_BASIC_KEY: Basic auth key/username (if using Basic auth)
            - OPENAPI_BASIC_SECRET: Basic auth secret/password (if using Basic auth)
            - OPENAPI_SERVICE_NAME: Service name/prefix (optional, default: "default")
        """
        specs = []

        # If config file is present and has openapi services, use them
        if self.openapi_services:
            for service in self.openapi_services:
                file_location = self.get_openapi_file_location(service)
                auth_type = self.get_openapi_auth_type(service)
                # New: parse include/exclude tags/paths
                openapi_service = self._get("openapi", service, default={})
                include_tags = openapi_service.get("include_tags", None)
                exclude_tags = openapi_service.get("exlude_tags", None) or openapi_service.get("exclude_tags", None)
                include_paths = openapi_service.get("include_paths", None)
                exclude_paths = openapi_service.get("exclude_paths", None)
                # Normalize to list if present
                def to_list(val):
                    if val is None:
                        return None
                    if isinstance(val, list):
                        return val
                    if isinstance(val, str):
                        return [v.strip() for v in val.split(",") if v.strip()]
                    return None
                include_tags = to_list(include_tags)
                exclude_tags = to_list(exclude_tags)
                include_paths = to_list(include_paths)
                exclude_paths = to_list(exclude_paths)
                if file_location:
                    specs.append(OpenAPISpec(
                        service_name=service,
                        file_location=file_location,
                        prefix=service,  # prefix can be customized if needed
                        auth_type=auth_type,
                        include_tags=include_tags,
                        exclude_tags=exclude_tags,
                        include_paths=include_paths,
                        exclude_paths=exclude_paths
                    ))
            return specs

        # Fallback: check for environment variables
        spec_path = get_env_var("OPENAPI_SPEC_PATH")
        base_url = get_env_var("OPENAPI_BASE_URL")
        auth_type = get_env_var("OPENAPI_AUTH_TYPE")
        service_name = get_env_var("OPENAPI_SERVICE_NAME", "default")
        # Only add if both spec_path and base_url are present
        if spec_path and base_url:
            specs.append(OpenAPISpec(
                service_name=service_name,
                file_location=spec_path,
                prefix=service_name,
                auth_type=auth_type,
                base_url=base_url,
                include_tags=None,
                exclude_tags=None,
                include_paths=None,
                exclude_paths=None
            ))
        return specs

config = Config()