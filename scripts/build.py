#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from china_calendar import (  # noqa: E402
    DataError,
    build_calendar,
    build_common_festivals_calendar,
    build_solar_calendar,
    load_common_annual_documents,
    load_common_rules,
    load_documents,
    load_solar_documents,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the China mainland holiday subscription calendar."
    )
    parser.add_argument(
        "--data-root", type=Path, default=ROOT / "data", help="calendar data root"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="generated ICS directory",
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
        holiday_documents = load_documents(args.data_root / "holidays")
        solar_documents = load_solar_documents(args.data_root / "solar-terms")
        common_rules = load_common_rules(args.data_root / "common-festivals.json")
        common_annual = load_common_annual_documents(
            args.data_root / "common-festivals"
        )
        outputs = {
            args.output_dir / "china-holidays.ics": build_calendar(
                holiday_documents
            ),
            args.output_dir / "solar-terms.ics": build_solar_calendar(
                solar_documents
            ),
            args.output_dir / "common-festivals.ics": build_common_festivals_calendar(
                common_rules, common_annual
            ),
        }
    except DataError as exc:
        print(f"data error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        stale = []
        for path, content in outputs.items():
            if not path.exists() or path.read_bytes() != content:
                stale.append(path)
        if stale:
            for path in stale:
                print(f"generated file is missing or stale: {path}", file=sys.stderr)
            print("run python3 scripts/build.py", file=sys.stderr)
            return 1
        print(f"OK: {len(outputs)} generated calendars are up to date")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_bytes(content)
        print(f"Wrote {path} ({content.count(b'BEGIN:VEVENT')} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

