import json
import os

import pytest
from src.example_generator import generate_example_from_schema


def load_openapi_spec():
    # Load the real openapi.json from the specs directory
    here = os.path.dirname(__file__)
    openapi_path = os.path.abspath(os.path.join(here, "..", "specs", "message_media.json"))
    with open(openapi_path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_first_schema_with_properties(spec):
    # Find a schema in components.schemas with properties
    schemas = spec.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        if schema.get("type") == "object" and "properties" in schema:
            return name, schema
    return None, None

def test_generate_example_from_real_schema():
    spec = load_openapi_spec()
    name, schema = find_first_schema_with_properties(spec)
    if not schema:
        pytest.skip("No object schema with properties found in openapi.json")
    example = generate_example_from_schema(spec, {"$ref": f"#/components/schemas/{name}"})
    assert isinstance(example, dict)
    # At least one property should be present
    assert example, f"Example for {name} should not be empty"
    # Only check for __required_params__ if the example is a plain object (not a paginated/list wrapper)
    # Heuristic: if the example has more than one key or has __required_params__, check for it
    if (
        "__required_params__" in example
        or (
            len(example) > 1
            and not any(isinstance(v, list) for v in example.values())
        )
    ):
        assert "__required_params__" in example, (
            f"Example for {name} should include '__required_params__'"
        )
        assert isinstance(
            example["__required_params__"], list
        ), "__required_params__ should be a list"
    print(f"Example for {name}:", example)

def test_generate_example_from_primitive_schema():
    spec = load_openapi_spec()
    schemas = spec.get("components", {}).get("schemas", {})
    for name, schema in schemas.items():
        if schema.get("type") in ("string", "integer", "number", "boolean"):
            _example = generate_example_from_schema(spec, {"$ref": f"#/components/schemas/{name}"})
