"""Unit tests for the audit orchestrator."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models import (
    AuditRun,
    AuditStatus,
    ConventionSet,
    DiffResult,
)
from src.domain.ports import IFindingRepository, IGitHubAdapter, IRunRepository
from src.services.audit_orchestrator import AuditOrchestrator

# ── helpers ───────────────────────────────────────────────────────────────────


def make_run(pr_title: str = "PR title") -> AuditRun:
    return AuditRun(
        repo_id=uuid.uuid4(),
        pr_number=42,
        pr_title=pr_title,
    )


def make_github(
    files: list[dict] | None = None,
    diff: str = "",
    comment_id: int = 999,
) -> IGitHubAdapter:
    gh = MagicMock(spec=IGitHubAdapter)
    gh.get_pr_files = AsyncMock(return_value=files or [])
    gh.get_pr_diff = AsyncMock(return_value=diff)
    gh.post_pr_comment = AsyncMock(return_value=comment_id)
    gh.update_pr_comment = AsyncMock()
    return gh


def make_run_repo() -> IRunRepository:
    repo = MagicMock(spec=IRunRepository)
    repo.update_status = AsyncMock()
    repo.finalize_run = AsyncMock()
    return repo


def make_finding_repo() -> IFindingRepository:
    repo = MagicMock(spec=IFindingRepository)
    repo.bulk_create = AsyncMock(return_value=[])
    return repo


def make_llm() -> MagicMock:
    return MagicMock()


def make_orchestrator(
    github: IGitHubAdapter | None = None,
    llm: MagicMock | None = None,
    run_repo: IRunRepository | None = None,
    finding_repo: IFindingRepository | None = None,
) -> AuditOrchestrator:
    return AuditOrchestrator(
        github=github or make_github(),
        llm=llm or make_llm(),
        run_repo=run_repo or make_run_repo(),
        finding_repo=finding_repo or make_finding_repo(),
    )


SHA = "abc123"
INSTALLATION_ID = 12345
REPO_FULL_NAME = "owner/repo"


# ── happy path — no files, no findings ───────────────────────────────────────


@pytest.mark.asyncio
async def test_run_marks_status_running_then_completed() -> None:
    run_repo = make_run_repo()
    orch = make_orchestrator(run_repo=run_repo)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    run_repo.update_status.assert_awaited_once_with(run.id, AuditStatus.running)
    call_kwargs = run_repo.finalize_run.call_args.kwargs
    assert call_kwargs["status"] == AuditStatus.completed


@pytest.mark.asyncio
async def test_run_posts_pr_comment() -> None:
    github = make_github()
    orch = make_orchestrator(github=github)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    github.post_pr_comment.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_uses_explicit_repo_full_name_not_pr_title() -> None:
    github = make_github()
    orch = make_orchestrator(github=github)
    run = make_run(pr_title="A human PR title")

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    github.get_pr_files.assert_awaited_once_with(
        REPO_FULL_NAME, run.pr_number, INSTALLATION_ID, head_sha=SHA
    )


@pytest.mark.asyncio
async def test_finalize_receives_comment_id() -> None:
    run_repo = make_run_repo()
    github = make_github(comment_id=777)
    orch = make_orchestrator(github=github, run_repo=run_repo)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    kwargs = run_repo.finalize_run.call_args.kwargs
    assert kwargs["comment_id"] == 777


@pytest.mark.asyncio
async def test_no_findings_skips_bulk_create() -> None:
    finding_repo = make_finding_repo()
    orch = make_orchestrator(finding_repo=finding_repo)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    finding_repo.bulk_create.assert_not_awaited()


# ── error handling ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exception_marks_run_failed() -> None:
    run_repo = make_run_repo()
    github = make_github()
    github.get_pr_files = AsyncMock(side_effect=RuntimeError("network error"))
    orch = make_orchestrator(github=github, run_repo=run_repo)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor"),
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    kwargs = run_repo.finalize_run.call_args.kwargs
    assert kwargs["status"] == AuditStatus.failed
    assert "network error" in kwargs["error"]


@pytest.mark.asyncio
async def test_exception_does_not_propagate() -> None:
    github = make_github()
    github.get_pr_files = AsyncMock(side_effect=RuntimeError("boom"))
    orch = make_orchestrator(github=github)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.ConventionExtractor"),
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
    ):
        # Should NOT raise — orchestrator catches all exceptions internally
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)


# ── file filtering ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_only_py_and_md_files_are_indexed() -> None:
    files = [
        {"path": "src/foo.py", "content": "def foo(): ..."},
        {"path": "README.md", "content": "# Title\n\nBody."},
        {"path": "config.json", "content": '{"key": "value"}'},
        {"path": "image.png", "content": ""},
    ]
    github = make_github(files=files)
    orch = make_orchestrator(github=github)
    run = make_run()

    with (
        patch("src.services.audit_orchestrator.index_python") as mock_py,
        patch("src.services.audit_orchestrator.index_markdown") as mock_md,
        patch("src.services.audit_orchestrator.ConventionExtractor") as MockCE,
        patch("src.services.audit_orchestrator.DriftJudge"),
        patch("src.services.audit_orchestrator.StyleJudge"),
        patch("src.services.audit_orchestrator.link", return_value=[]),
        patch("src.services.audit_orchestrator.analyze_diff", return_value=DiffResult()),
    ):
        mock_py.return_value = []
        mock_md.return_value = []
        MockCE.return_value.extract = AsyncMock(return_value=ConventionSet())
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    # Only foo.py indexed (json and image skipped; image has empty content)
    assert mock_py.call_count == 1
    assert mock_py.call_args[0][0] == "src/foo.py"

    # Only README.md indexed
    assert mock_md.call_count == 1
    assert mock_md.call_args[0][0] == "README.md"


@pytest.mark.asyncio
async def test_convention_extractor_receives_run_id() -> None:
    files = [{"path": "src/foo.py", "content": "def foo(): ..."}]
    github = make_github(files=files)
    orch = make_orchestrator(github=github)
    run = make_run()

    orch._convention_extractor = MagicMock()
    orch._convention_extractor.extract = AsyncMock(return_value=ConventionSet())
    orch._drift_judge = MagicMock()
    orch._drift_judge.judge_many = AsyncMock(return_value=[])
    orch._drift_judge._model = "test-drift-model"
    orch._style_judge = MagicMock()
    orch._style_judge.judge_many = AsyncMock(return_value=[])
    orch._style_judge._model = "test-style-model"

    with (
        patch("src.services.audit_orchestrator.index_python", return_value=[]),
        patch("src.services.audit_orchestrator.index_markdown", return_value=[]),
        patch("src.services.audit_orchestrator.link", return_value=[]),
        patch("src.services.audit_orchestrator.analyze_diff", return_value=DiffResult()),
    ):
        await orch.run_audit(run, REPO_FULL_NAME, INSTALLATION_ID, SHA)

    orch._convention_extractor.extract.assert_awaited_once_with(
        SHA,
        ["def foo(): ..."],
        run_id=run.id,
    )
