from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ── Enums ─────────────────────────────────────────────────────────────────────


class FindingType(StrEnum):
    doc_drift = "doc_drift"
    style_violation = "style_violation"
    convention = "convention"


class Severity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class AuditStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class UserAction(StrEnum):
    accepted = "accepted"
    dismissed = "dismissed"
    ignored = "ignored"
    custom = "custom"
    pending = "pending"


# ── Core domain models ─────────────────────────────────────────────────────────


class Repo(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    full_name: str  # e.g. "owner/repo"
    github_installation_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditRun(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    repo_id: uuid.UUID
    pr_number: int
    pr_title: str = ""
    status: AuditStatus = AuditStatus.pending
    finding_count: int = 0
    drift_count: int = 0
    style_count: int = 0
    cost_usd: float = 0.0
    gh_comment_id: int | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None


class Finding(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    run_id: uuid.UUID
    finding_type: FindingType
    severity: Severity
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    title: str
    description: str
    proposed_fix: str | None = None
    user_action: UserAction = UserAction.pending
    raw_llm_output: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Indexing intermediate types (used within the pipeline, not persisted) ──────


class CodeSymbol(BaseModel):
    name: str
    symbol_type: str  # "function" | "class" | "method"
    signature: str
    docstring: str | None = None
    file_path: str
    line_number: int


class DocSection(BaseModel):
    heading: str
    body: str
    code_blocks: list[str] = Field(default_factory=list)
    inline_refs: list[str] = Field(default_factory=list)
    file_path: str
    heading_level: int = 1


class LinkedPair(BaseModel):
    doc_section: DocSection
    code_symbol: CodeSymbol
    confidence: float  # 0.0 – 1.0


# ── Convention extraction types ───────────────────────────────────────────────


class ConventionSet(BaseModel):
    """Inferred style conventions for a repository, extracted by LLM.

    Each field is a short natural-language description of what the codebase
    does consistently, e.g. "Functions use snake_case; classes use PascalCase."
    These descriptions are passed verbatim to the style judge.
    """

    naming: str = ""
    control_flow: str = ""
    error_handling: str = ""
    imports: str = ""
    comments: str = ""


# ── Diff analysis types ───────────────────────────────────────────────────────


class DiffResult(BaseModel):
    """Output of the PR diff analyzer.

    Attributes:
        changed_symbols:  Names of Python symbols (functions/classes/methods)
                          that appear in the diff — used by the drift judge to
                          narrow which LinkedPairs need checking.
        new_code_blocks:  Raw added-code strings extracted per hunk — passed to
                          the style judge for convention checking.
        deleted_symbols:  Names of symbols present only in removed lines —
                          useful for detecting doc references to deleted code.
    """

    changed_symbols: list[str] = Field(default_factory=list)
    new_code_blocks: list[str] = Field(default_factory=list)
    deleted_symbols: list[str] = Field(default_factory=list)


# ── LLM trace / observability ─────────────────────────────────────────────────


class LLMTrace(BaseModel):
    """Emitted as a structured log event after every LLM call.

    Surfaced in the dashboard (Phase 8) to show per-run LLM usage and cost.
    """

    trace_id: str  # provider request ID (e.g. "chatcmpl-xxx")
    run_id: uuid.UUID | None = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0  # populated when provider returns cost info
    latency_ms: float = 0.0


# ── LLM judgment output types ─────────────────────────────────────────────────


class DriftJudgment(BaseModel):
    """Structured output from the drift judge LLM call."""

    drifted: bool
    severity: Severity = Severity.low
    description: str = ""
    proposed_fix: str | None = None
    reasoning: str = ""
    confidence: float = 0.0


class StyleJudgment(BaseModel):
    """Structured output from the style judge LLM call."""

    violation: bool
    severity: Severity = Severity.low
    description: str = ""
    proposed_fix: str | None = None
    reasoning: str = ""
    confidence: float = 0.0


# ── LLM structured output types ───────────────────────────────────────────────


class LLMFinding(BaseModel):
    """Raw structured output from the drift / style judge LLM calls."""

    finding_type: FindingType
    severity: Severity
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    title: str
    description: str
    proposed_fix: str | None = None
