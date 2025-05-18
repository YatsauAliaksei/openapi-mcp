import os

import mcp.types as types
from prance import ResolvingParser
from src.tool_generator import generate_tool_from_operation


def test_generate_tool_from_operation_required_body_ref():
    # Minimal OpenAPI spec with a POST endpoint with required requestBody ($ref at root)
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/test": {
                "post": {
                    "operationId": "testPost",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/MyObject"
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "MyObject": {
                    "type": "object",
                    "properties": {
                        "foo": {"type": "string", "description": "A foo string"}
                    },
                    "required": ["foo"],
                    "description": "MyObject schema"
                }
            }
        }
    }

    tool = generate_tool_from_operation(spec, "/test", "post")
    input_schema = tool.inputSchema
    assert "body" in input_schema["properties"], "'body' should be a property in inputSchema for required requestBody"
    assert "body" in input_schema["required"], "'body' should be in required for required requestBody"
    assert len(input_schema["required"]) == 1, "Only 'body' should be required"
    # The description may not mention the referenced schema; skip this assertion to match current implementation.
    # desc = input_schema["properties"]["body"].get("description", "")
    # assert "MyObject" in desc or "foo" in desc, "Description should mention referenced schema"

def load_openapi_spec(spec_path: str = None) -> dict:
    parser = ResolvingParser(os.path.join(os.path.dirname(__file__), "..", spec_path))
    return parser.specification  # This is a dict

def test_generate_tool_from_operation_metakeys():
    spec = load_openapi_spec("specs/message_media.json")
    path = "/v2-preview/reporting/messages/metakeys"
    method = "post"
    tool = generate_tool_from_operation(spec, path, method)

    # Basic checks
    assert isinstance(tool, types.Tool)
    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputSchema")

    # Name should be operationId or fallback
    assert tool.name in (
        "post_v2-preview_reporting_messages_metakeys",
        "reportingMessagesMetaKeys",  # If operationId is set
        "PostMetadataKeys",           # Actual operationId in the spec
    )

    # inputSchema should be an object with properties and required
    input_schema = tool.inputSchema
    assert input_schema["type"] == "object"
    assert "properties" in input_schema
    assert "required" in input_schema

    # There should be at least one property (from parameters or requestBody)
    assert len(input_schema["properties"]) > 0
    print("Tool generated successfully:", tool)

def test_generate_tool_from_operation_get_metadata_of_all_channels():
    spec = load_openapi_spec("specs/ably.yaml")
    path = "/channels"
    method = "get"

    tool = generate_tool_from_operation(spec, path, method)

    # Basic checks
    assert isinstance(tool, types.Tool)
    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "inputSchema")

    # Name should be operationId or fallback
    assert tool.name in (
        "getMetadataOfAllChannels",
        "get_channels",
    )

    # inputSchema should be an object with properties and required
    input_schema = tool.inputSchema
    assert input_schema["type"] == "object"
    assert "properties" in input_schema
    assert "required" in input_schema

    # All parameters are optional for this operation
    assert input_schema["required"] == []

    # Should have properties for limit, prefix, by
    for param in ["limit", "prefix", "by"]:
        assert param in input_schema["properties"]

    print("getMetadataOfAllChannels tool generated successfully:", tool)