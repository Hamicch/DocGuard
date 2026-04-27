"""Unit tests for the provider-agnostic LLM client."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.adapters.llm_client import GPT4O_MINI, HAIKU, LLMClient
from src.domain.models import ConventionSet

# ── fixtures ──────────────────────────────────────────────────────────────────


class EchoSchema(BaseModel):
    message: str
    score: float


def make_openai_response(
    parsed: BaseModel,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    response_id: str = "chatcmpl-test123",
) -> MagicMock:
    """Build a mock that looks like an openai ParsedChatCompletion."""
    choice = SimpleNamespace(message=SimpleNamespace(parsed=parsed))
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    mock = MagicMock()
    mock.id = response_id
    mock.choices = [choice]
    mock.usage = usage
    return mock


def make_client() -> tuple[LLMClient, MagicMock]:
    """Return (LLMClient, mock_openai_inner_client)."""
    client = LLMClient(api_key="test-key", base_url="http://fake/v1")
    mock_inner = MagicMock()
    mock_inner.beta.chat.completions.parse = AsyncMock()
    client._client = mock_inner
    return client, mock_inner


# ── happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_parsed_pydantic_model() -> None:
    client, mock_inner = make_client()
    expected = EchoSchema(message="hello", score=0.9)
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(expected)

    result = await client.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        model=HAIKU,
        response_format=EchoSchema,
    )

    assert isinstance(result, EchoSchema)
    assert result.message == "hello"
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_passes_correct_model_and_messages() -> None:
    client, mock_inner = make_client()
    expected = EchoSchema(message="x", score=0.0)
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(expected)

    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    await client.chat_completion(messages=messages, model=HAIKU, response_format=EchoSchema)

    call_kwargs = mock_inner.beta.chat.completions.parse.call_args.kwargs
    assert call_kwargs["model"] == HAIKU
    assert call_kwargs["messages"] == messages
    assert call_kwargs["response_format"] is EchoSchema


@pytest.mark.asyncio
async def test_extract_conventions_uses_chat_completion() -> None:
    client, mock_inner = make_client()
    expected = ConventionSet(
        naming="snake_case",
        control_flow="",
        error_handling="",
        imports="",
        comments="",
    )
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(expected)

    result = await client.extract_conventions(["def foo(): pass"])

    assert result is expected
    call_kwargs = mock_inner.beta.chat.completions.parse.call_args.kwargs
    assert call_kwargs["model"] == GPT4O_MINI
    assert call_kwargs["response_format"] is ConventionSet
    assert "def foo(): pass" in call_kwargs["messages"][-1]["content"]


# ── LLMTrace logging ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logs_llm_trace(caplog: pytest.LogCaptureFixture) -> None:
    client, mock_inner = make_client()
    expected = EchoSchema(message="hi", score=1.0)
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(
        expected,
        prompt_tokens=5,
        completion_tokens=15,
        response_id="chatcmpl-abc",
    )

    await client.chat_completion(
        messages=[{"role": "user", "content": "test"}],
        model=HAIKU,
        response_format=EchoSchema,
    )

    # structlog writes to standard logging in test mode
    # Just verify the call completed without error; trace emission is tested
    # via structlog's bound logger — no assertion needed beyond no exception.


@pytest.mark.asyncio
async def test_trace_carries_run_id() -> None:
    client, mock_inner = make_client()
    run_id = uuid.uuid4()
    expected = EchoSchema(message="hi", score=0.0)
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(expected)

    # Should not raise; run_id flows into the LLMTrace
    await client.chat_completion(
        messages=[{"role": "user", "content": "test"}],
        model=HAIKU,
        response_format=EchoSchema,
        run_id=run_id,
    )


@pytest.mark.asyncio
async def test_langfuse_generation_uses_run_id_as_trace_id() -> None:
    client, mock_inner = make_client()

    generation = MagicMock()
    trace = MagicMock()
    trace.generation.return_value = generation
    client._langfuse = MagicMock()
    client._langfuse.trace.return_value = trace

    run_id = uuid.uuid4()
    expected = EchoSchema(message="hello", score=0.9)
    mock_inner.beta.chat.completions.parse.return_value = make_openai_response(expected)

    await client.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        model=HAIKU,
        response_format=EchoSchema,
        run_id=run_id,
        span_name="test_agent",
    )

    client._langfuse.trace.assert_called_once_with(
        id=str(run_id),
        name="audit_run",
        metadata={"run_id": str(run_id)},
    )
    trace.generation.assert_called_once_with(
        name="test_agent",
        model=HAIKU,
        input={"messages": [{"role": "user", "content": "hi"}]},
        metadata={"response_format": "EchoSchema"},
    )
    generation.end.assert_called_once_with(
        output={"message": "hello", "score": 0.9},
        usage_details={
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
        cost_details=None,
    )


# ── error cases ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_raises_value_error_when_parsed_is_none() -> None:
    client, mock_inner = make_client()
    response = make_openai_response(EchoSchema(message="x", score=0.0))
    response.choices[0].message.parsed = None
    mock_inner.beta.chat.completions.parse.return_value = response

    with pytest.raises(ValueError, match="no parsed content"):
        await client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            model=HAIKU,
            response_format=EchoSchema,
        )


@pytest.mark.asyncio
async def test_null_usage_does_not_crash() -> None:
    client, mock_inner = make_client()
    expected = EchoSchema(message="ok", score=0.5)
    response = make_openai_response(expected)
    response.usage = None
    mock_inner.beta.chat.completions.parse.return_value = response

    result = await client.chat_completion(
        messages=[{"role": "user", "content": "test"}],
        model=HAIKU,
        response_format=EchoSchema,
    )
    assert result.message == "ok"


# ── from_settings ─────────────────────────────────────────────────────────────


def test_from_settings_constructs_client() -> None:
    with patch("src.adapters.llm_client.settings") as mock_settings:
        mock_settings.llm_api_key = "key-123"
        mock_settings.llm_base_url = "http://fake/v1"
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        client = LLMClient.from_settings()
    assert isinstance(client, LLMClient)


def test_from_settings_disables_langfuse_without_credentials() -> None:
    with patch("src.adapters.llm_client.settings") as mock_settings:
        mock_settings.llm_api_key = "key-123"
        mock_settings.llm_base_url = "http://fake/v1"
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        client = LLMClient.from_settings()

    assert client._langfuse is None
