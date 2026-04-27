"""Unit tests for the convention extractor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.models import ConventionSet, LLMFinding
from src.domain.ports import ILLMAdapter
from src.services.indexing.convention_extractor import MAX_FILES, ConventionExtractor


# ── mock adapter ──────────────────────────────────────────────────────────────


def make_llm(conventions: ConventionSet | None = None) -> ILLMAdapter:
    """Return a mock ILLMAdapter whose extract_conventions returns *conventions*."""
    adapter = MagicMock(spec=ILLMAdapter)
    adapter.extract_conventions = AsyncMock(
        return_value=conventions or ConventionSet(
            naming="snake_case for functions",
            control_flow="early returns preferred",
            error_handling="raise typed exceptions",
            imports="stdlib then third-party",
            comments="docstrings on public functions",
        )
    )
    return adapter


SHA = "abc123"
FILES = ["def foo(): ...", "class Bar: ..."]


# ── happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_convention_set() -> None:
    extractor = ConventionExtractor(make_llm())
    result = await extractor.extract(SHA, FILES)
    assert isinstance(result, ConventionSet)
    assert result.naming == "snake_case for functions"


@pytest.mark.asyncio
async def test_llm_called_once_per_sha() -> None:
    llm = make_llm()
    extractor = ConventionExtractor(llm)

    await extractor.extract(SHA, FILES)
    await extractor.extract(SHA, FILES)  # second call — should hit cache

    llm.extract_conventions.assert_awaited_once()


@pytest.mark.asyncio
async def test_different_shas_each_call_llm() -> None:
    llm = make_llm()
    extractor = ConventionExtractor(llm)

    await extractor.extract("sha_a", FILES)
    await extractor.extract("sha_b", FILES)

    assert llm.extract_conventions.await_count == 2


@pytest.mark.asyncio
async def test_cached_result_is_same_object() -> None:
    extractor = ConventionExtractor(make_llm())
    first = await extractor.extract(SHA, FILES)
    second = await extractor.extract(SHA, FILES)
    assert first is second


# ── empty inputs ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_files_returns_blank_convention_set_without_llm_call() -> None:
    llm = make_llm()
    extractor = ConventionExtractor(llm)
    result = await extractor.extract(SHA, [])
    assert isinstance(result, ConventionSet)
    assert result.naming == ""
    llm.extract_conventions.assert_not_awaited()


# ── file sampling ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_truncates_to_max_files() -> None:
    llm = make_llm()
    extractor = ConventionExtractor(llm)
    many_files = [f"def fn_{i}(): ..." for i in range(MAX_FILES + 5)]

    await extractor.extract(SHA, many_files)

    called_with = llm.extract_conventions.call_args.args[0]
    assert len(called_with) == MAX_FILES


@pytest.mark.asyncio
async def test_fewer_than_max_files_passes_all() -> None:
    llm = make_llm()
    extractor = ConventionExtractor(llm)
    few_files = ["def a(): ...", "def b(): ..."]

    await extractor.extract(SHA, few_files)

    called_with = llm.extract_conventions.call_args.args[0]
    assert len(called_with) == 2


# ── cache isolation across instances ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_not_shared_between_extractor_instances() -> None:
    llm = make_llm()
    extractor_a = ConventionExtractor(llm)
    extractor_b = ConventionExtractor(llm)

    await extractor_a.extract(SHA, FILES)
    await extractor_b.extract(SHA, FILES)

    assert llm.extract_conventions.await_count == 2
