from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.models import (
    AuditRun,
    AuditStatus,
    ConventionSet,
    Finding,
    LLMFinding,
    Repo,
    UserAction,
)

# ── GitHub ────────────────────────────────────────────────────────────────────


class IGitHubAdapter(ABC):
    @abstractmethod
    async def get_pr_diff(
        self, repo_full_name: str, pr_number: int, installation_id: int
    ) -> str:
        """Return the raw unified diff text for a pull request."""

    @abstractmethod
    async def get_pr_files(
        self, repo_full_name: str, pr_number: int, installation_id: int
    ) -> list[dict[str, str]]:
        """Return changed files: [{"path": ..., "content": ...}, ...]"""

    @abstractmethod
    async def get_file_contents(
        self, repo_full_name: str, path: str, ref: str, installation_id: int
    ) -> str:
        """Return file content at a specific commit ref."""

    @abstractmethod
    async def post_pr_comment(
        self, repo_full_name: str, pr_number: int, body: str, installation_id: int
    ) -> int:
        """Post a comment on a PR and return the GitHub comment ID."""

    @abstractmethod
    async def update_pr_comment(
        self, repo_full_name: str, comment_id: int, body: str, installation_id: int
    ) -> None:
        """Update an existing PR comment."""


# ── LLM ───────────────────────────────────────────────────────────────────────


class ILLMAdapter(ABC):
    @abstractmethod
    async def judge_drift(
        self,
        diff: str,
        doc_sections: list[dict[str, str]],
        code_symbols: list[dict[str, str]],
    ) -> list[LLMFinding]:
        """Call the drift judge; returns structured findings."""

    @abstractmethod
    async def judge_style(
        self,
        diff: str,
        conventions: list[str],
    ) -> list[LLMFinding]:
        """Call the style judge; returns structured findings."""

    @abstractmethod
    async def draft_fix(self, finding: LLMFinding) -> str:
        """Return a proposed fix string for a single finding."""

    @abstractmethod
    async def extract_conventions(self, file_contents: list[str]) -> ConventionSet:
        """Infer coding conventions from representative Python file contents."""


# ── Repositories ──────────────────────────────────────────────────────────────


class IRepoRepository(ABC):
    @abstractmethod
    async def create(self, repo: Repo) -> Repo: ...

    @abstractmethod
    async def get_by_user(self, user_id: uuid.UUID) -> list[Repo]: ...

    @abstractmethod
    async def get_by_installation(self, installation_id: int) -> Repo | None: ...


class IRunRepository(ABC):
    @abstractmethod
    async def create(self, run: AuditRun) -> AuditRun: ...

    @abstractmethod
    async def update_status(
        self,
        run_id: uuid.UUID,
        status: AuditStatus,
        *,
        error: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def finalize_run(
        self,
        run_id: uuid.UUID,
        *,
        status: AuditStatus,
        finding_count: int,
        drift_count: int,
        style_count: int,
        cost_usd: float,
        duration_ms: int,
        comment_id: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update run with final counts, cost, comment ID, and status."""
        ...

    @abstractmethod
    async def get_by_id(self, run_id: uuid.UUID) -> AuditRun | None: ...

    @abstractmethod
    async def list_by_repo(self, repo_id: uuid.UUID) -> list[AuditRun]: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[AuditRun], int]:
        """Return paginated runs for all repos owned by user, plus total count."""
        ...


class IFindingRepository(ABC):
    @abstractmethod
    async def bulk_create(self, findings: list[Finding]) -> list[Finding]: ...

    @abstractmethod
    async def get_by_run(self, run_id: uuid.UUID) -> list[Finding]: ...

    @abstractmethod
    async def update_action(
        self,
        finding_id: uuid.UUID,
        action: UserAction,
        *,
        custom_fix: str | None = None,
    ) -> None: ...
