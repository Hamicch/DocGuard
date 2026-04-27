"""PR unified diff analyzer.

Parses a raw unified diff and extracts:

- ``changed_symbols``  — Python symbol names (functions / classes) that appear
  in added or removed lines.  Used by the drift judge to restrict which
  ``LinkedPair`` objects need checking.
- ``new_code_blocks``  — Contiguous chunks of added lines per hunk as
  ``(file_path, code_block)`` tuples. Passed to the style judge for
  convention checking.
- ``deleted_symbols``  — Symbol names present only in removed lines (not in any
  added line).  Useful for spotting doc references to deleted code.

Strategy
--------
Regex is used to find symbol definitions (``def`` / ``async def`` / ``class``)
inside ``+`` and ``-`` lines.  Full AST parsing is intentionally avoided because
diff hunks are rarely valid standalone Python.
"""

from __future__ import annotations

import re

import structlog

from src.domain.models import DiffResult

logger = structlog.get_logger(__name__)

# Matches Python function / class definitions at any indentation level.
_SYMBOL_DEF_RE = re.compile(
    r"^(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(|^class\s+([A-Za-z_]\w*)\s*[:(]",
    re.MULTILINE,
)

# Unified diff markers
_FILE_HEADER_RE = re.compile(r"^(?:\+\+\+|---)\s")
_HUNK_HEADER_RE = re.compile(r"^@@")


def _extract_symbol_names(code: str) -> set[str]:
    """Return all symbol names found in *code* via regex."""
    names: set[str] = set()
    for match in _SYMBOL_DEF_RE.finditer(code):
        name = match.group(1) or match.group(2)
        if name:
            names.add(name)
    return names


def _parse_file_path_from_header(line: str) -> str | None:
    if not line.startswith("+++ "):
        return None
    raw = line.removeprefix("+++ ").strip()
    if raw == "/dev/null":
        return None
    if raw.startswith("b/"):
        return raw[2:]
    return raw


def _iter_hunks(diff_text: str) -> list[tuple[str, list[str], list[str]]]:
    """Split *diff_text* into hunks and return file-scoped hunk tuples."""
    hunks: list[tuple[str, list[str], list[str]]] = []
    added: list[str] = []
    removed: list[str] = []
    in_hunk = False
    current_file_path = "(unknown)"

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            if in_hunk and (added or removed):
                hunks.append((current_file_path, added, removed))
                added = []
                removed = []
            parsed_path = _parse_file_path_from_header(line)
            current_file_path = parsed_path or "(unknown)"
            in_hunk = False
            continue

        if line.startswith("--- "):
            if in_hunk and (added or removed):
                hunks.append((current_file_path, added, removed))
                added = []
                removed = []
            in_hunk = False
            continue

        if _FILE_HEADER_RE.match(line):
            if in_hunk and (added or removed):
                hunks.append((current_file_path, added, removed))
                added = []
                removed = []
            in_hunk = False
            continue

        if _HUNK_HEADER_RE.match(line):
            if in_hunk and (added or removed):
                hunks.append((current_file_path, added, removed))
            added = []
            removed = []
            in_hunk = True
            continue

        if not in_hunk:
            continue

        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])

    if in_hunk and (added or removed):
        hunks.append((current_file_path, added, removed))

    return hunks


def analyze_diff(diff_text: str) -> DiffResult:
    """Parse *diff_text* and return a ``DiffResult``.

    Args:
        diff_text: Raw unified diff string (as returned by GitHub's diff API).

    Returns:
        ``DiffResult`` with changed symbols, new code blocks, and deleted symbols.
        All fields are empty when the diff is empty or contains no Python changes.
    """
    if not diff_text.strip():
        logger.debug("diff_analyzer.empty")
        return DiffResult()

    all_added_names: set[str] = set()
    all_removed_names: set[str] = set()
    new_code_blocks: list[tuple[str, str]] = []

    for file_path, added_lines, removed_lines in _iter_hunks(diff_text):
        added_code = "\n".join(added_lines)
        removed_code = "\n".join(removed_lines)

        added_names = _extract_symbol_names(added_code)
        removed_names = _extract_symbol_names(removed_code)

        all_added_names |= added_names
        all_removed_names |= removed_names

        if added_code.strip():
            new_code_blocks.append((file_path, added_code))

    # A symbol is "changed" if it appears in added lines (modified or new).
    # A symbol is "deleted" if it appears only in removed lines.
    changed_symbols = sorted(all_added_names)
    deleted_symbols = sorted(all_removed_names - all_added_names)

    logger.debug(
        "diff_analyzer.done",
        changed=len(changed_symbols),
        deleted=len(deleted_symbols),
        blocks=len(new_code_blocks),
    )

    return DiffResult(
        changed_symbols=changed_symbols,
        new_code_blocks=new_code_blocks,
        deleted_symbols=deleted_symbols,
    )
