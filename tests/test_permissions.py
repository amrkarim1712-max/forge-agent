from forge_agent.permissions import Decision, PermissionManager


def test_tool_permissions_are_conservative():
    manager = PermissionManager()
    assert manager.classify_tool("read_file") == Decision.SAFE
    assert manager.classify_tool("write_file") == Decision.REVIEW
    assert manager.classify_tool("not_a_tool") == Decision.BLOCKED