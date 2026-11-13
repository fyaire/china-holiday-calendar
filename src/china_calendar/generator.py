from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


class DataError(ValueError):
    """Raised when a source data document is invalid."""


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise DataError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DataError(f"{field} is not a valid ISO date: {value!r}") from exc


def _require_text(mapping: dict[str, Any], field: str, context: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{context}.{field} must be non-empty text")
    return value.strip()


def validate_document(document: dict[str, Any]) -> None:
    year = document.get("year")
    if not isinstance(year, int) or not 1900 <= year <= 2200:
        raise DataError("year must be an integer between 1900 and 2200")

    source = document.get("source")
    if not isinstance(source, dict):
        raise DataError("source must be an object")
    for field in (
        "title",
        "document_no",
        "published",
        "url",
        "verification_url",
        "retrieved",
    ):
        _require_text(source, field, "source")
    _parse_date(source["published"], "source.published")
    _parse_date(source["retrieved"], "source.retrieved")

    holidays = document.get("holidays")
    workdays = document.get("workdays")
    if not isinstance(holidays, list) or not holidays:
        raise DataError("holidays must be a non-empty list")
    if not isinstance(workdays, list):
        raise DataError("workdays must be a list")

    used_ids: set[str] = set()
    holiday_ranges: list[tuple[date, date, str]] = []

    for index, holiday in enumerate(holidays):
        context = f"holidays[{index}]"
        if not isinstance(holiday, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(holiday, "id", context)
        _validate_id(item_id, used_ids, context)
        _require_text(holiday, "name", context)
        start = _parse_date(holiday.get("start"), f"{context}.start")
        end = _parse_date(holiday.get("end"), f"{context}.end")
        if start.year != year or end.year != year:
            raise DataError(f"{context} dates must be inside {year}")
        if end < start:
            raise DataError(f"{context}.end must not precede start")
        holiday_ranges.append((start, end, item_id))

    for current, following in zip(
        sorted(holiday_ranges), sorted(holiday_ranges)[1:]
    ):
        if following[0] <= current[1]:
            raise DataError(
                f"holiday ranges overlap: {current[2]!r} and {following[2]!r}"
            )

    for index, workday in enumerate(workdays):
        context = f"workdays[{index}]"
        if not isinstance(workday, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(workday, "id", context)
        _validate_id(item_id, used_ids, context)
        _require_text(workday, "name", context)
        day = _parse_date(workday.get("date"), f"{context}.date")
        if day.year != year:
            raise DataError(f"{context}.date must be inside {year}")
        if any(start <= day <= end for start, end, _ in holiday_ranges):
            raise DataError(f"{context}.date falls inside a holiday range")


def _validate_id(item_id: str, used_ids: set[str], context: str) -> None:
    if not ID_PATTERN.fullmatch(item_id):
        raise DataError(f"{context}.id must use lowercase kebab-case")
    if item_id in used_ids:
        raise DataError(f"duplicate id in one year: {item_id!r}")
    used_ids.add(item_id)


def load_documents(data_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise DataError(f"no JSON data files found in {data_dir}")

    documents: list[dict[str, Any]] = []
    years: set[int] = set()
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataError(f"cannot read {path}: {exc}") from exc
        if not isinstance(document, dict):
            raise DataError(f"{path} must contain a JSON object")
        validate_document(document)
        year = document["year"]
        if path.stem != str(year):
            raise DataError(f"{path.name} does not match document year {year}")
        if year in years:
            raise DataError(f"duplicate year: {year}")
        years.add(year)
        documents.append(document)
    return sorted(documents, key=lambda item: item["year"])


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold_line(line: str) -> str:
    if not line:
        return line
    chunks: list[str] = []
    current = ""
    limit = 75
    for char in line:
        if current and len((current + char).encode("utf-8")) > limit:
            chunks.append(current)
            current = char
            limit = 74
        else:
            current += char
    chunks.append(current)
    return "\r\n ".join(chunks)


def _event_lines(document: dict[str, Any]) -> Iterable[tuple[date, list[str]]]:
    year = document["year"]
    source = document["source"]
    modified = _parse_date(source["published"], "source.published").strftime(
        "%Y%m%dT000000Z"
    )
    description = _escape_text(
        f"依据：{source['title']}（{source['document_no']}）\n{source['url']}"
    )

    for holiday in document["holidays"]:
        start = _parse_date(holiday["start"], "holiday.start")
        end = _parse_date(holiday["end"], "holiday.end") + timedelta(days=1)
        lines = [
            "BEGIN:VEVENT",
            f"UID:{year}-{holiday['id']}-holiday@china-calendar.local",
            f"DTSTAMP:{modified}",
            f"LAST-MODIFIED:{modified}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{end:%Y%m%d}",
            f"SUMMARY:{_escape_text(holiday['name'] + '（休）')}",
            f"DESCRIPTION:{description}",
            f"URL:{source['url']}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "TRANSP:TRANSPARENT",
            "CATEGORIES:法定节假日",
            "X-APPLE-SPECIAL-DAY:WORK-HOLIDAY",
            "END:VEVENT",
        ]
        yield start, lines

    for workday in document["workdays"]:
        day = _parse_date(workday["date"], "workday.date")
        next_day = day + timedelta(days=1)
        lines = [
            "BEGIN:VEVENT",
            f"UID:{year}-{workday['id']}-workday@china-calendar.local",
            f"DTSTAMP:{modified}",
            f"LAST-MODIFIED:{modified}",
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{next_day:%Y%m%d}",
            f"SUMMARY:{_escape_text(workday['name'] + '（班）')}",
            f"DESCRIPTION:{description}",
            f"URL:{source['url']}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "TRANSP:TRANSPARENT",
            "CATEGORIES:调休上班",
            "X-APPLE-SPECIAL-DAY:ALTERNATE-WORKDAY",
            "END:VEVENT",
        ]
        yield day, lines


def build_calendar(documents: list[dict[str, Any]]) -> bytes:
    if not documents:
        raise DataError("at least one document is required")
    for document in documents:
        validate_document(document)

    events: list[tuple[date, list[str]]] = []
    for document in documents:
        events.extend(_event_lines(document))
    events.sort(key=lambda item: (item[0], item[1][1]))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//fujinqiang//China Mainland Holiday Calendar//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:中国大陆法定节假日与调休",
        "X-WR-CALDESC:国务院办公厅正式公布的放假与调休安排",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:PT24H",
    ]
    for _, event_lines in events:
        lines.extend(event_lines)
    lines.append("END:VCALENDAR")

    content = "\r\n".join(_fold_line(line) for line in lines) + "\r\n"
    return content.encode("utf-8")

