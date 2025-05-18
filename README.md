# openapi-mcp

OpenAPI MCP Server that exposes any OpenAPI spec as a set of tools via the MCP protocol.

---

## Table of Contents

- [Overview](#overview)
- [Supported Content Types](#supported-content-types)
- [Requirements](#requirements)
- [Quickstart](#quickstart)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Using config.yaml (Recommended)](#using-configyaml-recommended)
  - [Using Environment Variables](#using-environment-variables)
  - [Example config.yaml](#example-configyaml)
- [Running the Server](#running-the-server)
  - [With Python](#with-python)
  - [With Environment Variables](#with-environment-variables)
  - [As an MCP Server (stdio)](#as-an-mcp-server-stdio)
  - [MCP Inspector](#mcp-inspector)
- [OpenAPI Spec Integration](#openapi-spec-integration)
- [Logging and Debugging](#logging-and-debugging)
- [Testing](#testing)
- [🤖 Agent Integration Example](#-agent-integration-example)
- [License](#license)
- [Configuration and Startup Flow (Diagram)](#configuration-and-startup-flow-diagram)

---

## Overview

This project allows you to expose any OpenAPI spec as a set of tools via the Model Context Protocol (MCP). It supports aggregation of multiple OpenAPI specs with different authentication, and filtering (tags/paths). The server is designed to be run as a subprocess (stdio) for integration with the MCP CLI or other orchestrators.

Supported formats:
- Supports OpenAPI spec 3.0

---

## Supported Content Types

This project currently supports the following request content types for API calls:

- `application/json`
- `application/x-www-form-urlencoded`
- `multipart/form-data`

---

## Requirements

- Python >= 3.12
- Dependencies listed in [`pyproject.toml`](pyproject.toml)

---

## Quickstart

```sh
python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
python -m src.server
```

---

## Installation

```sh
git clone https://github.com/yourusername/openapi-mcp.git
cd openapi-mcp
pip install .
```
Or, to install dependencies only:
```sh
pip install -r requirements.txt
```

---

## Configuration

### Using config.yaml (Recommended)

- Place a `config.yaml` in the project root, or set the `OPENAPI_MCP_CONFIG` environment variable to its path.
- Supports multiple OpenAPI specs, per-spec base URLs, authentication, and filtering (tags/paths).

### Using Environment Variables

If no config file is present, you can use environment variables to configure a single OpenAPI spec:

- `OPENAPI_SPEC_PATH`: Path or URL to the OpenAPI spec (required)
- `OPENAPI_BASE_URL`: Base URL for the API (required)
- `OPENAPI_AUTH_TYPE`: "Bearer" or "Basic" (optional)
- `OPENAPI_BEARER_TOKEN`: Bearer token (if using Bearer auth)
- `OPENAPI_BASIC_CLIENT_ID`: Basic auth client_id (if using Basic auth)
- `OPENAPI_BASIC_CLIENT_SECRET`: Basic auth client secret (if using Basic auth)
- `OPENAPI_SERVICE_NAME`: Service name/prefix (optional, default: "default")

### Example config.yaml

```yaml
openapi:
  ably:
    file_location: "specs/ably.yaml"
    base_url: "https://rest.ably.io"
    filter:
      include_tags: ["Status", "History"]
      exclude_tags: ["Publishing", "Authentication"]
      include_paths: ["/push/**"]
      exclude_paths: ["/push/deviceRegistrations"]
    authentication:
      auth_type: "Basic"
      client_id: "dummy_client_id"
      client_secret: "dummy_client_secret"
  slack:
    file_location: "specs/slack.json"
    base_url: "https://slack.com/api"
    authentication:
      auth_type: "Bearer"
      api_token: "dummy_key"
debug: false
log_file: "openapi_mcp.log"
```

---

## Running the Server

### With Python

```sh
python src/server.py
```
- By default, loads `config.yaml` from the project root.
- To specify a config file:
  ```sh
  OPENAPI_MCP_CONFIG=path/to/your_config.yaml python src/server.py
  ```

### With Environment Variables

```sh
OPENAPI_SPEC_PATH=specs/ably.yaml OPENAPI_BASE_URL=https://rest.ably.io python src/server.py
```
- Add authentication variables as needed.

### As an MCP Server (stdio)

- The server runs using stdio, designed to be launched by the MCP CLI or orchestrator.

### MCP Inspector

To inspect the MCP server, use:

```sh
mcp dev src/server.py
```

---

## OpenAPI Spec Integration

- Add new specs by editing `config.yaml`.
- Supports filtering by tags and paths.
- Supports Basic and Bearer authentication.

---

## Logging and Debugging

- Logging is configured via `log_file` in `config.yaml`.
- Set `debug: true` for more verbose output.

---

## Testing

Run tests with:

```sh
pytest
```

---

## 🤖 Agent Integration Example

To connect this MCP server to your Agent, configure your `mcp_settings.json` like this:

```json
{
  "mcpServers": {
    "sinch_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "path_to_project/openapi-mcp",
        "run",
        "src/server.py"
      ],
      "env": {
        "SMS_API_TOKEN": "SMS_API_TOKEN_HERE",
        "MAILGUN_API_KEY": "api",
        "MAILGUN_API_SECRET": "MAILGUN_API_SECRET_HERE",
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

---

## License

This project is licensed under the MIT License. See the [`LICENSE`](LICENSE) file for details.

MIT License (see [`LICENSE`](LICENSE)).

---
