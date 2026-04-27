"""Unit tests for the doc-code linker."""

from __future__ import annotations

import pytest

from src.domain.models import CodeSymbol, DocSection
from src.services.indexing.linker import MIN_CONFIDENCE, link


# ── fixtures ──────────────────────────────────────────────────────────────────


def make_section(
    heading: str,
    body: str = "",
    inline_refs: list[str] | None = None,
    file_path: str = "README.md",
) -> DocSection:
    return DocSection(
        heading=heading,
        body=body,
        inline_refs=inline_refs or [],
        file_path=file_path,
    )


def make_symbol(name: str, file_path: str = "src/foo.py") -> CodeSymbol:
    return CodeSymbol(
        name=name,
        symbol_type="function",
        signature=f"{name}()",
        file_path=file_path,
        line_number=1,
    )


# ── confidence levels ─────────────────────────────────────────────────────────


def test_exact_heading_match_gives_full_confidence() -> None:
    sections = [make_section("fetch_data")]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert len(pairs) == 1
    assert pairs[0].confidence == 1.0


def test_inline_ref_match_gives_09() -> None:
    sections = [make_section("Usage", inline_refs=["fetch_data"])]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert len(pairs) == 1
    assert pairs[0].confidence == 0.9


def test_whole_word_body_match_gives_07() -> None:
    sections = [make_section("Guide", body="Call fetch_data to load results.")]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert len(pairs) == 1
    assert pairs[0].confidence == 0.7


def test_substring_body_match_gives_05() -> None:
    # "fetch" is a substring of body but not a whole word for "fetch_data"
    sections = [make_section("Guide", body="use fetch_data_helper here")]
    symbols = [make_symbol("fetch_data")]
    # "fetch_data" IS a substring of "fetch_data_helper"
    pairs = link(sections, symbols)
    assert len(pairs) == 1
    assert pairs[0].confidence == 0.5


def test_no_match_returns_no_pair() -> None:
    sections = [make_section("Overview", body="No relevant names here.")]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert pairs == []


# ── priority: higher confidence wins ─────────────────────────────────────────


def test_heading_beats_inline_ref_when_both_present() -> None:
    # If heading matches exactly AND inline_ref also present, score is 1.0 (heading wins)
    sections = [make_section("fetch_data", inline_refs=["fetch_data"])]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert pairs[0].confidence == 1.0


def test_inline_ref_beats_body_match() -> None:
    sections = [
        make_section("Guide", body="Call fetch_data here.", inline_refs=["fetch_data"])
    ]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert pairs[0].confidence == 0.9


# ── sorting ───────────────────────────────────────────────────────────────────


def test_results_sorted_by_confidence_descending() -> None:
    sections = [
        make_section("fetch_data"),          # exact → 1.0
        make_section("Usage", inline_refs=["parse_result"]),  # inline → 0.9
        make_section("Guide", body="Call run to start."),     # whole word → 0.7
    ]
    symbols = [
        make_symbol("fetch_data"),
        make_symbol("parse_result"),
        make_symbol("run"),
    ]
    pairs = link(sections, symbols)
    confidences = [p.confidence for p in pairs]
    assert confidences == sorted(confidences, reverse=True)


# ── empty inputs ─────────────────────────────────────────────────────────────


def test_empty_sections_returns_empty() -> None:
    assert link([], [make_symbol("fn")]) == []


def test_empty_symbols_returns_empty() -> None:
    assert link([make_section("Heading")], []) == []


def test_both_empty_returns_empty() -> None:
    assert link([], []) == []


# ── multiple matches ──────────────────────────────────────────────────────────


def test_one_section_can_match_multiple_symbols() -> None:
    section = make_section("API", inline_refs=["fetch_data", "parse_result"])
    symbols = [make_symbol("fetch_data"), make_symbol("parse_result")]
    pairs = link([section], symbols)
    assert len(pairs) == 2
    assert all(p.confidence == 0.9 for p in pairs)


def test_one_symbol_can_match_multiple_sections() -> None:
    sections = [
        make_section("fetch_data"),
        make_section("Usage", inline_refs=["fetch_data"]),
    ]
    symbols = [make_symbol("fetch_data")]
    pairs = link(sections, symbols)
    assert len(pairs) == 2


# ── pair content ─────────────────────────────────────────────────────────────


def test_pair_carries_correct_section_and_symbol() -> None:
    section = make_section("run")
    symbol = make_symbol("run")
    pairs = link([section], [symbol])
    assert pairs[0].doc_section is section
    assert pairs[0].code_symbol is symbol


# ── MIN_CONFIDENCE boundary ───────────────────────────────────────────────────


def test_min_confidence_filters_weak_matches() -> None:
    # A symbol name that appears nowhere in the section
    section = make_section("Overview", body="Completely unrelated text.")
    symbol = make_symbol("totally_absent")
    pairs = link([section], [symbol])
    assert pairs == []
