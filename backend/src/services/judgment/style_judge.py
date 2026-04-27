"""Code style judge.

For each new code block introduced by the PR diff, asks the LLM
(GPT-4o-mini by default) whether it violates the repository's inferred
coding conventions.  Returns a ``StyleJudgment`` per block.
"""

from __future__ import annotations

import uuid

import structlog

from src.adapters.llm_client import GPT4O_MINI, LLMClient
from src.domain.models import ConventionSet, StyleJudgment

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a code style enforcer for Python codebases.

Given a set of established coding conventions and a new block of code from a
pull request, decide whether the code violates those conventions.

Rules:
- Only flag clear, unambiguous violations — not matters of preference.
- If the conventions are empty or vague, do not flag violations.
- A violation must reference a specific convention that was broken.
- Provide a concrete proposed_fix when flagging a violation.

Respond strictly with the JSON schema provided. Be concise.
"""


def _build_user_message(code_block: str, conventions: ConventionSet) -> str:
    conv_lines = []
    if conventions.naming:
        conv_lines.append(f"Naming: {conventions.naming}")
    if conventions.control_flow:
        conv_lines.append(f"Control flow: {conventions.control_flow}")
    if conventions.error_handling:
        conv_lines.append(f"Error handling: {conventions.error_handling}")
    if conventions.imports:
        conv_lines.append(f"Imports: {conventions.imports}")
    if conventions.comments:
        conv_lines.append(f"Comments/docstrings: {conventions.comments}")

    conventions_text = "\n".join(conv_lines) if conv_lines else "(no conventions inferred)"

    return f"""\
## Established conventions

{conventions_text}

## New code from pull request

```python
{code_block}
```

## Task

Does this code violate any of the conventions above? Answer using the required JSON schema.
"""


class StyleJudge:
    """Calls the LLM to check new code blocks against inferred conventions.

    Args:
        llm:   Configured ``LLMClient`` instance.
        model: Model string to use (defaults to GPT-4o-mini).
    """

    def __init__(self, llm: LLMClient, model: str = GPT4O_MINI) -> None:
        self._llm = llm
        self._model = model

    async def judge(
        self,
        code_block: str,
        conventions: ConventionSet,
        run_id: uuid.UUID | None = None,
    ) -> StyleJudgment:
        """Judge a single new code block against the convention set.

        Args:
            code_block:   Raw added code string from the diff.
            conventions:  Inferred conventions for this repository.
            run_id:       Audit run ID forwarded to ``LLMTrace`` for tracing.

        Returns:
            ``StyleJudgment`` with ``violation``, severity, description, and fix.
        """
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(code_block, conventions)},
        ]

        judgment = await self._llm.chat_completion(
            messages=messages,
            model=self._model,
            response_format=StyleJudgment,
            run_id=run_id,
            span_name="style_judge",
        )

        logger.info(
            "style_judge.result",
            violation=judgment.violation,
            severity=judgment.severity,
            confidence=judgment.confidence,
        )
        return judgment

    async def judge_many(
        self,
        code_blocks: list[str],
        conventions: ConventionSet,
        run_id: uuid.UUID | None = None,
    ) -> list[tuple[str, StyleJudgment]]:
        """Judge multiple code blocks sequentially.

        Returns ``(code_block, judgment)`` tuples for all blocks including
        those with ``violation=False``.
        """
        results: list[tuple[str, StyleJudgment]] = []
        for block in code_blocks:
            if not block.strip():
                continue
            judgment = await self.judge(block, conventions, run_id=run_id)
            results.append((block, judgment))
        return results
