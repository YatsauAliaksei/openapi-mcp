from unittest.mock import Mock, patch

import src.utils.config as config_mod
from src.tool_caller import OpenAPIToolCaller
from src.utils.config import OpenAPISpec


def test_get_metadata_of_all_channels_with_limit(monkeypatch):
    """
    Test that OpenAPIToolCaller correctly handles the getMetadataOfAllChannels operation from ably.yaml.
    """

    # Patch config to provide dummy credentials for sms
    config_mod.config._yaml.setdefault("openapi", {})
    config_mod.config._yaml["openapi"].setdefault("sms", {})
    config_mod.config._yaml["openapi"]["sms"]["authentication"] = {
        "auth_type": "Basic",
        "api_key": "dummy_key",
        "api_secret": "dummy_secret"
    }

    ably_spec_path = "specs/ably.yaml"
    base_url = "https://rest.ably.io"
    caller = OpenAPIToolCaller(
        openapi_specs=[
            OpenAPISpec(
                "sms",
                file_location=ably_spec_path,
                prefix="sms",
                auth_type="Basic",
                base_url=base_url,
            )
        ]
    )
    tool_name = "sms:getMetadataOfAllChannels"
    assert tool_name in caller.registry
    meta = caller.registry[tool_name]
    required = set(meta.required)
    # All parameters are optional for this operation
    assert required == set()

    arguments = {
        "limit": 1
    }
    expected_response = [{"channel": "test"}]

    with patch("requests.Session.send") as mock_send:
        mock_resp = Mock()
        mock_resp.json.return_value = expected_response
        mock_resp.raise_for_status = Mock()
        mock_resp.status_code = 200
        mock_send.return_value = mock_resp

        result = caller.call_tool(tool_name, arguments)

        mock_send.assert_called_once()
        assert result == expected_response

def test_get_metadata_of_channel(monkeypatch):
    """
    Test that OpenAPIToolCaller correctly handles the getMetadataOfChannel operation from ably.yaml.
    """
    # Patch config to provide dummy credentials for sms
    config_mod.config._yaml.setdefault("openapi", {})
    config_mod.config._yaml["openapi"].setdefault("sms", {})
    config_mod.config._yaml["openapi"]["sms"]["authentication"] = {
        "auth_type": "Basic",
        "api_key": "dummy_key",
        "api_secret": "dummy_secret"
    }

    ably_spec_path = "specs/ably.yaml"
    base_url = "https://rest.ably.io"
    caller = OpenAPIToolCaller(
        openapi_specs=[
            OpenAPISpec(
                "sms",
                file_location=ably_spec_path,
                prefix="sms",
                auth_type="Basic",
                base_url=base_url,
            )
        ]
    )
    tool_name = "sms:getMetadataOfChannel"
    assert tool_name in caller.tools

    arguments = {
        "channel_id": "test-channel"
    }
    expected_response = {"channel": "test-channel", "metadata": {}}

    with patch("requests.Session.send") as mock_send:
        mock_resp = Mock()
        mock_resp.json.return_value = expected_response
        mock_resp.raise_for_status = Mock()
        mock_resp.status_code = 200
        mock_send.return_value = mock_resp

        result = caller.call_tool(tool_name, arguments)

        mock_send.assert_called_once()
        assert result == expected_response

def test_multispec_prefix_and_baseurl(monkeypatch):
    """
    Test OpenAPIToolCaller with two specs (actually the same ably.yaml) and different prefixes.
    """
    # Patch config to provide dummy credentials for sms and ably2
    config_mod.config._yaml.setdefault("openapi", {})
    config_mod.config._yaml["openapi"].setdefault("sms", {})
    config_mod.config._yaml["openapi"]["sms"]["authentication"] = {
        "auth_type": "Basic",
        "api_key": "dummy_key",
        "api_secret": "dummy_secret"
    }
    config_mod.config._yaml["openapi"].setdefault("ably2", {})
    config_mod.config._yaml["openapi"]["ably2"]["authentication"] = {
        "auth_type": "Basic",
        "api_key": "dummy_key",
        "api_secret": "dummy_secret"
    }

    ably_spec_path = "specs/ably.yaml"
    base_url = "https://rest.ably.io"
    spec_sms = OpenAPISpec("sms", file_location=ably_spec_path, prefix="sms", auth_type="Basic", base_url=base_url)
    spec_ably2 = OpenAPISpec(
        "ably2",
        file_location=ably_spec_path,
        prefix="ably2",
        auth_type="Basic",
        base_url=base_url,
    )
    caller = OpenAPIToolCaller(openapi_specs=[spec_sms, spec_ably2])

    # Should have at least one tool from each spec with correct prefixes
    assert any(name.startswith("sms:") for name in caller.tools)
    assert any(name.startswith("ably2:") for name in caller.tools)

    # Pick a real tool from each spec for invocation
    sms_tool = "sms:getMetadataOfAllChannels"
    ably2_tool = "ably2:getMetadataOfAllChannels"
    assert sms_tool in caller.tools
    assert ably2_tool in caller.tools

    with patch("requests.Session.send") as mock_send:
        mock_resp = Mock()
        mock_resp.json.return_value = [{"channel": "test"}]
        mock_resp.raise_for_status = Mock()
        mock_resp.status_code = 200
        mock_send.return_value = mock_resp

        # Call sms:getMetadataOfAllChannels
        caller.call_tool(sms_tool, {"limit": 1})
        mock_send.assert_called()
        # Call ably2:getMetadataOfAllChannels
        caller.call_tool(ably2_tool, {"limit": 1})
        mock_send.assert_called()

