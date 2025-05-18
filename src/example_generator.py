from typing import Any

from src.utils.openapi_utils import _resolve_ref


def generate_example_from_schema(spec: dict, schema: dict) -> Any:
    """
    Recursively generate an example object for a given schema.
    Uses 'example', 'default', or 'enum' if present, otherwise generates a plausible value.
    Appends a list of all required params for the body at the end (under key '__required_params__' if top-level object).
    """
    # Handle $ref at the root
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])

    # Use explicit example if present
    if "example" in schema:
        return schema["example"]
    # Use first example from 'examples' if present
    if "examples" in schema and isinstance(schema["examples"], dict):
        for ex in schema["examples"].values():
            if isinstance(ex, dict) and "value" in ex:
                return ex["value"]
            elif isinstance(ex, str):
                return ex
    # Use default if present
    if "default" in schema:
        return schema["default"]
    # Use first enum value if present
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]

    # Handle type-specific logic
    typ = schema.get("type")
    if typ == "object":
        props = schema.get("properties", {})
        example_obj = {}
        for prop_name, prop_schema in props.items():
            example_obj[prop_name] = generate_example_from_schema(spec, prop_schema)
        return example_obj
    elif typ == "array":
        items_schema = schema.get("items", {})
        return [generate_example_from_schema(spec, items_schema)]
    elif typ == "string":
        fmt = schema.get("format")
        if fmt == "date-time":
            return "2023-01-01T00:00:00Z"
        elif fmt == "date":
            return "2023-01-01"
        elif fmt == "uuid":
            return "123e4567-e89b-12d3-a456-426614174000"
        elif fmt == "email":
            return "user@example.com"
        return "string"
    elif typ == "integer":
        return 0
    elif typ == "number":
        return 0.0
    elif typ == "boolean":
        return True
    # Fallback
    return "example"
