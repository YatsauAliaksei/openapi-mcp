from prance import ResolvingParser

from src.utils.logging_utils import setup_logging

logger = setup_logging("openapi_loader")

def load_openapi_spec(openapi_spec_path: str = "openapi.json") -> dict:
    """
    Load an OpenAPI spec from a local file or a URL (supports JSON and YAML).
    - If openapi_spec_path is a URL (https only), download and parse using prance (supports YAML/JSON).
    - If openapi_spec_path is a file path, read and parse using prance (supports YAML/JSON).
    - If openapi_spec_path is None or file does not exist, fallback to
      'openapi.json', 'openapi.yaml', 'openapi.yml' in the project root.
    - Raises RuntimeError if neither is available or if the file/URL is invalid.
    Returns:
        dict: The loaded OpenAPI spec.
    """

    logger.info(f"Attempting to load OpenAPI spec from: {openapi_spec_path}")

    parser = ResolvingParser(openapi_spec_path)

    logger.info(f"Successfully loaded OpenAPI spec from: {openapi_spec_path}")
    return parser.specification