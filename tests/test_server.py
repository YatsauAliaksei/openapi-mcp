from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import src.server as server


@pytest.mark.asyncio
async def test_list_tools_returns_tools():
    fake_tools = ["tool1", "tool2"]
    with patch.object(server.tool_caller, "list_tools", return_value=fake_tools):
        result = await server.list_tools()
        assert result == fake_tools

@pytest.mark.asyncio
async def test_call_tool_success():
    fake_result = [{"type": "text", "text": "ok"}]
    with patch.object(server.tool_caller, "call_tool", return_value={"foo": "bar"}):
        with patch("src.server.types.TextContent") as MockTextContent:
            MockTextContent.return_value = fake_result[0]
            result = await server.call_tool("toolname", {"arg": 1})
            assert result == fake_result

@pytest.mark.asyncio
async def test_call_tool_exception():
    with patch.object(server.tool_caller, "call_tool", side_effect=Exception("fail")):
        with patch("src.server.types.TextContent") as MockTextContent:
            MockTextContent.return_value = {
                "type": "text",
                "text": '{"error": {"type": "Exception", "message": "fail"}}',
            }
            result = await server.call_tool("toolname", {"arg": 1})
            assert isinstance(result, list)
            assert "error" in result[0]["text"]
@pytest.mark.asyncio
async def test_main_runs(monkeypatch):
    # Patch stdio_server to yield dummy streams using a real async context manager
    dummy_stream = MagicMock()
    class DummyCM:
        async def __aenter__(self):
            return (dummy_stream, dummy_stream)
        async def __aexit__(self, exc_type, exc, tb):
            return False
    monkeypatch.setattr(server, "stdio_server", lambda: DummyCM())

    # Patch server.run to a coroutine that does nothing
    monkeypatch.setattr(server.server, "run", AsyncMock())

    # Should not raise
    await server.main()