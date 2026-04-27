"""Provider-agnostic LLM client.

Uses the OpenAI Python SDK pointed at any OpenAI-compatible base URL.
Switching providers requires only env-var changes — no code changes.

Default routing: OpenRouter (https://openrouter.ai/api/v1).
To target OpenAI directly:  LLM_BASE_URL=https://api.openai.com/v1
To target Anthropic directly: LLM_BASE_URL=https://api.anthropic.com/v1

Usage::

    client = LLMClient.from_settings()
    result: MySchema = await client.chat_completion(
        messages=[{"role": "user", "content": "..."}],
        model=HAIKU,
        response_format=MySchema,
        run_id=run_id,
    )
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import TypeVar

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.config import settings
from src.domain.models import ConventionSet, LLMTrace

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Model name constants ───────────────────────────────────────────────────────
# These are OpenRouter model strings. If routing directly to a provider,
# replace with that provider's native model ID.

HAIKU = "anthropic/claude-haiku-4-5"
GPT4O_MINI = "openai/gpt-4o-mini"
GEMINI_FLASH = "google/gemini-flash-1.5"

_CONVENTION_SYSTEM_PROMPT = """\
You infer stable Python coding conventions from several file excerpts of the same codebase.

For each field, write one short phrase (not bullet lists) describing what the samples do \
consistently. If a topic is not visible in the samples, leave that field empty.

Fields:
- naming: function / class / variable naming patterns
- control_flow: branching, loops, early returns
- error_handling: exceptions, result types, validation
- imports: ordering and grouping
- comments: docstrings and inline comment style

Respond strictly with the JSON schema provided. Be concise.
"""


class LLMClient:
    """Thin async wrapper around ``AsyncOpenAI`` with per-call tracing.

    Args:
        api_key:  Provider API key.
        base_url: Base URL of the OpenAI-compatible endpoint.
    """

    def __init__(self, api_key: str, base_url: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._traces_by_run: dict[uuid.UUID, list[LLMTrace]] = defaultdict(list)

    @classmethod
    def from_settings(cls) -> LLMClient:
        """Construct from the application ``Settings`` singleton."""
        return cls(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        response_format: type[T],
        run_id: uuid.UUID | None = None,
    ) -> T:
        """Call the LLM and return a parsed Pydantic model.

        Uses ``client.beta.chat.completions.parse`` for structured output —
        the SDK validates the response against *response_format* automatically.

        Args:
            messages:        OpenAI-style message list.
            model:           Model string (e.g. ``HAIKU``, ``GPT4O_MINI``).
            response_format: Pydantic model class to parse the response into.
            run_id:          Optional audit run ID attached to the trace log.

        Returns:
            Parsed instance of *response_format*.

        Raises:
            openai.OpenAIError: On API or network errors.
            ValueError: If the response cannot be parsed into *response_format*.
        """
        start = time.monotonic()

        response = await self._client.beta.chat.completions.parse(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            response_format=response_format,
        )

        latency_ms = (time.monotonic() - start) * 1000
        usage = response.usage

        trace = LLMTrace(
            trace_id=response.id,
            run_id=run_id,
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=round(latency_ms, 2),
        )
        if run_id is not None:
            self._traces_by_run[run_id].append(trace)
        logger.info("llm.trace", **trace.model_dump(mode="json"))

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError(
                f"LLM returned no parsed content for model {model}. "
                "Check that the response_format schema is correct."
            )

        return parsed

    async def extract_conventions(
        self,
        file_contents: list[str],
        run_id: uuid.UUID | None = None,
    ) -> ConventionSet:
        """Infer a ``ConventionSet`` from representative Python sources."""
        blocks: list[str] = []
        for i, src in enumerate(file_contents, start=1):
            blocks.append(f"### Sample {i}\n\n```python\n{src}\n```")
        user_message = (
            "Infer stable coding conventions across these samples.\n\n" + "\n\n".join(blocks)
        )
        messages = [
            {"role": "system", "content": _CONVENTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        return await self.chat_completion(
            messages=messages,
            model=GPT4O_MINI,
            response_format=ConventionSet,
            run_id=run_id,
        )

    def pop_run_traces(self, run_id: uuid.UUID) -> list[LLMTrace]:
        """Return and clear buffered traces for a run."""
        traces = self._traces_by_run.get(run_id, [])
        if run_id in self._traces_by_run:
            del self._traces_by_run[run_id]
        return traces
