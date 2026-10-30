"""Render a Report as Markdown with every point linked to its HN comment."""
from __future__ import annotations

from .models import Point, Report


def _point(point: Point, report: Report) -> str:
    by_ref = {c.ref: c for c in report.comments}
    links = ", ".join(f"[{ref}]({by_ref[ref].url})" for ref in point.cites if ref in by_ref)
    return f"- **{point.point}**\n  > \"{point.quote}\" ({links})"


def to_markdown(report: Report) -> str:
    lines = [f"# What developers say about {report.tool}", ""]
    if not report.comments:
        return "\n".join(lines + ["No Hacker News threads found for this tool."])
    lines.append(f"From {len(report.comments)} comments across {len(report.stories)} Hacker News threads: "
                 + "; ".join(f"*{t}*" for t in report.stories) + ".")
    writer = "a model, then checked by the grounding validator" if report.written_by == "llm" \
        else "the rule-based analyst (quotes taken directly from comments)"
    lines += ["", f"Written by {writer}.", "", "## Pros", ""]
    lines += [_point(p, report) for p in report.pros] or ["- None found."]
    lines += ["", "## Cons", ""]
    lines += [_point(p, report) for p in report.cons] or ["- None found."]
    if report.rejected:
        lines += ["", "## Rejected by the validator", ""]
        lines += [f"- {r.side}: {r.point} ({r.reason})" for r in report.rejected]
    lines += ["", "## How this report was made", ""] + [f"1. {step}" for step in report.trace]
    return "\n".join(lines) + "\n"
