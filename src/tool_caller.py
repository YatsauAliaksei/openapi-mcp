import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import requests
from mcp.types import Tool

from src.tool_generator import generate_tool_from_operation
from src.utils.auth import get_auth_header
from src.utils.config import OpenAPISpec
from src.utils.logging_utils import setup_logging
from src.utils.openapi_loader import load_openapi_spec


@dataclass
class OperationMeta:
    def __init__(
        self,
        method: str,
        path: str,
        param_locations: Dict[str, str],  # param_name -> location (path, query, header, body)
        required: list,  # list of required parameter names
        content_media_type: str,
        auth_type: str,
        service_name: str
    ):
        """
        Initialize OperationMeta with HTTP method, path, parameter locations, and required parameters.

        Args:
            method: HTTP method (e.g., "GET", "POST").
            path: API endpoint path.
            param_locations: Mapping of parameter names to their locations.
            required: List of required parameter names.
        """
        self.method = method
        self.path = path
        self.param_locations = param_locations
        self.required = required
        self.conten_media_type = content_media_type
        self.auth_type = auth_type
        self.service_name=service_name

    def __repr__(self):
        """
        Return a string representation of the OperationMeta instance.
        """
        return (
            f"OperationMeta("
            f"method={self.method!r}, "
            f"path={self.path!r}, "
            f"param_locations={self.param_locations!r}, "
            f"required={self.required!r})"
            f"content_media_type={self.conten_media_type!r})"
            f"auth_type={self.auth_type!r})"
            f"service_name={self.service_name!r})"
        )

logger = setup_logging("openapi_tool_caller")
setup_logging("urllib3", level=logging.DEBUG)


