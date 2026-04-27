"""Fix drafter.

Enriches drift/style judgments that lack a ``proposed_fix`` by making one
additional LLM call per finding.  Judgments that already have a fix are
passed through unchanged.
"""

from __future__ import annotations

import uuid

import structlog
from pydantic import BaseModel

from src.adapters.llm_client import LLMClient
from src.domain.models import DriftJudgment, StyleJudgment

logger = structlog.get_logger(__name__)

type AnyJudgment = DriftJudgment | StyleJudgment

_SYSTEM_PROMPT = """\
You are a code and documentation fix generator.

Given a finding (a description of a documentation drift or style violation),
produce a short, concrete proposed fix — a single string the developer can
act on directly.  Be specific: reference exact lines, function names, or
documentation sections where possible.

Respond strictly with the JSON schema provided.
"""


class _FixResponse(BaseModel):
    proposed_fix: str


class FixDrafter:
    """Fills in ``proposed_fix`` for judgments that don't already have one.

    Args:
        llm:   Configured ``LLMClient`` instance.
        model: Model to use — should match the model that produced the judgment
               so context is preserved.
    """

    def __init__(self, llm: LLMClient, model: str) -> None:
        self._llm = llm
        self._model = model

    async def enrich(
        self,
        judgment: AnyJudgment,
        run_id: uuid.UUID | None = None,
    ) -> AnyJudgment:
        """Return *judgment* with ``proposed_fix`` guaranteed to be set.

        If ``proposed_fix`` is already present, returns *judgment* unchanged
        (no LLM call made).
        """
        if judgment.proposed_fix:
            return judgment

        kind = "documentation drift" if isinstance(judgment, DriftJudgment) else "style violation"
        user_content = f"""\
Finding type: {kind}
Severity: {judgment.severity}
Description: {judgment.description}
Reasoning: {judgment.reasoning}

Generate a concrete proposed_fix for this finding.
"""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        response = await self._llm.chat_completion(
            messages=messages,
            model=self._model,
            response_format=_FixResponse,
            run_id=run_id,
            span_name="fix_drafter",
        )

        # Return a new model instance with proposed_fix filled in
        return judgment.model_copy(update={"proposed_fix": response.proposed_fix})

    async def enrich_many(
        self,
        judgments: list[AnyJudgment],
        run_id: uuid.UUID | None = None,
    ) -> list[AnyJudgment]:
        """Enrich a list of judgments, skipping those with ``violation=False``
        or ``drifted=False`` (no finding, no fix needed).
        """
        results: list[AnyJudgment] = []
        for j in judgments:
            needs_fix = (
                (isinstance(j, DriftJudgment) and j.drifted)
                or (isinstance(j, StyleJudgment) and j.violation)
            )
            if needs_fix:
                j = await self.enrich(j, run_id=run_id)
            results.append(j)
        return results
