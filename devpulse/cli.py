"""devpulse "<tool>" [--json] [--out FILE] [--no-llm]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import investigate
from .llm import LLMAnalyst
from .render import to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="devpulse",
                                     description="What do developers say about a tool? Cited from Hacker News.")
    parser.add_argument("tool", help='tool or library name, e.g. "Bun"')
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--out", type=Path, help="also write the output to this file")
    parser.add_argument("--no-llm", action="store_true", help="use the rule-based analyst only")
    parser.add_argument("--threads", type=int, default=3, help="HN threads to read (default 3)")
    args = parser.parse_args(argv)

    report = investigate(args.tool, analyst=None if args.no_llm else LLMAnalyst(), stories=args.threads)
    output = report.model_dump_json(indent=2) if args.json else to_markdown(report)
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
