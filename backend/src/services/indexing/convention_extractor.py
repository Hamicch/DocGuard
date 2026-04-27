"""Convention extractor.

Infers coding conventions from a sample of Python files in a repository by
making a single LLM call.  Results are cached in memory by ``head_sha`` so
the same commit never triggers a second LLM round-trip.

Usage::

    extractor = ConventionExtractor(llm_adapter)
    conventions = await extractor.extract(head_sha, file_contents)
"""

from __future__ import annotations

import structlog

from src.adapters.llm_client import HAIKU, LLMClient
from src.domain.models import ConventionSet

logger = structlog.get_logger(__name__)

# How many files to sample when the caller supplies more than this limit.
# Keeps the LLM prompt from blowing up on large repos.
MAX_FILES = 10

_SYSTEM_PROMPT = """\
You are a coding conventions analyst for Python codebases.

Given a set of representative Python source files from a repository, infer the
coding conventions used by this project. Focus on concrete, observable patterns.

Extract conventions across these dimensions:
- naming: variable, function, class naming style (snake_case, PascalCase, etc.)
- control_flow: how loops, conditionals, and early returns are used
- error_handling: exception handling patterns (specific exceptions, logging, re-raises)
- imports: import grouping, aliasing conventions
- comments: docstring format, inline comment style

Be concise. Only describe patterns you can clearly observe. Leave fields empty
if the files don't show a clear convention for that dimension.
"""


def _build_user_message(file_contents: list[str]) -> str:
    parts = []
    for i, content in enumerate(file_contents, 1):
        parts.append(f"## File {i}\n\n```python\n{content}\n```")
    return "\n\n".join(parts) + "\n\nExtract the coding conventions from these files."


class ConventionExtractor:
    """Wraps an LLM call with a per-commit cache.

    Args:
        llm: Configured ``LLMClient`` instance.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._cache: dict[str, ConventionSet] = {}

    async def extract(self, head_sha: str, file_contents: list[str]) -> ConventionSet:
        """Return the ``ConventionSet`` for *head_sha*.

        If the result for this commit is already cached, the LLM is not called
        again.  If *file_contents* is empty, a blank ``ConventionSet`` is
        returned without calling the LLM.

        Args:
            head_sha:      The commit SHA used as the cache key.
            file_contents: Python source strings for representative files
                           (5–10 recommended; extras are silently truncated).

        Returns:
            ``ConventionSet`` instance with natural-language convention fields.
        """
        if head_sha in self._cache:
            logger.debug("convention_extractor.cache_hit", sha=head_sha)
            return self._cache[head_sha]

        if not file_contents:
            logger.debug("convention_extractor.no_files", sha=head_sha)
            return ConventionSet()

        sample = file_contents[:MAX_FILES]
        logger.debug(
            "convention_extractor.calling_llm",
            sha=head_sha,
            files_sampled=len(sample),
        )

        conventions = await self._llm.chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(sample)},
            ],
            model=HAIKU,
            response_format=ConventionSet,
        )

        self._cache[head_sha] = conventions
        logger.debug("convention_extractor.cached", sha=head_sha)
        return conventions
