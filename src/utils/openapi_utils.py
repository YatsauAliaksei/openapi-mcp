def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref string in the OpenAPI spec and return the referenced schema dict."""
    if not ref.startswith("#/"):
        raise ValueError(f"Only local refs are supported, got: {ref}")
    parts = ref.lstrip("#/").split("/")
    obj = spec
    for part in parts:
        obj = obj[part]
    return obj

def _extract_example_text(schema: dict) -> str:
    """Return a string with the example if present, else empty string."""
    if "example" in schema:
        return f" Example: {schema['example']}"
    elif "examples" in schema and isinstance(schema["examples"], dict):
        # Use the first example if available
        for ex in schema["examples"].values():
            if isinstance(ex, dict) and "value" in ex:
                return f" Example: {ex['value']}"
            elif isinstance(ex, str):
                return f" Example: {ex}"
    return ""