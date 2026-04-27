"""Markdown document indexer.

Parses a Markdown file using ``markdown-it-py`` and returns a list of
``DocSection`` objects — one per heading — each carrying its body text,
fenced code blocks, and inline ``code`` references found in that section.
"""

from __future__ import annotations

import re

import structlog
from markdown_it import MarkdownIt
from markdown_it.token import Token

from src.domain.models import DocSection

logger = structlog.get_logger(__name__)

# Matches inline `backtick` references in plain text
_INLINE_REF_RE = re.compile(r"`([^`]+)`")

_md = MarkdownIt()


def _token_text(token: Token) -> str:
    """Return the raw text content of a token, including children."""
    if token.content:
        return token.content
    if token.children:
        return "".join(c.content for c in token.children if c.content)
    return ""


def _heading_text(tokens: list[Token], inline_idx: int) -> str:
    """Extract plain text from the inline token inside a heading."""
    inline = tokens[inline_idx]
    if inline.children:
        return "".join(
            c.content for c in inline.children if c.type in ("text", "code_inline", "softbreak")
        )
    return inline.content


def index_markdown(file_path: str, source: str) -> list[DocSection]:
    """Parse *source* as Markdown and return one ``DocSection`` per heading.

    Sections before the first heading are collected under an implicit
    heading of ``""`` at level 0, then discarded if empty.

    Args:
        file_path: Repository-relative path stored on each ``DocSection``.
        source:    Full Markdown source text.

    Returns:
        List of ``DocSection`` instances in document order.
    """
    if not source.strip():
        logger.debug("md_indexer.empty", file=file_path)
        return []

    tokens = _md.parse(source)

    sections: list[DocSection] = []

    # Working state for the section currently being built
    current_heading: str = ""
    current_level: int = 0
    current_body_parts: list[str] = []
    current_code_blocks: list[str] = []
    current_inline_refs: list[str] = []

    def flush() -> None:
        """Save the current section (if it has a heading)."""
        body = "\n\n".join(current_body_parts).strip()
        # Discard the implicit pre-heading bucket — no heading means nothing to link against
        if not current_heading:
            return
        sections.append(
            DocSection(
                heading=current_heading,
                body=body,
                code_blocks=list(current_code_blocks),
                inline_refs=list(current_inline_refs),
                file_path=file_path,
                heading_level=current_level,
            )
        )

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            flush()
            current_heading = ""
            current_level = int(token.tag.lstrip("h"))  # "h1" → 1
            current_body_parts = []
            current_code_blocks = []
            current_inline_refs = []

            # The very next token is the inline content of the heading
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                current_heading = _heading_text(tokens, i + 1)
                i += 2  # skip heading_open + inline; heading_close follows
            # skip heading_close
            if i < len(tokens) and tokens[i].type == "heading_close":
                i += 1
            continue

        if token.type == "fence":
            # Fenced code block: token.content is the code, token.info is the lang tag
            current_code_blocks.append(token.content.rstrip())

        elif token.type == "inline":
            text = _token_text(token)
            if text.strip():
                current_body_parts.append(text)
            # Collect inline `code` references
            refs = _INLINE_REF_RE.findall(text)
            current_inline_refs.extend(refs)

        elif token.type == "code_block":
            # Indented code block
            current_code_blocks.append(token.content.rstrip())

        i += 1

    flush()

    logger.debug("md_indexer.done", file=file_path, section_count=len(sections))
    return sections
