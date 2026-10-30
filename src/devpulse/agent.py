"""The DevPulse loop: retrieve -> propose -> validate -> repair once -> fall back.

    retrieve   top HN threads about the tool, their comments numbered C1..Cn
    propose    the model drafts pros and cons with quotes and citations
    validate   drop anything whose quote isn't in the comment it cites
    repair     if anything was dropped, send the reasons back once
    fall back  if the model fails or nothing survives, the rule-based analyst
               writes the report instead (it is grounded by construction)

Every step is written to the trace so the report shows how it was produced.
"""
from __future__ import annotations

from .baseline import analyse as baseline_analyse
from .hn import HackerNews
from .llm import LLMAnalyst, ModelError
from .models import Analysis, Comment, Rejection, Report
from .validator import validate


async def run_analysis(tool: str, comments: list[Comment], analyst: LLMAnalyst | None) -> tuple[Analysis, str, list[Rejection], list[str]]:
    trace: list[str] = [f"retrieved {len(comments)} comments"]
    rejected: list[Rejection] = []
    if analyst is not None and analyst.available and comments:
        try:
            draft = await analyst.analyse(tool, comments)
            kept, dropped = validate(draft, comments)
            trace.append(f"model proposed {len(draft.pros)} pros, {len(draft.cons)} cons; "
                         f"validator rejected {len(dropped)}")
            rejected += dropped
            if dropped:
                feedback = "These points were rejected. Fix or remove them:\n" + "\n".join(
                    f"- {r.side}: {r.point!r} ({r.reason})" for r in dropped)
                repaired = await analyst.analyse(tool, comments, feedback=feedback)
                kept, dropped = validate(repaired, comments)
                trace.append(f"repair attempt: validator rejected {len(dropped)}")
                rejected += dropped
            if kept.pros or kept.cons:
                return kept, "llm", rejected, trace
            trace.append("no grounded points survived; falling back to the baseline")
        except ModelError as exc:
            trace.append(f"model call failed ({exc}); falling back to the baseline")
    elif comments:
        trace.append("no model configured; using the baseline")
    analysis = baseline_analyse(tool, comments)
    trace.append(f"baseline wrote {len(analysis.pros)} pros, {len(analysis.cons)} cons")
    return analysis, "baseline", rejected, trace


async def investigate(tool: str, hn: HackerNews | None = None, analyst: LLMAnalyst | None = None,
                stories: int = 3, max_comments: int = 40) -> Report:
    hn = hn or HackerNews()
    titles, comments = await hn.comments(tool, stories=stories, max_comments=max_comments)
    analysis, written_by, rejected, trace = await run_analysis(tool, comments, analyst)
    trace.insert(0, f"found {len(titles)} HN threads about {tool!r}")
    return Report(tool=tool, stories=titles, comments=comments, pros=analysis.pros,
                  cons=analysis.cons, written_by=written_by, rejected=rejected, trace=trace)
