import json

from mcp.types import Tool

from src.example_generator import generate_example_from_schema
from src.utils.openapi_utils import _extract_example_text, _resolve_ref


def generate_tool_from_operation(
    spec: dict, path: str, method: str, prefix: str = None
) -> Tool:
    """
    Generate a Tool dict for a single OpenAPI operation using a dict spec (from prance).

    Args:
        spec: The OpenAPI spec as a dict (from prance).
        path: The endpoint path (e.g., "/v2-preview/reporting/messages/metakeys").
        method: The HTTP method (e.g., "post").

    Returns:
        A Tool object with the following fields:
        - name: A unique identifier for the tool.
        - description: Human-readable description.
        - inputSchema: JSON Schema for the tool's parameters.
    """
    # Get the operation object
    paths = spec.get("paths", {})
    path_item = paths.get(path)
    if not path_item:
        raise ValueError(f"Path '{path}' not found in OpenAPI spec.")
    operation = path_item.get(method.lower())
    if not operation:
        raise ValueError(f"Method '{method}' not found for path '{path}' in OpenAPI spec.")

    # Tool name: use operationId if available, else fallback to method+path
    name = operation.get("operationId") or f"{method}_{path}".replace("/", "_").strip("_")
    if prefix:
        name = f"{prefix}:{name}"

    # Description
    description = operation.get("description") or operation.get("summary") or ""

    # Collect parameters (query, path, header)
    properties = {}
    required = []

    # Extract parameters from the operation
    extract_parameters(spec, operation, properties, required)

    # Collect requestBody (JSON only)
    extract_body(spec, operation, properties, required)

    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    return Tool(
        name=name,
        description=description,
        inputSchema=input_schema
    ) 

def extract_body(spec, operation, properties, required):
    request_body = operation.get("requestBody")
    if request_body:
        content = request_body.get("content", {})
        # app_json = content.get("application/json")
        first_media_type, first_schema = next(iter(content.items()))

        example = None
        if "example" in first_schema:
            example = json.dumps(first_schema.get("example", "{}"))

        if first_schema:
            properties["body"] = first_schema

            if "description" not in properties["body"]:
                properties["body"]["description"] = ""

            properties["body"]["description"] += f" Body Content-Type: {first_media_type}"
            properties["body"]["description"] += " Example: " + example if example else ""

            required.append("body")


def extract_parameters(spec, operation, properties, required):
    """
    Extract parameters from an OpenAPI operation and update the properties and required lists.

    Args:
        spec: The OpenAPI specification dictionary.
        operation: The operation object from the OpenAPI spec.
        properties: The dictionary to update with parameter properties.
        required: The list to update with required parameter names.
    """
    for param in operation.get("parameters", []):
        param_name = param["name"]
        schema = param.get("schema", {})
        # Handle $ref in parameter schema
        if "$ref" in schema:
            ref_schema = _resolve_ref(spec, schema["$ref"])
            prop = {
                "type": ref_schema.get("type", "string"),
                "title": param_name
            }
            # Description extraction
            desc = ref_schema.get("description", "")
            # Enum handling
            if "enum" in ref_schema:
                enum_vals = ref_schema["enum"]
                desc = (desc or "") + f" Possible values: {enum_vals}"
            # Example handling
            example_text = _extract_example_text(ref_schema)
            if not example_text:
                # Generate example if none present
                generated_example = generate_example_from_schema(spec, ref_schema)
                example_text = f" Example: {generated_example}"
            if example_text:
                desc = (desc or "") + example_text
            if desc:
                prop["description"] = desc
            properties[param_name] = prop
        else:
            prop = {
                "type": schema.get("type", "string")
            }
            # Description extraction
            desc = ""
            if "description" in schema:
                desc = schema["description"]
            elif "description" in param:
                desc = param["description"]
            # Enum handling
            if "enum" in schema:
                enum_vals = schema["enum"]
                desc = (desc or "") + f" Possible values: {enum_vals}"
            if desc:
                prop["description"] = desc
            properties[param_name] = prop
        if param.get("required"):
            required.append(param_name)
