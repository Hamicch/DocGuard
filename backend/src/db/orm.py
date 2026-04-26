from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RepoORM(Base):
    __tablename__ = "repos"
    __table_args__ = (UniqueConstraint("user_id", "full_name", name="uq_repos_user_full_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    github_installation_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    runs: Mapped[list[AuditRunORM]] = relationship("AuditRunORM", back_populates="repo")


class AuditRunORM(Base):
    __tablename__ = "audit_runs"
    __table_args__ = (
        Index("idx_runs_user_recent", "user_id", "created_at"),
        Index("idx_runs_repo_pr", "repo_id", "pr_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repos.id"))
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[str | None] = mapped_column(Text)
    pr_author: Mapped[str | None] = mapped_column(Text)
    pr_url: Mapped[str | None] = mapped_column(Text)
    head_sha: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    doc_drift_count: Mapped[int] = mapped_column(Integer, default=0)
    style_violation_count: Mapped[int] = mapped_column(Integer, default=0)
    convention_violation_count: Mapped[int] = mapped_column(Integer, default=0)

    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)

    pr_comment_id: Mapped[int | None] = mapped_column(BigInteger)
    pr_comment_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    repo: Mapped[RepoORM] = relationship("RepoORM", back_populates="runs")
    findings: Mapped[list[FindingORM]] = relationship(
        "FindingORM", back_populates="run", cascade="all, delete-orphan"
    )


class FindingORM(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("idx_findings_run", "run_id"),
        Index("idx_findings_type_severity", "finding_type", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False
    )

    finding_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    current_code: Mapped[str | None] = mapped_column(Text)
    current_doc: Mapped[str | None] = mapped_column(Text)
    proposed_fix: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)

    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))

    user_action: Mapped[str | None] = mapped_column(Text)
    user_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_custom_fix: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    run: Mapped[AuditRunORM] = relationship("AuditRunORM", back_populates="findings")