class OpenAPIToolCaller:
    def __init__(
        self,
        openapi_specs: List[OpenAPISpec],
    ):
        """
        :param openapi_specs: List of OpenAPISpec objects.
        """
        logger.debug(f"Initializing OpenAPIToolCaller with OpenAPI specs. {openapi_specs}")

        self.tools: Dict[str, Tool] = {}
        self.registry: Dict[str, OperationMeta] = {}
        self.tool_base_urls: Dict[str, str] = {}
        self.tool_specs: Dict[str, dict] = {}

        for spec_obj in openapi_specs:
            service_name = spec_obj.service_name
            spec_path = spec_obj.file_location
            prefix = spec_obj.prefix
            auth_type = spec_obj.auth_type

            # New: per-spec filters
            include_tags = getattr(spec_obj, "include_tags", None)
            exclude_tags = getattr(spec_obj, "exclude_tags", None)
            include_paths = getattr(spec_obj, "include_paths", None)
            exclude_paths = getattr(spec_obj, "exclude_paths", None)

            # Load spec
            try:
                spec = load_openapi_spec(spec_path)
            except Exception:
                logger.error(
                    f"Failed to load OpenAPI spec from {spec_path} (service: {service_name}). Skipping.",
                    exc_info=True,
                )
                continue

            # Get base_url from the spec (if present)
            # Prefer base_url from spec_obj if present
            base_url = getattr(spec_obj, "base_url", None)
            if not base_url:
                # Fallback: try to get from config.yaml via service_name
                from src.utils.config import config
                base_url = config.get_openapi_base_url(service_name)
            if not base_url:
                logger.warning(f"No base URL found for spec '{service_name}', skipping.")
                continue

            # Count tools before adding
            tools_before = len(self.tools)

            # Build tools and registry for this spec
            self._add_tools_from_spec(
                spec, prefix, base_url, service_name, auth_type,
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
            )

            # Count tools after adding
            tools_after = len(self.tools)
            tools_added = tools_after - tools_before
            logger.info(f"Loaded {tools_added} tools from spec file '{spec_path}' (service: {service_name}).")
        
        logger.info(f"Loaded {len(self.tools)} tools from all OpenAPI specs.")
        logger.debug(f"Loaded tools: {list(self.tools.keys())}")

    def _add_tools_from_spec(
        self, spec, filename_prefix: str, base_url: str, service_name: str, auth_type: str,
        include_tags: list = None,
        exclude_tags: list = None,
        include_paths: list = None,
        exclude_paths: list = None,
    ):
        """
        Add tools and registry entries from a single OpenAPI spec, with tool name prefixing and filtering.
        """
        import fnmatch

        def match_any(val_list, patterns):
            if not patterns or not val_list:
                return False
            for pat in patterns:
                for val in val_list:
                    if fnmatch.fnmatch(val, pat):
                        return True
            return False

        def match_path(path, patterns):
            if not patterns:
                return False
            for pat in patterns:
                if fnmatch.fnmatch(path, pat):
                    return True
            return False

        paths = spec.get("paths", {})
        for path, path_item in paths.items():
            for method in path_item:
                if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    continue
                operation = path_item[method]
                op_tags = operation.get("tags", [])

                # --- Filtering logic ---
                # 1. Include paths (if set, only allow if matches)
                if include_paths and not match_path(path, include_paths):
                    continue
                # 2. Exclude paths (if set, skip if matches)
                if exclude_paths and match_path(path, exclude_paths):
                    continue
                # 3. Include tags (if set, only allow if any tag matches)
                if include_tags and not match_any(op_tags, include_tags):
                    continue
                # 4. Exclude tags (if set, skip if any tag matches)
                if exclude_tags and match_any(op_tags, exclude_tags):
                    continue

                try:
                    tool = generate_tool_from_operation(spec, path, method, prefix=filename_prefix)
                except Exception:
                    logger.exception(f"Failed to generate tool for {method} {path} in {filename_prefix}. Skipping.")
                    continue  # skip invalid operations

                # Map parameter locations
                param_locations = {}
                for param in operation.get("parameters", []):
                    pname = param["name"]
                    loc = param.get("in", "query")
                    param_locations[pname] = loc
                
                content_media_type = "application/json"  # Default content type
                # Handle requestBody (JSON only)
                if "requestBody" in operation:
                    param_locations["body"] = "body"
                    content = operation["requestBody"].get("content", {})
                    # setting content_media_type to the first available content type
                    content_media_type = next(iter(content))

                self.tools[tool.name] = tool
                self.registry[tool.name] = OperationMeta(
                    method=method.upper(),
                    path=path,
                    param_locations=param_locations,
                    required=tool.inputSchema.get("required", []),
                    content_media_type=content_media_type,
                    auth_type=auth_type,
                    service_name=service_name
                )
                self.tool_base_urls[tool.name] = base_url
                self.tool_specs[tool.name] = spec

    def list_tools(self) -> List[Tool]:
        """
        Return a list of all loaded Tool objects.

        Returns:
            List of Tool objects.
        """
        return list(self.tools.values())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool by name with the provided arguments.

        Args:
            tool_name: The name of the tool to call.
            arguments: Dictionary of arguments to pass to the tool.

        Returns:
            The result of the tool call, typically a parsed JSON response.

        Raises:
            ValueError: If the tool name is unknown or required arguments are missing.
            requests.HTTPError: If the HTTP request fails.
        """
        if tool_name not in self.tools or tool_name not in self.registry:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        meta = self.registry[tool_name]
        # spec = self.tool_specs[tool_name]  # Removed unused variable to fix F841

        logger.info(f"Calling tool: {tool_name}")
        logger.debug("Arguments: (arguments)")
        logger.debug(f"Tool: {tool}")
        logger.debug(f"Meta: {repr(meta)}")

        # Validate required arguments
        required = tool.inputSchema.get("required", [])
        for req in required:
            if req not in arguments:
                raise ValueError(f"Missing required argument: {req}")

        # Prepare request
        base_url = self.tool_base_urls.get(tool_name)
        if not base_url:
            raise ValueError(f"No base URL found for tool: {tool_name}")
        url = base_url.rstrip("/") + meta.path
        path_params = {}
        query_params = {}
        headers = {}
        req_body = {}

        for pname, value in arguments.items():
            loc = meta.param_locations.get(pname, "query")
            if loc == "path":
                path_params[pname] = value
            elif loc == "query":
                query_params[pname] = value
            elif loc == "header":
                headers[pname] = value
            elif loc == "body":
                req_body[pname] = value

        # If "body" is present in arguments, unwrap it and use its value as the JSON body
        if "body" in arguments:
            req_body = arguments["body"]
        # Substitute path parameters
        for pname, value in path_params.items():
            url = url.replace("{" + pname + "}", str(value))

        req_headers = self.create_headers(meta, headers)

        # Optionally log the full HTTP request before sending (using logger)
        # todo: remove this
        log(meta, url, query_params, req_body, req_headers)

        # Make HTTP request based on content type
        content_type = meta.conten_media_type.lower() or "application/json"
        request_kwargs = {
            "method": meta.method,
            "url": url,
            "params": query_params if query_params else None,
            "headers": req_headers,
        }

        files = []
        if content_type == "application/json":
            request_kwargs["json"] = req_body if req_body else None
        elif content_type == "application/x-www-form-urlencoded":
            request_kwargs["data"] = req_body if req_body else None
        elif content_type == "multipart/form-data":
            # attachments: list of file paths or a single file path
            attachments = req_body.get("attachment")
            if not attachments:
                request_kwargs["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
                request_kwargs["data"] = req_body if req_body else None
            else:
                if not isinstance(attachments, list):
                    attachments = [attachments]

                import os
                for file_path in attachments:
                    if not isinstance(file_path, str):
                        raise ValueError(f"Attachment path must be a string, got {type(file_path)}")
                    # Use absolute path as-is, resolve relative path to cwd
                    resolved_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
                    # Try to guess content type, fallback to octet-stream
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(os.path.basename(resolved_path))
                    mime_type = mime_type or "application/octet-stream"
                    try:
                        file_obj = open(resolved_path, "rb")
                    except Exception as e:
                        raise ValueError(f"Failed to open attachment file: {resolved_path}") from e
                    files.append(("attachment", (os.path.basename(resolved_path), file_obj, mime_type)))
    
                # Remove 'attachment' from req_body for form fields
                # Replace any '\\n' with '\n' in string fields for correct newlines in email/text
                form_fields = {}
                for k, v in req_body.items():
                    if k == "attachment":
                        continue
                    if isinstance(v, str):
                        form_fields[k] = v.replace("\\n", "\n")
                    else:
                        form_fields[k] = v

                request_kwargs["files"] = files
                request_kwargs["data"] = form_fields if form_fields else None
    
                # Remove Content-Type header so requests can set it with the correct boundary
                if "Content-Type" in request_kwargs["headers"]:
                    del request_kwargs["headers"]["Content-Type"]
    
        # Ensure file handles are closed after the request
        try:
            s = requests.Session()
            req = requests.Request(**request_kwargs)
            prepped = s.prepare_request(req)
            logger.info(f"==== Request Headers: {prepped.headers}")
            logger.info(f"==== Request Body: {prepped.body}")
            resp = s.send(prepped)
        finally:
            for _, (filename, file_obj, mime_type) in files:
                file_obj.close()
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text

    def create_headers(self, meta: OperationMeta, headers):
        auth_header = get_auth_header(meta.auth_type, meta.service_name)
        # Merge with any user-supplied headers (user headers take precedence)
        content_type_header = {"Content-Type": meta.conten_media_type}
            
        headers = {**headers, **content_type_header}
        merged_headers = {**auth_header, **headers} if headers else auth_header
        return merged_headers

@staticmethod
def log(meta, url, query_params, request_body, merged_headers):
    """
    Log the details of an HTTP request if logging is enabled.

    Args:
        meta: OperationMeta instance describing the operation.
        url: The request URL.
        query_params: Query parameters dictionary.
        body: body dictionary.
        merged_headers: Headers dictionary.
    """
    # Skip logging if not enabled
    if logger.level > logging.DEBUG:
        return

    # Log the full HTTP request
    log_lines = [
        "[openapi_tool_caller] --- HTTP REQUEST ---",
        f"Method: {meta.method}",
        f"URL: {url}",
    ]
    if query_params:
        log_lines.append(f"Query Params: {json.dumps(query_params, indent=2)}")
    log_lines.append(f"Headers: {json.dumps(merged_headers, indent=2)}")
    if request_body:
        # log_lines.append(f"Body: {json.dumps(json_body, indent=2)}")
        log_lines.append(f"Body: {request_body}")
    log_lines.append("[openapi_tool_caller] ---------------------")

    logger.info("\n".join(log_lines))