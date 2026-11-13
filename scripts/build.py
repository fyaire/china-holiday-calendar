#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from china_calendar import DataError, build_calendar, load_documents  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the China mainland holiday subscription calendar."
    )
    parser.add_argument(
        "--data-dir", type=Path, default=ROOT / "data", help="annual JSON directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "china-holidays.ics",
        help="generated ICS path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the existing output differs from generated content",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        documents = load_documents(args.data_dir)
        content = build_calendar(documents)
    except DataError as exc:
        print(f"data error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        if not args.output.exists():
            print(f"missing generated file: {args.output}", file=sys.stderr)
            return 1
        if args.output.read_bytes() != content:
            print(
                f"generated file is stale: run python3 scripts/build.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {args.output} is up to date")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(
        f"Wrote {args.output} ({sum(len(d['holidays']) + len(d['workdays']) for d in documents)} events)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

