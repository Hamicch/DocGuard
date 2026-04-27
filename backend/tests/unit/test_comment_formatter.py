"""Unit tests for the PR comment formatter."""

from __future__ import annotations

import uuid

import pytest

from src.domain.models import Finding, FindingType, Severity
from src.services.comment_formatter import format_comment


def make_finding(
    finding_type: FindingType = FindingType.doc_drift,
    severity: Severity = Severity.medium,
    title: str = "Test finding",
    description: str = "Something drifted.",
    file_path: str = "src/foo.py",
    proposed_fix: str | None = None,
    line_start: int | None = None,
) -> Finding:
    return Finding(
        run_id=uuid.uuid4(),
        finding_type=finding_type,
        severity=severity,
        file_path=file_path,
        line_start=line_start,
        title=title,
        description=description,
        proposed_fix=proposed_fix,
    )


# ── empty findings ────────────────────────────────────────────────────────────


def test_empty_findings_returns_no_findings_message() -> None:
    result = format_comment([])
    assert "no findings" in result.lower()
    assert "DocGuard Review" in result


# ── summary header ────────────────────────────────────────────────────────────


def test_header_shows_total_count() -> None:
    findings = [make_finding(), make_finding()]
    result = format_comment(findings)
    assert "2 findings" in result


def test_header_shows_singular_when_one_finding() -> None:
    result = format_comment([make_finding()])
    assert "1 finding" in result
    assert "1 findings" not in result


def test_header_shows_severity_counts() -> None:
    findings = [
        make_finding(severity=Severity.high),
        make_finding(severity=Severity.medium),
        make_finding(severity=Severity.medium),
        make_finding(severity=Severity.low),
    ]
    result = format_comment(findings)
    assert "1 high" in result
    assert "2 medium" in result
    assert "1 low" in result


# ── grouping by type ──────────────────────────────────────────────────────────


def test_drift_findings_appear_under_drift_heading() -> None:
    findings = [make_finding(finding_type=FindingType.doc_drift)]
    result = format_comment(findings)
    assert "Documentation Drift" in result


def test_style_findings_appear_under_style_heading() -> None:
    findings = [make_finding(finding_type=FindingType.style_violation)]
    result = format_comment(findings)
    assert "Style Violations" in result


def test_groups_with_no_findings_are_omitted() -> None:
    findings = [make_finding(finding_type=FindingType.doc_drift)]
    result = format_comment(findings)
    assert "Style Violations" not in result
    assert "Convention Violations" not in result


def test_multiple_types_all_present() -> None:
    findings = [
        make_finding(finding_type=FindingType.doc_drift),
        make_finding(finding_type=FindingType.style_violation),
        make_finding(finding_type=FindingType.convention),
    ]
    result = format_comment(findings)
    assert "Documentation Drift" in result
    assert "Style Violations" in result
    assert "Convention Violations" in result


# ── finding content ───────────────────────────────────────────────────────────


def test_finding_title_appears_in_output() -> None:
    findings = [make_finding(title="fetch_data signature changed")]
    result = format_comment(findings)
    assert "fetch_data signature changed" in result


def test_finding_description_appears() -> None:
    findings = [make_finding(description="The doc is out of date.")]
    result = format_comment(findings)
    assert "The doc is out of date." in result


def test_file_path_appears_in_output() -> None:
    findings = [make_finding(file_path="src/api/client.py")]
    result = format_comment(findings)
    assert "src/api/client.py" in result


def test_proposed_fix_appears_when_present() -> None:
    findings = [make_finding(proposed_fix="Update the docstring.")]
    result = format_comment(findings)
    assert "Update the docstring." in result
    assert "Proposed fix" in result


def test_no_proposed_fix_section_when_absent() -> None:
    findings = [make_finding(proposed_fix=None)]
    result = format_comment(findings)
    assert "Proposed fix" not in result


def test_severity_label_appears() -> None:
    findings = [make_finding(severity=Severity.high)]
    result = format_comment(findings)
    assert "[HIGH]" in result


def test_line_number_appears_when_set() -> None:
    findings = [make_finding(line_start=42)]
    result = format_comment(findings)
    assert "line 42" in result


def test_no_line_number_when_none() -> None:
    findings = [make_finding(line_start=None)]
    result = format_comment(findings)
    assert "line None" not in result
