"""Rule-based analyst: no model, grounded by construction.

Splits comments into sentences, scores each with a small developer-sentiment
lexicon (with simple negation), and quotes the strongest positive and negative
sentences directly. It is the fallback when the model fails and the benchmark
the model is compared against in evals.
"""
from __future__ import annotations

import re

from .hn import names_tool
from .models import Analysis, Comment, Point

POSITIVE = ("fast", "faster", "love", "great", "easy", "easier", "simple", "reliable", "stable",
            "impressive", "recommend", "enjoy", "productive", "works well", "just works", "clean",
            "nice", "excellent", "smooth", "solid", "pleasant", "better", "quick")
NEGATIVE = ("slow", "slower", "bug", "bugs", "buggy", "crash", "crashes", "broken", "pain",
            "hate", "confusing", "unstable", "issue", "issues", "problem", "problems", "missing",
            "incompatible", "leak", "worse", "annoying", "doesn't work", "frustrating", "frustrated", "breaks",
            "bloated", "flaky", "regret", "painful")
NEGATORS = re.compile(r"\b(not|never|isn't|wasn't|don't|doesn't|no)\b\s+(\w+\s+)?$")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
LINK = re.compile(r"https?://|www\.", re.I)


def _hits(sentence: str, words: tuple[str, ...]) -> int:
    lowered = sentence.lower()
    total = 0
    for word in words:
        for match in re.finditer(rf"\b{re.escape(word)}\b", lowered):
            negated = NEGATORS.search(lowered[: match.start()])
            total += -1 if negated else 1
    return total


def score(sentence: str) -> int:
    return _hits(sentence, POSITIVE) - _hits(sentence, NEGATIVE)


def analyse(tool: str, comments: list[Comment], per_side: int = 4) -> Analysis:
    scored = []
    for comment in comments:
        for sentence in SENTENCE.split(comment.text):
            sentence = sentence.strip()
            words = len(sentence.split())
            # Skip lines quoting another commenter, bare links, and mixed sentences
            # ("I love it, but it's frustrating") whose direction is ambiguous.
            if not 6 <= words <= 45 or sentence.startswith(">") or LINK.search(sentence):
                continue
            if _hits(sentence, POSITIVE) > 0 and _hits(sentence, NEGATIVE) > 0:
                continue
            bonus = 1 if names_tool(sentence, tool) else 0
            scored.append((score(sentence), bonus, sentence, comment))

    def pick(positive: bool) -> list[Point]:
        candidates = [s for s in scored if (s[0] > 0 if positive else s[0] < 0)]
        candidates.sort(key=lambda s: (-abs(s[0]), -s[1], s[3].ref))
        points, used = [], set()
        for _, _, sentence, comment in candidates:
            if comment.ref in used:
                continue  # one point per comment keeps the picture broad
            used.add(comment.ref)
            summary = sentence if len(sentence) <= 160 else sentence[:157] + "..."
            points.append(Point(point=summary, quote=sentence, cites=[comment.ref]))
            if len(points) == per_side:
                break
        return points

    return Analysis(pros=pick(True), cons=pick(False))
