from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from china_calendar import DataError, build_calendar, load_documents, validate_document


class CalendarGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = load_documents(ROOT / "data")
        self.content = build_calendar(self.documents)
        self.text = self.content.decode("utf-8")

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
        without_crlf = self.content.replace(b"\r\n", b"")
        self.assertNotIn(b"\r", without_crlf)
        self.assertNotIn(b"\n", without_crlf)

    def test_folded_lines_stay_within_75_octets(self) -> None:
        for line in self.content.split(b"\r\n"):
            self.assertLessEqual(len(line), 75, line)

    def test_output_is_deterministic(self) -> None:
        self.assertEqual(self.content, build_calendar(self.documents))

    def test_rejects_workday_inside_holiday(self) -> None:
        document = json.loads((ROOT / "data" / "2027.json").read_text())
        document["workdays"][0]["date"] = "2027-01-01"
        with self.assertRaisesRegex(DataError, "falls inside a holiday range"):
            validate_document(document)

    def test_rejects_stale_filename_year(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2028.json"
            path.write_text((ROOT / "data" / "2027.json").read_text())
            with self.assertRaisesRegex(DataError, "does not match document year"):
                load_documents(Path(directory))


if __name__ == "__main__":
    unittest.main()

