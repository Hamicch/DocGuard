"""Unit tests for the Markdown indexer."""

from __future__ import annotations

import pytest

from src.services.indexing.md_indexer import index_markdown


# ── helpers ───────────────────────────────────────────────────────────────────


def sections_by_heading(source: str, file_path: str = "README.md") -> dict[str, object]:
    return {s.heading: s for s in index_markdown(file_path, source)}


# ── basic extraction ──────────────────────────────────────────────────────────


def test_single_heading_and_body() -> None:
    source = "# Overview\n\nThis is the overview.\n"
    result = index_markdown("README.md", source)
    assert len(result) == 1
    assert result[0].heading == "Overview"
    assert result[0].heading_level == 1
    assert "This is the overview." in result[0].body


def test_multiple_headings() -> None:
    source = """\
# Alpha

Alpha body.

## Beta

Beta body.

### Gamma

Gamma body.
"""
    result = index_markdown("doc.md", source)
    headings = [s.heading for s in result]
    assert headings == ["Alpha", "Beta", "Gamma"]


def test_heading_levels() -> None:
    source = "# H1\n\n## H2\n\n### H3\n"
    result = index_markdown("doc.md", source)
    assert result[0].heading_level == 1
    assert result[1].heading_level == 2
    assert result[2].heading_level == 3


# ── fenced code blocks ────────────────────────────────────────────────────────


def test_fenced_code_block_extracted() -> None:
    source = """\
# Usage

Run the following:

```python
def hello():
    print("hi")
```
"""
    result = index_markdown("doc.md", source)
    assert len(result[0].code_blocks) == 1
    assert "def hello" in result[0].code_blocks[0]


def test_multiple_code_blocks_in_section() -> None:
    source = """\
# Examples

```bash
echo hello
```

Some text.

```python
x = 1
```
"""
    result = index_markdown("doc.md", source)
    assert len(result[0].code_blocks) == 2


def test_code_blocks_isolated_to_their_section() -> None:
    source = """\
# Section A

```python
code_a = 1
```

# Section B

```python
code_b = 2
```
"""
    by = sections_by_heading(source)
    assert any("code_a" in b for b in by["Section A"].code_blocks)
    assert any("code_b" in b for b in by["Section B"].code_blocks)
    assert not any("code_b" in b for b in by["Section A"].code_blocks)


# ── inline refs ───────────────────────────────────────────────────────────────


def test_inline_refs_extracted() -> None:
    source = "# API\n\nCall `fetch_data` and `parse_result` to proceed.\n"
    result = index_markdown("doc.md", source)
    assert "fetch_data" in result[0].inline_refs
    assert "parse_result" in result[0].inline_refs


def test_inline_refs_isolated_to_section() -> None:
    source = """\
# A

Use `func_a`.

# B

Use `func_b`.
"""
    by = sections_by_heading(source)
    assert "func_a" in by["A"].inline_refs
    assert "func_b" not in by["A"].inline_refs


# ── file_path propagation ─────────────────────────────────────────────────────


def test_file_path_set_on_sections() -> None:
    source = "# Title\n\nBody.\n"
    result = index_markdown("docs/api.md", source)
    assert result[0].file_path == "docs/api.md"


# ── edge cases ────────────────────────────────────────────────────────────────


def test_empty_source_returns_empty_list() -> None:
    assert index_markdown("empty.md", "") == []


def test_whitespace_only_returns_empty_list() -> None:
    assert index_markdown("empty.md", "   \n\n  ") == []


def test_no_headings_returns_empty_list() -> None:
    # Plain paragraph with no heading — nothing to anchor a section to
    source = "Just some text without any heading.\n"
    result = index_markdown("doc.md", source)
    assert result == []


def test_heading_with_no_body() -> None:
    source = "# Title\n\n## Subtitle\n"
    result = index_markdown("doc.md", source)
    # Both headings should be present even without body
    headings = [s.heading for s in result]
    assert "Title" in headings
    assert "Subtitle" in headings


def test_heading_with_inline_code_in_title() -> None:
    source = "# The `run()` function\n\nBody text.\n"
    result = index_markdown("doc.md", source)
    assert "run()" in result[0].heading
