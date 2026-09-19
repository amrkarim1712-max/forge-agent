from forge_agent.models.base import ModelResponse, ToolCall


def test_tool_call_is_structured():
    response = ModelResponse(content="", tool_calls=[ToolCall("1", "read_file", {"path": "README.md"})])
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments["path"] == "README.md"