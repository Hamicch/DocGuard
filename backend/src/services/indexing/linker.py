"""Doc-code linker.

Matches ``DocSection`` objects to ``CodeSymbol`` objects by looking for
symbol names in section headings, inline code references, and body text.
Returns a flat list of ``LinkedPair`` instances sorted by confidence
(highest first).

Matching strategy (in priority order):
    1. Exact symbol name == section heading          → confidence 1.0
    2. Symbol name in section's inline_refs          → confidence 0.9
    3. Symbol name as whole word in body             → confidence 0.7
    4. Symbol name as substring in heading or body   → confidence 0.5

Only pairs that score at or above ``MIN_CONFIDENCE`` are returned.
"""

from __future__ import annotations

import re

import structlog

from src.domain.models import CodeSymbol, DocSection, LinkedPair

logger = structlog.get_logger(__name__)

MIN_CONFIDENCE: float = 0.5


def _whole_word_pattern(name: str) -> re.Pattern[str]:
    """Return a compiled regex that matches *name* as a whole word."""
    return re.compile(rf"\b{re.escape(name)}\b")


def _score(section: DocSection, symbol: CodeSymbol) -> float:
    """Compute a confidence score for a (section, symbol) pair.

    Returns 0.0 when no evidence of a relationship is found.
    """
    name = symbol.name
    best: float = 0.0

    # 1. Heading exact match
    if section.heading == name:
        return 1.0

    # 2. Inline ref exact match
    if name in section.inline_refs:
        best = max(best, 0.9)

    # 3. Whole-word match in body
    if best < 0.7 and _whole_word_pattern(name).search(section.body):
        best = max(best, 0.7)

    # 4. Substring match in heading or body (case-sensitive)
    if best < 0.5 and (name in section.heading or name in section.body):
        best = max(best, 0.5)

    return best


def link(sections: list[DocSection], symbols: list[CodeSymbol]) -> list[LinkedPair]:
    """Match every doc section against every code symbol.

    Args:
        sections: Output of ``index_markdown``.
        symbols:  Output of ``index_python``.

    Returns:
        ``LinkedPair`` list sorted by confidence descending.
        Empty if either input is empty.
    """
    if not sections or not symbols:
        return []

    pairs: list[LinkedPair] = []

    for section in sections:
        for symbol in symbols:
            confidence = _score(section, symbol)
            if confidence >= MIN_CONFIDENCE:
                pairs.append(
                    LinkedPair(
                        doc_section=section,
                        code_symbol=symbol,
                        confidence=confidence,
                    )
                )

    pairs.sort(key=lambda p: p.confidence, reverse=True)

    logger.debug(
        "linker.done",
        sections=len(sections),
        symbols=len(symbols),
        pairs=len(pairs),
    )
    return pairs
