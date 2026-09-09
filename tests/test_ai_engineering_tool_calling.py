from types import SimpleNamespace
from unittest.mock import Mock

from ai_engineering.llm.tool_calling import ToolCallingAgent
from ai_engineering.schemas.audit import AuditEventType


class FakeCompletions:
    def __init__(self, message):
        self.message = message

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=self.message)])


def make_tool_call(arguments: str = "{}"):
    return SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="broken_tool", arguments=arguments),
    )


def test_unexpected_tool_exception_is_returned_as_structured_failure(monkeypatch):
    first_message = SimpleNamespace(
        content="",
        tool_calls=[make_tool_call()],
    )
    final_message = SimpleNamespace(content="Tool failed safely", tool_calls=[])
    client = Mock()
    client.chat.completions = FakeCompletions(first_message)
    client.chat.completions.create = Mock(side_effect=[
        SimpleNamespace(choices=[SimpleNamespace(message=first_message)]),
        SimpleNamespace(choices=[SimpleNamespace(message=final_message)]),
    ])

    registry = Mock()
    registry.definitions.return_value = []
    registry.execute.side_effect = RuntimeError("backend exploded")
    audit = Mock()
    audit.new_trace_id.return_value = "trace-123"

    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: client)

    agent = ToolCallingAgent(
        provider=SimpleNamespace(base_url="http://llm", api_key="test", model="test-model"),
        registry=registry,
        audit_service=audit,
    )
    result = agent.run("Inspect the system")

    assert result["status"] == "completed"
    assert result["trace_id"] == "trace-123"
    registry.execute.assert_called_once_with("broken_tool", {})

    tool_result_calls = [
        call for call in audit.record.call_args_list
        if call.args and call.args[0] == AuditEventType.TOOL_RESULT
    ]
    assert len(tool_result_calls) == 1
    assert tool_result_calls[0].kwargs["status"] == "failed"
    assert tool_result_calls[0].kwargs["payload"]["result"]["error"] == "Tool execution failed"
    assert tool_result_calls[0].kwargs["payload"]["result"]["error_type"] == "RuntimeError"
    assert tool_result_calls[0].kwargs["error"] == "backend exploded"


def test_invalid_tool_json_is_audited_as_failure(monkeypatch):
    first_message = SimpleNamespace(
        content="",
        tool_calls=[make_tool_call("{invalid")],
    )
    final_message = SimpleNamespace(content="Recovered", tool_calls=[])
    client = Mock()
    client.chat.completions.create = Mock(side_effect=[
        SimpleNamespace(choices=[SimpleNamespace(message=first_message)]),
        SimpleNamespace(choices=[SimpleNamespace(message=final_message)]),
    ])

    registry = Mock()
    registry.definitions.return_value = []
    audit = Mock()
    audit.new_trace_id.return_value = "trace-456"

    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: client)

    result = ToolCallingAgent(
        provider=SimpleNamespace(base_url="http://llm", api_key="test", model="test-model"),
        registry=registry,
        audit_service=audit,
    ).run("Inspect the system")

    assert result["status"] == "completed"
    registry.execute.assert_not_called()
    tool_result_calls = [
        call for call in audit.record.call_args_list
        if call.args and call.args[0] == AuditEventType.TOOL_RESULT
    ]
    assert tool_result_calls[0].kwargs["status"] == "failed"
    assert "Invalid JSON tool arguments" == tool_result_calls[0].kwargs["payload"]["result"]["error"]
