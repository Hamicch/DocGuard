"""Audit orchestrator.

Runs the full 14-step DocGuard pipeline for a single pull request.
All I/O dependencies are injected so the orchestrator is fully testable.

Pipeline (mirrors tasks/todo.md Phase 6 and IMPLEMENTATION_GUIDE.md):
  1.  Create DB run row (status=running).
  2.  Fetch PR metadata from GitHub API.
  3.  Fetch changed .py / .md file contents at head_sha into memory.
  4.  Index Python (AST) and Markdown from those blobs.
  5.  Link doc sections to code symbols.
  6.  Extract conventions (LLM, cached by head_sha).
  7.  Fetch unified PR diff text.
  8.  Analyze diff → changed symbols + new code blocks.
  9.  Drift judge (LLM) on linked pairs whose symbols appear in the diff.
  10. Style judge (LLM) on new code blocks vs conventions.
  11. Fix drafter pass — fill in any missing proposed_fix.
  12. Convert judgments → Finding domain objects; bulk-persist.
  13. Format and post (or update) PR comment.
  14. Finalize run (status=completed, counts, cost, comment_id, duration).

On any unhandled exception the run is marked failed and the error is logged.
"""

from __future__ import annotations

import time
import uuid
from typing import cast

import structlog

from src.adapters.llm_client import LLMClient
from src.domain.models import (
    AuditRun,
    AuditStatus,
    DriftJudgment,
    Finding,
    FindingType,
    LinkedPair,
    StyleJudgment,
)
from src.domain.ports import (
    IFindingRepository,
    IGitHubAdapter,
    IRunRepository,
)
from src.services.comment_formatter import format_comment
from src.services.indexing.ast_indexer import index_python
from src.services.indexing.convention_extractor import ConventionExtractor
from src.services.indexing.diff_analyzer import analyze_diff
from src.services.indexing.linker import link
from src.services.indexing.md_indexer import index_markdown
from src.services.judgment.drift_judge import DriftJudge
from src.services.judgment.fix_drafter import FixDrafter
from src.services.judgment.style_judge import StyleJudge

logger = structlog.get_logger(__name__)


def _drift_to_finding(
    pair: LinkedPair,
    judgment: DriftJudgment,
    run_id: uuid.UUID,
) -> Finding:
    return Finding(
        run_id=run_id,
        finding_type=FindingType.doc_drift,
        severity=judgment.severity,
        file_path=pair.code_symbol.file_path,
        line_start=pair.code_symbol.line_number,
        title=f"Documentation drift: {pair.code_symbol.name}",
        description=judgment.description,
        proposed_fix=judgment.proposed_fix,
    )


def _style_to_finding(
    judgment: StyleJudgment,
    run_id: uuid.UUID,
    file_path: str,
) -> Finding:
    return Finding(
        run_id=run_id,
        finding_type=FindingType.style_violation,
        severity=judgment.severity,
        file_path=file_path,
        title="Style violation",
        description=judgment.description,
        proposed_fix=judgment.proposed_fix,
    )


