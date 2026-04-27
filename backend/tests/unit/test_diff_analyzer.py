"""Unit tests for the PR diff analyzer."""

from __future__ import annotations

import textwrap

import pytest

from src.services.indexing.diff_analyzer import analyze_diff


# ── helpers ───────────────────────────────────────────────────────────────────


def make_diff(added: list[str], removed: list[str] | None = None) -> str:
    """Build a minimal unified diff string with one hunk."""
    lines = [
        "--- a/src/foo.py",
        "+++ b/src/foo.py",
        "@@ -1,4 +1,4 @@",
    ]
    for line in removed or []:
        lines.append(f"-{line}")
    for line in added:
        lines.append(f"+{line}")
    return "\n".join(lines)


# ── empty / no-op ─────────────────────────────────────────────────────────────


def test_empty_diff_returns_empty_result() -> None:
    result = analyze_diff("")
    assert result.changed_symbols == []
    assert result.new_code_blocks == []
    assert result.deleted_symbols == []


def test_whitespace_only_diff_returns_empty_result() -> None:
    result = analyze_diff("   \n\n  ")
    assert result.changed_symbols == []


def test_diff_with_no_python_defs_returns_no_symbols() -> None:
    diff = make_diff(added=["x = 1", "y = 2"], removed=["x = 0"])
    result = analyze_diff(diff)
    assert result.changed_symbols == []
    assert result.deleted_symbols == []


# ── changed_symbols ───────────────────────────────────────────────────────────


def test_detects_added_function() -> None:
    diff = make_diff(added=["def fetch_data(url: str) -> bytes:", "    ..."])
    result = analyze_diff(diff)
    assert "fetch_data" in result.changed_symbols


def test_detects_added_async_function() -> None:
    diff = make_diff(added=["async def fetch(url): ..."])
    result = analyze_diff(diff)
    assert "fetch" in result.changed_symbols


def test_detects_added_class() -> None:
    diff = make_diff(added=["class MyService:", "    pass"])
    result = analyze_diff(diff)
    assert "MyService" in result.changed_symbols


def test_detects_modified_function_as_changed() -> None:
    diff = make_diff(
        added=["def parse(text: str) -> dict:", "    return {}"],
        removed=["def parse(text) -> dict:", "    return {}"],
    )
    result = analyze_diff(diff)
    assert "parse" in result.changed_symbols
    assert "parse" not in result.deleted_symbols


def test_changed_symbols_sorted() -> None:
    diff = make_diff(added=["def zebra(): ...", "def alpha(): ..."])
    result = analyze_diff(diff)
    assert result.changed_symbols == sorted(result.changed_symbols)


# ── deleted_symbols ───────────────────────────────────────────────────────────


def test_detects_deleted_function() -> None:
    diff = make_diff(added=[], removed=["def old_helper(): ..."])
    result = analyze_diff(diff)
    assert "old_helper" in result.deleted_symbols
    assert "old_helper" not in result.changed_symbols


def test_symbol_in_both_added_and_removed_is_changed_not_deleted() -> None:
    diff = make_diff(
        added=["def run(): return True"],
        removed=["def run(): return False"],
    )
    result = analyze_diff(diff)
    assert "run" in result.changed_symbols
    assert "run" not in result.deleted_symbols


def test_deleted_symbols_sorted() -> None:
    diff = make_diff(added=[], removed=["def zoo(): ...", "def ant(): ..."])
    result = analyze_diff(diff)
    assert result.deleted_symbols == sorted(result.deleted_symbols)


# ── new_code_blocks ───────────────────────────────────────────────────────────


def test_new_code_blocks_captures_added_lines() -> None:
    diff = make_diff(added=["x = 1", "y = 2"])
    result = analyze_diff(diff)
    assert len(result.new_code_blocks) == 1
    assert "x = 1" in result.new_code_blocks[0]
    assert "y = 2" in result.new_code_blocks[0]


def test_multiple_hunks_produce_multiple_code_blocks() -> None:
    diff = textwrap.dedent("""\
        --- a/src/foo.py
        +++ b/src/foo.py
        @@ -1,2 +1,2 @@
        -old_line_1
        +new_line_1
        @@ -10,2 +10,2 @@
        -old_line_2
        +new_line_2
    """)
    result = analyze_diff(diff)
    assert len(result.new_code_blocks) == 2


def test_hunk_with_only_removals_produces_no_code_block() -> None:
    diff = make_diff(added=[], removed=["def gone(): ..."])
    result = analyze_diff(diff)
    assert result.new_code_blocks == []


# ── file headers are not mistaken for code ────────────────────────────────────


def test_file_headers_not_treated_as_added_or_removed() -> None:
    diff = textwrap.dedent("""\
        --- a/src/foo.py
        +++ b/src/foo.py
        @@ -1,1 +1,1 @@
        +def real_fn(): ...
    """)
    result = analyze_diff(diff)
    assert "real_fn" in result.changed_symbols
    # The +++ header must not add a spurious code block containing "+++ b/src/foo.py"
    assert all("+++ b/src/foo.py" not in block for block in result.new_code_blocks)
