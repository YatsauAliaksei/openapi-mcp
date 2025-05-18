import importlib
import textwrap
from unittest.mock import patch

import pytest
import src.utils.config as config_mod
from src.utils.auth import get_basic_auth_header
from src.utils.config import load_dotenv_if_available
from src.utils.env_utils import get_env_var
from src.utils.logging_utils import setup_logging
from src.utils.openapi_loader import load_openapi_spec
from src.utils.openapi_utils import _extract_example_text


def test_get_basic_auth_headers(monkeypatch):
    monkeypatch.setenv("SMS_API_KEY", "key")
    monkeypatch.setenv("SMS_API_SECRET", "secret")
    headers = get_basic_auth_header("sms")
    assert isinstance(headers, dict)
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")

def test_load_dotenv_if_available(monkeypatch):
    # Patch dotenv.load_dotenv to check it is called
    with patch("dotenv.load_dotenv") as mock_load:
        load_dotenv_if_available()
        mock_load.assert_called_once()

def test_get_env_var(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert get_env_var("FOO") == "bar"
    assert get_env_var("MISSING", "default") == "default"

def test_setup_logging_creates_logger(tmp_path):
    logger = setup_logging("test_logger", level=10, log_file=str(tmp_path / "log.txt"))
    assert logger.name == "[test_logger]"
    assert logger.level == 10


def test_resolve_ref_and_extract_example_text():
    # Test with top-level example
    schema = {"type": "string", "example": "baz"}
    example_text = _extract_example_text(schema)
    assert "baz" in example_text

    # Test with examples dict
    schema2 = {"type": "string", "examples": {"ex1": {"value": "qux"}}}
    example_text2 = _extract_example_text(schema2)
    assert "qux" in example_text2

    # Test with no example
    schema3 = {"type": "string"}
    example_text3 = _extract_example_text(schema3)
    assert example_text3 == ""

def test_load_openapi_spec_file(tmp_path):
    # Write a minimal openapi.json file
    openapi_path = tmp_path / "openapi.json"
    openapi_path.write_text(
        '{"openapi": "3.0.0", "paths": {}, "info": {"title": "Test API", "version": "1.0.0"}}',
        encoding="utf-8",
    )
    spec = load_openapi_spec(str(openapi_path))
    assert spec["openapi"] == "3.0.0"
    assert "paths" in spec

def _write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def test_load_openapi_spec_local_file(tmp_path):
    # Should load from local file (YAML and JSON)
    yaml_content = textwrap.dedent("""
    openapi: "3.0.0"
    info:
      title: Test API
      version: "1.0.0"
    paths: {}
    """)
    json_content = '{"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}'
    yaml_path = tmp_path / "openapi.yaml"
    json_path = tmp_path / "openapi.json"
    _write_file(yaml_path, yaml_content)
    _write_file(json_path, json_content)
    # Should load YAML
    spec_yaml = load_openapi_spec(str(yaml_path))
    assert spec_yaml["openapi"] == "3.0.0"
    # Should load JSON
    spec_json = load_openapi_spec(str(json_path))
    assert spec_json["openapi"] == "3.0.0"

def test_load_openapi_spec_fallback(tmp_path, monkeypatch):
    # Should fallback to openapi.json, openapi.yaml, openapi.yml in order
    # Remove all files first
    for fname in ["openapi.json", "openapi.yaml", "openapi.yml"]:
        try:
            (tmp_path / fname).unlink()
        except FileNotFoundError:
            pass
    # Valid minimal OpenAPI spec (JSON and YAML)
    json_content = '{"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}'
    yaml_content = (
        "openapi: '3.0.0'\n"
        "info:\n"
        "  title: Test API\n"
        "  version: '1.0.0'\n"
        "paths: {}\n"
    )
    # 1. openapi.json
    (tmp_path / "openapi.json").write_text(json_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    spec = load_openapi_spec()
    assert spec["openapi"] == "3.0.0"
    (tmp_path / "openapi.json").unlink()
    # 2. openapi.yaml
    (tmp_path / "openapi.yaml").write_text(yaml_content, encoding="utf-8")
    spec = load_openapi_spec()
    assert spec["openapi"] == "3.0.0"
    (tmp_path / "openapi.yaml").unlink()
    # 3. openapi.yml
    (tmp_path / "openapi.yml").write_text(yaml_content, encoding="utf-8")
    spec = load_openapi_spec()
    assert spec["openapi"] == "3.0.0"
    (tmp_path / "openapi.yml").unlink()

def test_load_openapi_spec_not_found(tmp_path, monkeypatch):
    # Should raise if no file found
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Exception, match="No such file or directory"):
        load_openapi_spec("nonexistent.yaml")

# --- Fallback config tests: env var mode and empty mode ---

def test_openapi_specs_env_var_fallback(monkeypatch):
    """
    Test that config.openapi_specs returns a single OpenAPISpec when config file is missing
    and required environment variables are set.
    """
    # Point config to a nonexistent file
    monkeypatch.setenv("OPENAPI_MCP_CONFIG", "/tmp/does_not_exist.yaml")
    # Set required env vars
    monkeypatch.setenv("OPENAPI_SPEC_PATH", "/tmp/spec.yaml")
    monkeypatch.setenv("OPENAPI_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("OPENAPI_AUTH_TYPE", "Bearer")
    monkeypatch.setenv("OPENAPI_BEARER_TOKEN", "token123")
    monkeypatch.setenv("OPENAPI_SERVICE_NAME", "myapi")

    # Reload config module to pick up env changes
    importlib.reload(config_mod)
    specs = config_mod.config.openapi_specs
    assert len(specs) == 1
    spec = specs[0]
    assert spec.file_location == "/tmp/spec.yaml"
    assert spec.base_url == "https://api.example.com"
    assert spec.auth_type == "Bearer"
    assert spec.service_name == "myapi"
    assert spec.prefix == "myapi"

def test_openapi_specs_empty_if_no_config_and_no_env(monkeypatch):
    """
    Test that config.openapi_specs returns an empty list if neither config nor env vars are present.
    """
    monkeypatch.setenv("OPENAPI_MCP_CONFIG", "/tmp/does_not_exist.yaml")
    monkeypatch.delenv("OPENAPI_SPEC_PATH", raising=False)
    monkeypatch.delenv("OPENAPI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAPI_AUTH_TYPE", raising=False)
    monkeypatch.delenv("OPENAPI_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("OPENAPI_BASIC_KEY", raising=False)
    monkeypatch.delenv("OPENAPI_BASIC_SECRET", raising=False)
    monkeypatch.delenv("OPENAPI_SERVICE_NAME", raising=False)

    importlib.reload(config_mod)
    specs = config_mod.config.openapi_specs
    assert specs == []
