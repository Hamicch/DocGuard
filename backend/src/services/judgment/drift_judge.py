"""Documentation drift judge.

For each ``LinkedPair`` that was touched by the PR diff, asks the LLM
(Claude Haiku) whether the documentation still accurately describes the code.
Returns a ``DriftJudgment`` per pair.
"""

from __future__ import annotations

import uuid

import structlog

from src.adapters.llm_client import HAIKU, LLMClient
from src.domain.models import DriftJudgment, LinkedPair

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a documentation drift detector for Python codebases.

Given a changed code symbol and its linked documentation section, decide whether
the documentation has drifted — i.e., it no longer accurately describes the current
code behaviour, signature, or semantics.

Rules:
- Only flag drift when the doc is genuinely misleading or out of date.
- Minor wording differences are not drift.
- Missing docs for a new parameter IS drift.
- A doc that describes old behaviour that was removed IS drift.

Respond strictly with the JSON schema provided. Be concise in description and reasoning.
"""


def _build_user_message(pair: LinkedPair, diff_context: str) -> str:
    symbol = pair.code_symbol
    section = pair.doc_section

    return f"""\
## Changed code symbol

Name: {symbol.name}
Type: {symbol.symbol_type}
Signature: {symbol.signature}
File: {symbol.file_path} (line {symbol.line_number})
Docstring: {symbol.docstring or "(none)"}

## Diff context (lines changed around this symbol)

{diff_context or "(no diff context provided)"}

## Linked documentation section

File: {section.file_path}
Heading: {section.heading}
Body:
{section.body}

Inline code refs: {", ".join(section.inline_refs) or "(none)"}

## Task

Has this documentation drifted from the code? Answer using the required JSON schema.
"""


class DriftJudge:
    """Calls the LLM to detect documentation drift for a set of linked pairs.

    Args:
        llm: Configured ``LLMClient`` instance.
        model: Model string to use (defaults to Claude Haiku).
    """

    def __init__(self, llm: LLMClient, model: str = HAIKU) -> None:
        self._llm = llm
        self._model = model

    async def judge(
        self,
        pair: LinkedPair,
        diff_context: str = "",
        run_id: uuid.UUID | None = None,
    ) -> DriftJudgment:
        """Judge a single doc-code pair for drift.

        Args:
            pair:         The linked doc section + code symbol to evaluate.
            diff_context: Relevant diff lines around the symbol (optional but
                          strongly recommended — improves accuracy).
            run_id:       Audit run ID forwarded to ``LLMTrace`` for tracing.

        Returns:
            ``DriftJudgment`` with ``drifted``, severity, description, and fix.
        """
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(pair, diff_context)},
        ]

        judgment = await self._llm.chat_completion(
            messages=messages,
            model=self._model,
            response_format=DriftJudgment,
            run_id=run_id,
        )

        logger.info(
            "drift_judge.result",
            symbol=pair.code_symbol.name,
            drifted=judgment.drifted,
            severity=judgment.severity,
            confidence=judgment.confidence,
        )
        return judgment

    async def judge_many(
        self,
        pairs: list[LinkedPair],
        diff_context: str = "",
        run_id: uuid.UUID | None = None,
    ) -> list[tuple[LinkedPair, DriftJudgment]]:
        """Judge multiple pairs sequentially and return (pair, judgment) tuples.

        Pairs where ``drifted=False`` are included in the return value so the
        orchestrator can log the full picture. Filter on ``judgment.drifted``
        to get only actionable findings.
        """
        results: list[tuple[LinkedPair, DriftJudgment]] = []
        for pair in pairs:
            judgment = await self.judge(pair, diff_context=diff_context, run_id=run_id)
            results.append((pair, judgment))
        return results