def test_include_exclude_tags_paths(monkeypatch):
    """
    Test that OpenAPIToolCaller correctly filters tools by include/exclude tags and paths.
    """
    # Minimal OpenAPI spec with multiple paths and tags
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/foo": {
                "get": {
                    "operationId": "getFoo",
                    "tags": ["A", "B"],
                    "parameters": [],
                }
            },
            "/bar": {
                "post": {
                    "operationId": "postBar",
                    "tags": ["B", "C"],
                    "parameters": [],
                }
            },
            "/baz": {
                "get": {
                    "operationId": "getBaz",
                    "tags": ["C", "D"],
                    "parameters": [],
                }
            },
        }
    }

    # Patch load_openapi_spec to return our mock spec
    monkeypatch.setattr("src.tool_caller.load_openapi_spec", lambda path: spec)

    # Only include tag "A"
    spec_obj = OpenAPISpec(
        service_name="test",
        file_location="dummy.yaml",
        prefix="test",
        auth_type=None,
        base_url="https://dummy.api",
        include_tags=["A"],
        exclude_tags=None,
        include_paths=None,
        exclude_paths=None,
    )
    caller = OpenAPIToolCaller([spec_obj])
    tool_names = set(caller.tools.keys())
    assert any("getFoo" in name for name in tool_names)
    assert not any("postBar" in name for name in tool_names)
    assert not any("getBaz" in name for name in tool_names)

    # Exclude tag "B"
    spec_obj = OpenAPISpec(
        service_name="test",
        file_location="dummy.yaml",
        prefix="test",
        auth_type=None,
        base_url="https://dummy.api",
        include_tags=None,
        exclude_tags=["B"],
        include_paths=None,
        exclude_paths=None,
    )
    caller = OpenAPIToolCaller([spec_obj])
    tool_names = set(caller.tools.keys())
    assert not any("getFoo" in name for name in tool_names)
    assert not any("postBar" in name for name in tool_names)
    assert any("getBaz" in name for name in tool_names)

    # Include path "/bar"
    spec_obj = OpenAPISpec(
        service_name="test",
        file_location="dummy.yaml",
        prefix="test",
        auth_type=None,
        base_url="https://dummy.api",
        include_tags=None,
        exclude_tags=None,
        include_paths=["/bar"],
        exclude_paths=None,
    )
    caller = OpenAPIToolCaller([spec_obj])
    tool_names = set(caller.tools.keys())
    assert not any("getFoo" in name for name in tool_names)
    assert any("postBar" in name for name in tool_names)
    assert not any("getBaz" in name for name in tool_names)

    # Exclude path "/baz"
    spec_obj = OpenAPISpec(
        service_name="test",
        file_location="dummy.yaml",
        prefix="test",
        auth_type=None,
        base_url="https://dummy.api",
        include_tags=None,
        exclude_tags=None,
        include_paths=None,
        exclude_paths=["/baz"],
    )
    caller = OpenAPIToolCaller([spec_obj])
    tool_names = set(caller.tools.keys())
    assert any("getFoo" in name for name in tool_names)
    assert any("postBar" in name for name in tool_names)
    assert not any("getBaz" in name for name in tool_names)

    # Include tag "C", exclude path "/bar"
    spec_obj = OpenAPISpec(
        service_name="test",
        file_location="dummy.yaml",
        prefix="test",
        auth_type=None,
        base_url="https://dummy.api",
        include_tags=["C"],
        exclude_tags=None,
        include_paths=None,
        exclude_paths=["/bar"],
    )
    caller = OpenAPIToolCaller([spec_obj])
    tool_names = set(caller.tools.keys())
    assert not any("getFoo" in name for name in tool_names)
    assert not any("postBar" in name for name in tool_names)
    assert any("getBaz" in name for name in tool_names)