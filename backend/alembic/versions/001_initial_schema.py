"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("github_installation_id", sa.BigInteger, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "full_name", name="uq_repos_user_full_name"),
    )

    op.create_table(
        "audit_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "repo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repos.id"),
            nullable=True,
        ),
        sa.Column("pr_number", sa.Integer, nullable=False),
        sa.Column("pr_title", sa.Text, nullable=True),
        sa.Column("pr_author", sa.Text, nullable=True),
        sa.Column("pr_url", sa.Text, nullable=True),
        sa.Column("head_sha", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("total_findings", sa.Integer, server_default="0"),
        sa.Column("doc_drift_count", sa.Integer, server_default="0"),
        sa.Column("style_violation_count", sa.Integer, server_default="0"),
        sa.Column("convention_violation_count", sa.Integer, server_default="0"),
        sa.Column("llm_tokens_used", sa.Integer, server_default="0"),
        sa.Column("cost_estimate_usd", sa.Numeric(10, 4), server_default="0"),
        sa.Column("pr_comment_id", sa.BigInteger, nullable=True),
        sa.Column("pr_comment_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_runs_user_recent", "audit_runs", ["user_id", "created_at"])
    op.create_index("idx_runs_repo_pr", "audit_runs", ["repo_id", "pr_number"])

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_type", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("line_number", sa.Integer, nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("current_code", sa.Text, nullable=True),
        sa.Column("current_doc", sa.Text, nullable=True),
        sa.Column("proposed_fix", sa.Text, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("user_action", sa.Text, nullable=True),
        sa.Column("user_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_custom_fix", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_findings_run", "findings", ["run_id"])
    op.create_index("idx_findings_type_severity", "findings", ["finding_type", "severity"])


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_index("idx_runs_repo_pr", "audit_runs")
    op.drop_index("idx_runs_user_recent", "audit_runs")
    op.drop_table("audit_runs")
    op.drop_table("repos")