class AuditOrchestrator:
    """Wires together all pipeline services to produce a complete PR audit.

    Args:
        github:       GitHub API adapter (installation-auth aware).
        llm:          LLM client for convention extraction and judgment.
        run_repo:     Repository for ``AuditRun`` persistence.
        finding_repo: Repository for ``Finding`` persistence.
    """

    def __init__(
        self,
        github: IGitHubAdapter,
        llm: LLMClient,
        run_repo: IRunRepository,
        finding_repo: IFindingRepository,
    ) -> None:
        self._github = github
        self._llm = llm
        self._run_repo = run_repo
        self._finding_repo = finding_repo

        self._convention_extractor = ConventionExtractor(llm=llm)
        self._drift_judge = DriftJudge(llm=llm)
        self._style_judge = StyleJudge(llm=llm)

    async def run_audit(
        self,
        repo: AuditRun,
        repo_full_name: str,
        installation_id: int,
        head_sha: str,
    ) -> None:
        """Execute the full audit pipeline for *repo*.

        Args:
            repo:            Pre-created ``AuditRun`` domain object (status=pending).
            repo_full_name:  Canonical repository full name (``owner/repo``).
            installation_id: GitHub App installation ID used for auth.
            head_sha:        Head commit SHA of the PR branch.
        """
        run_id = repo.id

        log = logger.bind(run_id=str(run_id), pr=repo.pr_number)
        started_at = time.monotonic()
        comment_id: int | None = None
        findings: list[Finding] = []

        try:
            # ── 1. Mark run as running ────────────────────────────────────────
            await self._run_repo.update_status(run_id, AuditStatus.running)
            log.info("audit.started")

            # ── 3. Fetch changed files ────────────────────────────────────────
            log.info("audit.fetching_files")
            files = await self._github.get_pr_files(
                repo_full_name, repo.pr_number, installation_id, head_sha=head_sha
            )

            py_files = [f for f in files if f["path"].endswith(".py") and f["content"]]
            md_files = [f for f in files if f["path"].endswith(".md") and f["content"]]
            log.info(
                "audit.files_fetched",
                py=len(py_files),
                md=len(md_files),
            )

            # ── 4. Index Python and Markdown ──────────────────────────────────
            all_symbols = []
            for f in py_files:
                all_symbols.extend(index_python(f["path"], f["content"]))

            all_sections = []
            for f in md_files:
                all_sections.extend(index_markdown(f["path"], f["content"]))

            log.info(
                "audit.indexed",
                symbols=len(all_symbols),
                sections=len(all_sections),
            )

            # ── 5. Link doc sections to code symbols ──────────────────────────
            linked_pairs = link(all_sections, all_symbols)
            log.info("audit.linked", pairs=len(linked_pairs))

            # ── 6. Extract conventions ────────────────────────────────────────
            py_sources = [f["content"] for f in py_files]
            conventions = await self._convention_extractor.extract(head_sha, py_sources)
            log.info("audit.conventions_extracted")

            # ── 7 & 8. Fetch diff + analyze ───────────────────────────────────
            diff_text = await self._github.get_pr_diff(
                repo_full_name, repo.pr_number, installation_id
            )
            diff_result = analyze_diff(diff_text)
            log.info(
                "audit.diff_analyzed",
                changed=len(diff_result.changed_symbols),
                blocks=len(diff_result.new_code_blocks),
            )

            # ── 9. Drift judge ────────────────────────────────────────────────
            changed_set = set(diff_result.changed_symbols)
            pairs_to_judge = [
                p for p in linked_pairs if p.code_symbol.name in changed_set
            ]
            log.info("audit.drift_judging", pairs=len(pairs_to_judge))

            fix_drafter = FixDrafter(self._llm, model=self._drift_judge._model)
            drift_results = await self._drift_judge.judge_many(
                pairs_to_judge, diff_context=diff_text, run_id=run_id
            )

            for pair, drift_judgment in drift_results:
                if drift_judgment.drifted:
                    enriched_drift = cast(
                        DriftJudgment,
                        await fix_drafter.enrich(drift_judgment, run_id=run_id),
                    )
                    findings.append(_drift_to_finding(pair, enriched_drift, run_id))

            # ── 10. Style judge ───────────────────────────────────────────────
            log.info("audit.style_judging", blocks=len(diff_result.new_code_blocks))

            style_fix_drafter = FixDrafter(self._llm, model=self._style_judge._model)
            style_results = await self._style_judge.judge_many(
                [block for _, block in diff_result.new_code_blocks],
                conventions,
                run_id=run_id,
            )

            for (file_path, _), (_, style_judgment) in zip(
                diff_result.new_code_blocks, style_results, strict=True
            ):
                if style_judgment.violation:
                    enriched_style = cast(
                        StyleJudgment,
                        await style_fix_drafter.enrich(style_judgment, run_id=run_id),
                    )
                    findings.append(_style_to_finding(enriched_style, run_id, file_path))

            log.info("audit.judgments_complete", findings=len(findings))

            # ── 12. Persist findings ──────────────────────────────────────────
            if findings:
                await self._finding_repo.bulk_create(findings)

            # ── 13. Format and post PR comment ────────────────────────────────
            comment_body = format_comment(findings)
            comment_id = await self._github.post_pr_comment(
                repo_full_name, repo.pr_number, comment_body, installation_id
            )
            log.info("audit.comment_posted", comment_id=comment_id)

            # ── 14. Finalize run ──────────────────────────────────────────────
            drift_count = sum(1 for f in findings if f.finding_type == FindingType.doc_drift)
            style_count = sum(1 for f in findings if f.finding_type == FindingType.style_violation)
            duration_ms = int((time.monotonic() - started_at) * 1000)
            total_cost_usd = sum(trace.cost_usd for trace in self._llm.pop_run_traces(run_id))

            await self._run_repo.finalize_run(
                run_id,
                status=AuditStatus.completed,
                finding_count=len(findings),
                drift_count=drift_count,
                style_count=style_count,
                cost_usd=total_cost_usd,
                duration_ms=duration_ms,
                comment_id=comment_id,
            )
            log.info("audit.completed", duration_ms=duration_ms, findings=len(findings))

        except Exception as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            log.exception("audit.failed", error=str(exc))
            await self._run_repo.finalize_run(
                run_id,
                status=AuditStatus.failed,
                finding_count=len(findings),
                drift_count=0,
                style_count=0,
                cost_usd=sum(trace.cost_usd for trace in self._llm.pop_run_traces(run_id)),
                duration_ms=duration_ms,
                error=str(exc),
            )
