"""PR comment formatter.

Renders a list of ``Finding`` objects into a single Markdown string suitable
for posting as a GitHub PR comment.

Output structure:
    ## DocGuard Review — N findings (H high, M medium, L low)
    ### Documentation Drift (n)
    ### Style Violations (n)
    ### Convention Violations (n)
"""

from __future__ import annotations

from src.domain.models import Finding, FindingType, Severity

_SEVERITY_LABEL: dict[Severity, str] = {
    Severity.high: "[HIGH]",
    Severity.medium: "[MEDIUM]",
    Severity.low: "[LOW]",
}

_TYPE_HEADING: dict[FindingType, str] = {
    FindingType.doc_drift: "Documentation Drift",
    FindingType.style_violation: "Style Violations",
    FindingType.convention: "Convention Violations",
}

_TYPE_ORDER: list[FindingType] = [
    FindingType.doc_drift,
    FindingType.style_violation,
    FindingType.convention,
]


def _finding_block(f: Finding) -> str:
    lines: list[str] = []
    severity = _SEVERITY_LABEL[f.severity]
    location = f"`{f.file_path}`"
    if f.line_start:
        location += f" line {f.line_start}"

    lines.append(f"**{severity}** · {location}")
    lines.append(f"**{f.title}**")
    lines.append(f.description)
    if f.proposed_fix:
        lines.append(f"\n**Proposed fix:** {f.proposed_fix}")
    return "\n".join(lines)


def format_comment(findings: list[Finding]) -> str:
    """Render *findings* as a Markdown PR comment body.

    Args:
        findings: List of ``Finding`` objects to render.

    Returns:
        Markdown string ready to post to GitHub.  Returns a no-findings
        message when *findings* is empty.
    """
    if not findings:
        return (
            "## DocGuard Review — no findings\n\n"
            "No documentation drift or style violations detected in this PR."
        )

    high = sum(1 for f in findings if f.severity == Severity.high)
    medium = sum(1 for f in findings if f.severity == Severity.medium)
    low = sum(1 for f in findings if f.severity == Severity.low)
    total = len(findings)

    parts: list[str] = [
        f"## DocGuard Review — {total} finding{'s' if total != 1 else ''} "
        f"({high} high, {medium} medium, {low} low)",
    ]

    by_type: dict[FindingType, list[Finding]] = {}
    for f in findings:
        by_type.setdefault(f.finding_type, []).append(f)

    for finding_type in _TYPE_ORDER:
        group = by_type.get(finding_type)
        if not group:
            continue

        parts.append(f"\n---\n\n### {_TYPE_HEADING[finding_type]} ({len(group)})\n")
        for finding in sorted(
            group, key=lambda x: list(Severity).index(x.severity)
        ):
            parts.append(_finding_block(finding))
            parts.append("")  # blank line between findings

    return "\n".join(parts).strip()
