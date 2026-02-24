"""
Tests for E1.S2: SessionTracer Middleware (shared/patterns/evaluation/session_tracer.py)
"""

import pytest

from homeiq_patterns.evaluation.models import SessionTrace, ToolCall
from homeiq_patterns.evaluation.session_tracer import (
    CallbackSink,
    InMemorySink,
    SessionTracerContext,
    TraceSink,
    get_tracer_context,
    trace_session,
)


# ---------------------------------------------------------------------------
# Tests: SessionTracerContext
# ---------------------------------------------------------------------------


class TestSessionTracerContext:
    def test_create(self):
        ctx = SessionTracerContext(agent_name="test-agent")
        assert ctx.trace.agent_name == "test-agent"
        assert ctx.trace.user_messages == []
        assert ctx.trace.tool_calls == []

    def test_record_user_message(self):
        ctx = SessionTracerContext(agent_name="test")
        ctx.record_user_message("hello")
        assert len(ctx.trace.user_messages) == 1
        assert ctx.trace.user_messages[0].content == "hello"
        assert ctx.trace.user_messages[0].turn_index == 0

    def test_record_multiple_user_messages(self):
        ctx = SessionTracerContext(agent_name="test")
        ctx.record_user_message("msg1")
        ctx.record_user_message("msg2")
        assert len(ctx.trace.user_messages) == 2

    def test_record_agent_response(self):
        ctx = SessionTracerContext(agent_name="test")
        ctx.record_agent_response("I did the thing.")
        assert len(ctx.trace.agent_responses) == 1
        assert ctx.trace.agent_responses[0].content == "I did the thing."

    def test_record_agent_response_increments_turn(self):
        ctx = SessionTracerContext(agent_name="test")
        ctx.record_agent_response("resp1")
        ctx.record_agent_response("resp2")
        assert ctx.trace.agent_responses[0].turn_index == 0
        assert ctx.trace.agent_responses[1].turn_index == 1

    def test_record_tool_call(self):
        ctx = SessionTracerContext(agent_name="test")
        tc = ctx.record_tool_call(
            tool_name="search",
            parameters={"q": "room"},
            result={"found": 3},
            latency_ms=42.5,
        )
        assert tc.tool_name == "search"
        assert tc.parameters["q"] == "room"
        assert tc.latency_ms == 42.5
        assert len(ctx.trace.tool_calls) == 1

    def test_tool_call_sequence_index_auto_increments(self):
        ctx = SessionTracerContext(agent_name="test")
        tc1 = ctx.record_tool_call(tool_name="search")
        tc2 = ctx.record_tool_call(tool_name="book")
        assert tc1.sequence_index == 0
        assert tc2.sequence_index == 1

    def test_record_response_with_tool_calls(self):
        ctx = SessionTracerContext(agent_name="test")
        tc = ToolCall(tool_name="search")
        ctx.record_agent_response("Results:", tool_calls_in_turn=[tc])
        assert len(ctx.trace.agent_responses[0].tool_calls_in_turn) == 1


# ---------------------------------------------------------------------------
# Tests: Sinks
# ---------------------------------------------------------------------------


class TestInMemorySink:
    @pytest.mark.asyncio
    async def test_emit(self):
        sink = InMemorySink()
        trace = SessionTrace(agent_name="test")
        await sink.emit(trace)
        assert len(sink.traces) == 1
        assert sink.traces[0].agent_name == "test"

    @pytest.mark.asyncio
    async def test_multiple_emits(self):
        sink = InMemorySink()
        await sink.emit(SessionTrace(agent_name="a"))
        await sink.emit(SessionTrace(agent_name="b"))
        assert len(sink.traces) == 2


class TestCallbackSink:
    @pytest.mark.asyncio
    async def test_sync_callback(self):
        captured = []
        sink = CallbackSink(lambda t: captured.append(t))
        await sink.emit(SessionTrace(agent_name="cb-test"))
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_async_callback(self):
        captured = []

        async def cb(t):
            captured.append(t)

        sink = CallbackSink(cb)
        await sink.emit(SessionTrace(agent_name="async-test"))
        assert len(captured) == 1


# ---------------------------------------------------------------------------
# Tests: @trace_session decorator
# ---------------------------------------------------------------------------


class TestTraceSessionDecorator:
    @pytest.mark.asyncio
    async def test_basic_decorated_function(self):
        sink = InMemorySink()

        @trace_session(agent_name="test-agent", sink=sink, model="gpt-4o")
        async def handler():
            return {"response": "Done!"}

        result = await handler()
        assert result == {"response": "Done!"}
        assert len(sink.traces) == 1
        assert sink.traces[0].agent_name == "test-agent"
        assert sink.traces[0].model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_captures_latency(self):
        sink = InMemorySink()

        @trace_session(agent_name="latency-test", sink=sink)
        async def handler():
            return {}

        await handler()
        assert "total_latency_ms" in sink.traces[0].metadata
        assert sink.traces[0].metadata["total_latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_auto_captures_user_input_from_kwarg(self):
        sink = InMemorySink()

        @trace_session(agent_name="input-test", sink=sink)
        async def handler(request=None):
            return {"response": "ok"}

        await handler(request={"message": "hello world"})
        assert len(sink.traces[0].user_messages) == 1
        assert sink.traces[0].user_messages[0].content == "hello world"

    @pytest.mark.asyncio
    async def test_auto_captures_agent_output(self):
        sink = InMemorySink()

        @trace_session(agent_name="output-test", sink=sink)
        async def handler():
            return {"response": "Here are your results"}

        await handler()
        assert len(sink.traces[0].agent_responses) == 1
        assert "Here are your results" in sink.traces[0].agent_responses[0].content

    @pytest.mark.asyncio
    async def test_tracer_context_available_inside_handler(self):
        sink = InMemorySink()

        @trace_session(agent_name="ctx-test", sink=sink)
        async def handler():
            ctx = get_tracer_context()
            assert ctx is not None
            ctx.record_tool_call(tool_name="search", parameters={"q": "test"})
            return {"response": "done"}

        await handler()
        assert len(sink.traces[0].tool_calls) == 1
        assert sink.traces[0].tool_calls[0].tool_name == "search"

    @pytest.mark.asyncio
    async def test_tracer_context_none_outside_handler(self):
        ctx = get_tracer_context()
        assert ctx is None

    @pytest.mark.asyncio
    async def test_handler_exception_still_emits_trace(self):
        sink = InMemorySink()

        @trace_session(agent_name="error-test", sink=sink)
        async def handler():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await handler()

        assert len(sink.traces) == 1
        assert sink.traces[0].agent_name == "error-test"

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        sink = InMemorySink()

        @trace_session(agent_name="meta-test", sink=sink)
        async def my_handler():
            """My docstring."""
            return {}

        assert my_handler.__name__ == "my_handler"
        assert my_handler.__doc__ == "My docstring."
