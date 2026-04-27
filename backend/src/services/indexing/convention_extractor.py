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

from src.domain.models import ConventionSet
from src.domain.ports import ILLMAdapter

logger = structlog.get_logger(__name__)

# How many files to sample when the caller supplies more than this limit.
# Keeps the LLM prompt from blowing up on large repos.
MAX_FILES = 10


class ConventionExtractor:
    """Wraps ``ILLMAdapter.extract_conventions`` with a per-commit cache.

    Args:
        llm: Any concrete implementation of ``ILLMAdapter``.
    """

    def __init__(self, llm: ILLMAdapter) -> None:
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

        conventions = await self._llm.extract_conventions(sample)

        self._cache[head_sha] = conventions
        logger.debug("convention_extractor.cached", sha=head_sha)
        return conventions
