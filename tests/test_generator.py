from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from china_calendar import (
    DataError,
    build_calendar,
    build_common_festivals_calendar,
    build_solar_calendar,
    load_common_annual_documents,
    load_common_rules,
    load_documents,
    load_solar_documents,
    validate_document,
)


class CalendarGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = load_documents(ROOT / "data" / "holidays")
        self.content = build_calendar(self.documents)
        self.text = self.content.decode("utf-8")
        self.solar_documents = load_solar_documents(ROOT / "data" / "solar-terms")
        self.solar_content = build_solar_calendar(self.solar_documents)
        self.solar_text = self.solar_content.decode("utf-8")
        self.common_rules = load_common_rules(ROOT / "data" / "common-festivals.json")
        self.common_annual = load_common_annual_documents(
            ROOT / "data" / "common-festivals"
        )
        self.common_content = build_common_festivals_calendar(
            self.common_rules, self.common_annual
        )
        self.common_text = self.common_content.decode("utf-8")

    def test_2027_contains_all_official_events(self) -> None:
        self.assertEqual(self.text.count("BEGIN:VEVENT"), 12)
        expected_ranges = {
            ("20270101", "20270104", "元旦（休）"),
            ("20270131", "20270201", "春节（班）"),
            ("20270205", "20270214", "春节（休）"),
            ("20270214", "20270215", "春节（班）"),
            ("20270403", "20270406", "清明节（休）"),
            ("20270501", "20270506", "劳动节（休）"),
            ("20270508", "20270509", "劳动节（班）"),
            ("20270609", "20270610", "端午节（休）"),
            ("20270915", "20270916", "中秋节（休）"),
            ("20270926", "20270927", "国庆节（班）"),
            ("20271001", "20271008", "国庆节（休）"),
            ("20271009", "20271010", "国庆节（班）"),
        }
        for start, end, summary in expected_ranges:
            event = (
                f"DTSTART;VALUE=DATE:{start}\r\n"
                f"DTEND;VALUE=DATE:{end}\r\n"
                f"SUMMARY:{summary}\r\n"
            )
            self.assertIn(event, self.text)

    def test_output_uses_crlf_only(self) -> None:
        for content in (self.content, self.solar_content, self.common_content):
            without_crlf = content.replace(b"\r\n", b"")
            self.assertNotIn(b"\r", without_crlf)
            self.assertNotIn(b"\n", without_crlf)

    def test_folded_lines_stay_within_75_octets(self) -> None:
        for content in (self.content, self.solar_content, self.common_content):
            for line in content.split(b"\r\n"):
                self.assertLessEqual(len(line), 75, line)

    def test_output_is_deterministic(self) -> None:
        self.assertEqual(self.content, build_calendar(self.documents))
        self.assertEqual(
            self.solar_content, build_solar_calendar(self.solar_documents)
        )
        self.assertEqual(
            self.common_content,
            build_common_festivals_calendar(
                self.common_rules, self.common_annual
            ),
        )

    def test_2027_solar_terms_are_separate_and_complete(self) -> None:
        self.assertEqual(self.solar_text.count("BEGIN:VEVENT"), 24)
        expected = {
            ("20270204", "立春"),
            ("20270405", "清明"),
            ("20271107", "立冬"),
            ("20271222", "冬至"),
        }
        for day, summary in expected:
            self.assertIn(
                f"DTSTART;VALUE=DATE:{day}\r\n"
                f"DTEND;VALUE=DATE:{int(day) + 1:08d}\r\n"
                f"SUMMARY:{summary}\r\n",
                self.solar_text,
            )
        self.assertNotIn("SUMMARY:圣诞节", self.solar_text)
        self.assertNotIn("（休）", self.solar_text)

    def test_common_festivals_include_fixed_movable_and_lunar_dates(self) -> None:
        self.assertEqual(self.common_text.count("BEGIN:VEVENT"), 363)
        expected = {
            ("20270214", "情人节"),
            ("20270220", "元宵节"),
            ("20270509", "母亲节"),
            ("20270620", "父亲节"),
            ("20270808", "七夕节"),
            ("20271008", "重阳节"),
            ("20271125", "感恩节"),
            ("20271225", "圣诞节"),
        }
        for day, summary in expected:
            self.assertIn(f"DTSTART;VALUE=DATE:{day}\r\n", self.common_text)
            self.assertIn(f"SUMMARY:{summary}\r\n", self.common_text)
        self.assertNotIn("（休）", self.common_text)
        self.assertNotIn("（班）", self.common_text)

    def test_rejects_workday_inside_holiday(self) -> None:
        document = json.loads(
            (ROOT / "data" / "holidays" / "2027.json").read_text()
        )
        document["workdays"][0]["date"] = "2027-01-01"
        with self.assertRaisesRegex(DataError, "falls inside a holiday range"):
            validate_document(document)

    def test_rejects_stale_filename_year(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2028.json"
            path.write_text(
                (ROOT / "data" / "holidays" / "2027.json").read_text()
            )
            with self.assertRaisesRegex(DataError, "does not match document year"):
                load_documents(Path(directory))


if __name__ == "__main__":
    unittest.main()

