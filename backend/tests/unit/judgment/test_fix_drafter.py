"""Unit tests for the fix drafter."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from src.adapters.llm_client import LLMClient
from src.domain.models import DriftJudgment, Severity, StyleJudgment
from src.services.judgment.fix_drafter import FixDrafter, _FixResponse


# ── fixtures ──────────────────────────────────────────────────────────────────


def make_llm(fix: str = "Update the docstring.") -> LLMClient:
    llm = MagicMock(spec=LLMClient)
    llm.chat_completion = AsyncMock(return_value=_FixResponse(proposed_fix=fix))
    return llm


def make_drift(drifted: bool = True, fix: str | None = None) -> DriftJudgment:
    return DriftJudgment(
        drifted=drifted,
        severity=Severity.medium,
        description="Doc is out of date.",
        proposed_fix=fix,
        reasoning="Code changed.",
        confidence=0.9,
    )


def make_style(violation: bool = True, fix: str | None = None) -> StyleJudgment:
    return StyleJudgment(
        violation=violation,
        severity=Severity.low,
        description="Wrong naming convention.",
        proposed_fix=fix,
        reasoning="camelCase used.",
        confidence=0.85,
    )


# ── enrich single judgment ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fills_missing_fix_for_drift() -> None:
    llm = make_llm("Update docs to reflect new return type.")
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")
    result = await drafter.enrich(make_drift(fix=None))
    assert result.proposed_fix == "Update docs to reflect new return type."


@pytest.mark.asyncio
async def test_fills_missing_fix_for_style() -> None:
    llm = make_llm("Rename fetchData to fetch_data.")
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")
    result = await drafter.enrich(make_style(fix=None))
    assert result.proposed_fix == "Rename fetchData to fetch_data."


@pytest.mark.asyncio
async def test_skips_llm_when_fix_already_present() -> None:
    llm = make_llm()
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")
    judgment = make_drift(fix="Already has a fix.")
    result = await drafter.enrich(judgment)
    llm.chat_completion.assert_not_awaited()
    assert result.proposed_fix == "Already has a fix."


@pytest.mark.asyncio
async def test_returns_new_instance_not_mutated() -> None:
    drafter = FixDrafter(make_llm("a fix"), model="openai/gpt-4o-mini")
    original = make_drift(fix=None)
    result = await drafter.enrich(original)
    assert original.proposed_fix is None  # original unchanged
    assert result.proposed_fix is not None


@pytest.mark.asyncio
async def test_run_id_forwarded() -> None:
    run_id = uuid.uuid4()
    llm = make_llm()
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")
    await drafter.enrich(make_drift(fix=None), run_id=run_id)
    _, kwargs = llm.chat_completion.call_args
    assert kwargs["run_id"] == run_id


# ── enrich_many ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrich_many_only_calls_llm_for_actionable_judgments() -> None:
    llm = make_llm()
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")

    judgments = [
        make_drift(drifted=True, fix=None),    # needs fix
        make_drift(drifted=False, fix=None),   # no finding — skip
        make_style(violation=True, fix=None),  # needs fix
        make_style(violation=False, fix=None), # no finding — skip
    ]

    results = await drafter.enrich_many(judgments)
    assert len(results) == 4
    assert llm.chat_completion.await_count == 2  # only drifted + violation


@pytest.mark.asyncio
async def test_enrich_many_skips_when_fix_already_set() -> None:
    llm = make_llm()
    drafter = FixDrafter(llm, model="openai/gpt-4o-mini")
    judgments = [make_drift(drifted=True, fix="pre-existing fix")]
    await drafter.enrich_many(judgments)
    llm.chat_completion.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_many_empty_returns_empty() -> None:
    drafter = FixDrafter(make_llm(), model="openai/gpt-4o-mini")
    result = await drafter.enrich_many([])
    assert result == []
