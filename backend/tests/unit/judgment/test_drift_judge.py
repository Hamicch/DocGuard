"""Unit tests for the drift judge."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.llm_client import HAIKU, LLMClient
from src.domain.models import (
    CodeSymbol,
    DocSection,
    DriftJudgment,
    LinkedPair,
    Severity,
)
from src.services.judgment.drift_judge import DriftJudge


# ── fixtures ──────────────────────────────────────────────────────────────────


def make_pair(
    symbol_name: str = "fetch_data",
    heading: str = "fetch_data",
    body: str = "Fetches data from the API.",
) -> LinkedPair:
    return LinkedPair(
        doc_section=DocSection(
            heading=heading,
            body=body,
            file_path="README.md",
        ),
        code_symbol=CodeSymbol(
            name=symbol_name,
            symbol_type="function",
            signature=f"{symbol_name}(url: str) -> bytes",
            file_path="src/api.py",
            line_number=10,
        ),
        confidence=1.0,
    )


def make_llm(judgment: DriftJudgment) -> LLMClient:
    llm = MagicMock(spec=LLMClient)
    llm.chat_completion = AsyncMock(return_value=judgment)
    return llm


DRIFTED = DriftJudgment(
    drifted=True,
    severity=Severity.high,
    description="Doc says returns str but code returns bytes.",
    proposed_fix="Update doc to say 'returns bytes'.",
    reasoning="Return type mismatch.",
    confidence=0.95,
)

NOT_DRIFTED = DriftJudgment(
    drifted=False,
    severity=Severity.low,
    description="",
    reasoning="Documentation accurately reflects the code.",
    confidence=0.9,
)


# ── single judgment ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_drift_judgment() -> None:
    judge = DriftJudge(make_llm(DRIFTED))
    result = await judge.judge(make_pair())
    assert isinstance(result, DriftJudgment)
    assert result.drifted is True


@pytest.mark.asyncio
async def test_passes_haiku_model_by_default() -> None:
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    await judge.judge(make_pair())
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["model"] == HAIKU


@pytest.mark.asyncio
async def test_custom_model_is_passed_through() -> None:
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm, model="openai/gpt-4o")
    await judge.judge(make_pair())
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["model"] == "openai/gpt-4o"


@pytest.mark.asyncio
async def test_run_id_forwarded_to_llm() -> None:
    run_id = uuid.uuid4()
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    await judge.judge(make_pair(), run_id=run_id)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["run_id"] == run_id


@pytest.mark.asyncio
async def test_system_and_user_messages_sent() -> None:
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    await judge.judge(make_pair(), diff_context="+ def fetch_data(url): ...")
    messages = llm.chat_completion.call_args.kwargs["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user"]
    assert "fetch_data" in messages[1]["content"]
    assert "fetch_data(url): ..." in messages[1]["content"]


@pytest.mark.asyncio
async def test_response_format_is_drift_judgment() -> None:
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    await judge.judge(make_pair())
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["response_format"] is DriftJudgment


# ── batch judgment ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_many_returns_all_pairs() -> None:
    pairs = [make_pair("fn_a"), make_pair("fn_b"), make_pair("fn_c")]
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    results = await judge.judge_many(pairs)
    assert len(results) == 3
    assert llm.chat_completion.await_count == 3


@pytest.mark.asyncio
async def test_judge_many_includes_non_drifted_pairs() -> None:
    pairs = [make_pair("fn_a"), make_pair("fn_b")]
    llm = make_llm(NOT_DRIFTED)
    judge = DriftJudge(llm)
    results = await judge.judge_many(pairs)
    assert all(isinstance(j, DriftJudgment) for _, j in results)
    assert all(j.drifted is False for _, j in results)


@pytest.mark.asyncio
async def test_judge_many_empty_returns_empty() -> None:
    judge = DriftJudge(make_llm(NOT_DRIFTED))
    results = await judge.judge_many([])
    assert results == []
