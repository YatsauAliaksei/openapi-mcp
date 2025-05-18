"""
OpenAPI MCP Server

Configuration options:
1. config.yaml (default): Place a config.yaml in the project root, or set OPENAPI_MCP_CONFIG to its path.
2. Environment variables (if no config file is present):
    - OPENAPI_SPEC_PATH: Path or URL to the OpenAPI spec (required)
    - OPENAPI_BASE_URL: Base URL for the API (required)
    - OPENAPI_AUTH_TYPE: "Bearer" or "Basic" (optional)
    - OPENAPI_BEARER_TOKEN: Bearer token (if using Bearer auth)
    - OPENAPI_BASIC_KEY: Basic auth key/username (if using Basic auth)
    - OPENAPI_BASIC_SECRET: Basic auth secret/password (if using Basic auth)
    - OPENAPI_SERVICE_NAME: Service name/prefix (optional, default: "default")
"""

import asyncio
import json
from typing import Sequence

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from src.tool_caller import OpenAPIToolCaller
from src.utils.config import config
from src.utils.logging_utils import setup_logging

# --- Logging Configuration ---
logger = setup_logging("openapi_server")

# --- MCP Server Setup ---
server = Server("openapi-server")

# Configure OpenAPI Tool Caller (multi-spec, per-spec base URL, filename/tag filtering)
# Use per-spec include/exclude tags/paths from config.openapi_specs
tool_caller = OpenAPIToolCaller(
    config.openapi_specs
)

if not tool_caller.tools:
    raise RuntimeError(
        "No OpenAPI specs loaded. "
        "Please provide a config.yaml or set the required environment variables:\n"
        "  - OPENAPI_SPEC_PATH (required)\n"
        "  - OPENAPI_BASE_URL (required)\n"
        "  - OPENAPI_AUTH_TYPE (optional: Bearer or Basic)\n"
        "  - OPENAPI_BEARER_TOKEN (if Bearer)\n"
        "  - OPENAPI_BASIC_KEY and OPENAPI_BASIC_SECRET (if Basic)\n"
        "  - OPENAPI_SERVICE_NAME (optional, default: 'default')"
    )

# Log all tags present in the loaded tools after applying filter
loaded_tools = tool_caller.list_tools()
all_tags = set()
for tool in loaded_tools:
    # Try to get tags from the OpenAPI spec for this tool
    # We need to map tool.name back to the operation in the spec
    # We'll use the tool_caller.spec and tool_caller.registry for this
    meta = tool_caller.registry.get(tool.name)
    if meta:
        # Find the operation in the spec
        spec = tool_caller.tool_specs.get(tool.name)
        path_item = spec.get("paths", {}).get(meta.path, {}) if spec else {}
        operation = path_item.get(meta.method.lower())
        if operation:
            for tag in operation.get("tags", []):
                all_tags.add(tag)
if all_tags:
    logger.info(f"Loaded tools with tags: {sorted(all_tags)}")
else:
    logger.info("No tags found in loaded tools.")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    List all available tools provided by the OpenAPI Tool Caller.

    Returns:
        A list of Tool objects.
    """
    return tool_caller.list_tools()

@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Call a tool by name with the provided arguments.

    Args:
        name: The name of the tool to call.
        arguments: A dictionary of arguments to pass to the tool.

    Returns:
        A sequence of content objects (text, image, or embedded resource) as the tool's response.
    """
    try:
        result = tool_caller.call_tool(name, arguments)
        return [
            types.TextContent(type="text", text=json.dumps(result, indent=2))
        ]
    except Exception as e:
        logger.error("Exception in call_tool", exc_info=True)
        error_response = {
            "error": {
                "type": type(e).__name__,
                "message": str(e)
            }
        }
        return [
            types.TextContent(
                type="text",
                text=json.dumps(error_response)
            )
        ]

async def main():
    """
    Entry point for running the MCP server using stdio.

    This function sets up the stdio server and starts the main event loop.
    """
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())