"""Unit tests for the style judge."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.llm_client import GPT4O_MINI, LLMClient
from src.domain.models import ConventionSet, Severity, StyleJudgment
from src.services.judgment.style_judge import StyleJudge


# ── fixtures ──────────────────────────────────────────────────────────────────


def make_llm(judgment: StyleJudgment) -> LLMClient:
    llm = MagicMock(spec=LLMClient)
    llm.chat_completion = AsyncMock(return_value=judgment)
    return llm


CONVENTIONS = ConventionSet(
    naming="snake_case for functions, PascalCase for classes",
    error_handling="always raise typed exceptions",
)

VIOLATION = StyleJudgment(
    violation=True,
    severity=Severity.medium,
    description="Function uses camelCase instead of snake_case.",
    proposed_fix="Rename fetchData to fetch_data.",
    reasoning="Naming convention violated.",
    confidence=0.9,
)

NO_VIOLATION = StyleJudgment(
    violation=False,
    severity=Severity.low,
    description="",
    reasoning="Code follows all conventions.",
    confidence=0.95,
)

CODE_BLOCK = "def fetchData(url):\n    return requests.get(url)"


# ── single judgment ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_style_judgment() -> None:
    judge = StyleJudge(make_llm(VIOLATION))
    result = await judge.judge(CODE_BLOCK, CONVENTIONS)
    assert isinstance(result, StyleJudgment)
    assert result.violation is True


@pytest.mark.asyncio
async def test_passes_gpt4o_mini_by_default() -> None:
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    await judge.judge(CODE_BLOCK, CONVENTIONS)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["model"] == GPT4O_MINI


@pytest.mark.asyncio
async def test_custom_model_passed_through() -> None:
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm, model="anthropic/claude-haiku-4-5")
    await judge.judge(CODE_BLOCK, CONVENTIONS)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["model"] == "anthropic/claude-haiku-4-5"


@pytest.mark.asyncio
async def test_run_id_forwarded() -> None:
    run_id = uuid.uuid4()
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    await judge.judge(CODE_BLOCK, CONVENTIONS, run_id=run_id)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["run_id"] == run_id


@pytest.mark.asyncio
async def test_conventions_appear_in_user_message() -> None:
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    await judge.judge(CODE_BLOCK, CONVENTIONS)
    messages = llm.chat_completion.call_args.kwargs["messages"]
    user_msg = messages[1]["content"]
    assert "snake_case" in user_msg
    assert "typed exceptions" in user_msg
    assert "fetchData" in user_msg


@pytest.mark.asyncio
async def test_response_format_is_style_judgment() -> None:
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    await judge.judge(CODE_BLOCK, CONVENTIONS)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["response_format"] is StyleJudgment


# ── batch judgment ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_many_returns_all_non_empty_blocks() -> None:
    blocks = ["def a(): ...", "def b(): ...", "def c(): ..."]
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    results = await judge.judge_many(blocks, CONVENTIONS)
    assert len(results) == 3
    assert llm.chat_completion.await_count == 3


@pytest.mark.asyncio
async def test_judge_many_skips_blank_blocks() -> None:
    blocks = ["def a(): ...", "   ", "", "def b(): ..."]
    llm = make_llm(NO_VIOLATION)
    judge = StyleJudge(llm)
    results = await judge.judge_many(blocks, CONVENTIONS)
    assert len(results) == 2
    assert llm.chat_completion.await_count == 2


@pytest.mark.asyncio
async def test_judge_many_empty_returns_empty() -> None:
    judge = StyleJudge(make_llm(NO_VIOLATION))
    results = await judge.judge_many([], CONVENTIONS)
    assert results == []
