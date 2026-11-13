from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


class DataError(ValueError):
    """Raised when a source data document is invalid."""


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


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


def validate_solar_document(document: dict[str, Any]) -> None:
    year = document.get("year")
    if not isinstance(year, int) or not 1900 <= year <= 2200:
        raise DataError("solar year must be an integer between 1900 and 2200")

    source = document.get("source")
    if not isinstance(source, dict):
        raise DataError("solar source must be an object")
    for field in ("title", "url", "verification_url", "retrieved", "note"):
        _require_text(source, field, "source")
    _parse_date(source["retrieved"], "source.retrieved")

    terms = document.get("terms")
    if not isinstance(terms, list) or len(terms) != 24:
        raise DataError("terms must contain exactly 24 solar terms")

    used_ids: set[str] = set()
    used_names: set[str] = set()
    used_dates: set[date] = set()
    for index, term in enumerate(terms):
        context = f"terms[{index}]"
        if not isinstance(term, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(term, "id", context)
        _validate_id(item_id, used_ids, context)
        name = _require_text(term, "name", context)
        if name in used_names:
            raise DataError(f"duplicate solar term name: {name!r}")
        used_names.add(name)
        day = _parse_date(term.get("date"), f"{context}.date")
        if day.year != year:
            raise DataError(f"{context}.date must be inside {year}")
        if day in used_dates:
            raise DataError(f"duplicate solar term date: {day}")
        used_dates.add(day)


def load_solar_documents(data_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise DataError(f"no solar-term JSON files found in {data_dir}")
    documents: list[dict[str, Any]] = []
    years: set[int] = set()
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataError(f"cannot read {path}: {exc}") from exc
        if not isinstance(document, dict):
            raise DataError(f"{path} must contain a JSON object")
        validate_solar_document(document)
        year = document["year"]
        if path.stem != str(year):
            raise DataError(f"{path.name} does not match document year {year}")
        if year in years:
            raise DataError(f"duplicate solar-term year: {year}")
        years.add(year)
        documents.append(document)
    return sorted(documents, key=lambda item: item["year"])


def validate_common_rules(document: dict[str, Any]) -> None:
    start_year = document.get("start_year")
    end_year = document.get("end_year")
    if not isinstance(start_year, int) or not isinstance(end_year, int):
        raise DataError("common festival year range must use integers")
    if not 1900 <= start_year <= end_year <= 2200:
        raise DataError("invalid common festival year range")
    _parse_date(document.get("updated"), "updated")
    _require_text(document, "description", "common")

    fixed = document.get("fixed")
    nth_weekday = document.get("nth_weekday")
    if not isinstance(fixed, list) or not isinstance(nth_weekday, list):
        raise DataError("fixed and nth_weekday must be lists")

    used_ids: set[str] = set()
    for index, item in enumerate(fixed):
        context = f"fixed[{index}]"
        if not isinstance(item, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(item, "id", context)
        _validate_id(item_id, used_ids, context)
        _require_text(item, "name", context)
        _require_text(item, "category", context)
        month = item.get("month")
        day = item.get("day")
        if not isinstance(month, int) or not isinstance(day, int):
            raise DataError(f"{context} month and day must be integers")
        try:
            date(2000, month, day)
        except ValueError as exc:
            raise DataError(f"{context} contains an invalid month/day") from exc

    for index, item in enumerate(nth_weekday):
        context = f"nth_weekday[{index}]"
        if not isinstance(item, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(item, "id", context)
        _validate_id(item_id, used_ids, context)
        _require_text(item, "name", context)
        _require_text(item, "category", context)
        month = item.get("month")
        nth = item.get("nth")
        weekday = item.get("weekday")
        if not isinstance(month, int) or not 1 <= month <= 12:
            raise DataError(f"{context}.month must be between 1 and 12")
        if not isinstance(nth, int) or not 1 <= nth <= 5:
            raise DataError(f"{context}.nth must be between 1 and 5")
        if weekday not in WEEKDAYS:
            raise DataError(f"{context}.weekday is invalid")


def load_common_rules(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"cannot read {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise DataError(f"{path} must contain a JSON object")
    validate_common_rules(document)
    return document


def validate_common_annual_document(document: dict[str, Any]) -> None:
    year = document.get("year")
    if not isinstance(year, int) or not 1900 <= year <= 2200:
        raise DataError("common festival year must be valid")
    source = document.get("source")
    if not isinstance(source, dict):
        raise DataError("common festival source must be an object")
    for field in ("title", "url", "retrieved"):
        _require_text(source, field, "source")
    _parse_date(source["retrieved"], "source.retrieved")
    festivals = document.get("festivals")
    if not isinstance(festivals, list):
        raise DataError("festivals must be a list")
    used_ids: set[str] = set()
    for index, festival in enumerate(festivals):
        context = f"festivals[{index}]"
        if not isinstance(festival, dict):
            raise DataError(f"{context} must be an object")
        item_id = _require_text(festival, "id", context)
        _validate_id(item_id, used_ids, context)
        _require_text(festival, "name", context)
        _require_text(festival, "category", context)
        day = _parse_date(festival.get("date"), f"{context}.date")
        if day.year != year:
            raise DataError(f"{context}.date must be inside {year}")


def load_common_annual_documents(data_dir: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    years: set[int] = set()
    for path in sorted(data_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataError(f"cannot read {path}: {exc}") from exc
        if not isinstance(document, dict):
            raise DataError(f"{path} must contain a JSON object")
        validate_common_annual_document(document)
        year = document["year"]
        if path.stem != str(year):
            raise DataError(f"{path.name} does not match document year {year}")
        if year in years:
            raise DataError(f"duplicate common-festival year: {year}")
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


def _build_simple_calendar(
    calendar_name: str,
    calendar_description: str,
    events: list[tuple[date, list[str]]],
) -> bytes:
    events.sort(key=lambda item: (item[0], item[1][1]))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//fujinqiang//China Calendar Feeds//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
        f"X-WR-CALDESC:{_escape_text(calendar_description)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:PT24H",
    ]
    for _, event_lines in events:
        lines.extend(event_lines)
    lines.append("END:VCALENDAR")
    content = "\r\n".join(_fold_line(line) for line in lines) + "\r\n"
    return content.encode("utf-8")


def _simple_event(
    *,
    uid: str,
    day: date,
    summary: str,
    description: str,
    category: str,
    modified: str,
    url: str | None = None,
) -> tuple[date, list[str]]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{modified}",
        f"LAST-MODIFIED:{modified}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_escape_text(summary)}",
        f"DESCRIPTION:{_escape_text(description)}",
    ]
    if url:
        lines.append(f"URL:{url}")
    lines.extend(
        [
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "TRANSP:TRANSPARENT",
            f"CATEGORIES:{_escape_text(category)}",
            "END:VEVENT",
        ]
    )
    return day, lines


def build_solar_calendar(documents: list[dict[str, Any]]) -> bytes:
    if not documents:
        raise DataError("at least one solar-term document is required")
    events: list[tuple[date, list[str]]] = []
    for document in documents:
        validate_solar_document(document)
        source = document["source"]
        modified = _parse_date(source["retrieved"], "source.retrieved").strftime(
            "%Y%m%dT000000Z"
        )
        description = f"数据来源：{source['title']}\n{source['note']}"
        for term in document["terms"]:
            day = _parse_date(term["date"], "term.date")
            events.append(
                _simple_event(
                    uid=f"{document['year']}-{term['id']}-solar-term@china-calendar.local",
                    day=day,
                    summary=term["name"],
                    description=description,
                    category="二十四节气",
                    modified=modified,
                    url=source["url"],
                )
            )
    return _build_simple_calendar(
        "二十四节气",
        "独立的二十四节气日历，不包含法定假期和其他节日",
        events,
    )


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    result = first + timedelta(days=offset + (nth - 1) * 7)
    if result.month != month:
        raise DataError(
            f"{nth} occurrence of weekday {weekday} does not exist in {year}-{month:02d}"
        )
    return result


def build_common_festivals_calendar(
    rules: dict[str, Any], annual_documents: list[dict[str, Any]]
) -> bytes:
    validate_common_rules(rules)
    events: list[tuple[date, list[str]]] = []
    modified = _parse_date(rules["updated"], "updated").strftime("%Y%m%dT000000Z")

    for year in range(rules["start_year"], rules["end_year"] + 1):
        for item in rules["fixed"]:
            day = date(year, item["month"], item["day"])
            events.append(
                _simple_event(
                    uid=f"{year}-{item['id']}-festival@china-calendar.local",
                    day=day,
                    summary=item["name"],
                    description=rules["description"],
                    category=item["category"],
                    modified=modified,
                )
            )
        for item in rules["nth_weekday"]:
            day = _nth_weekday(
                year,
                item["month"],
                WEEKDAYS[item["weekday"]],
                item["nth"],
            )
            events.append(
                _simple_event(
                    uid=f"{year}-{item['id']}-festival@china-calendar.local",
                    day=day,
                    summary=item["name"],
                    description=rules["description"],
                    category=item["category"],
                    modified=modified,
                )
            )

    annual_years: set[int] = set()
    for document in annual_documents:
        validate_common_annual_document(document)
        year = document["year"]
        if not rules["start_year"] <= year <= rules["end_year"]:
            raise DataError(f"annual common festivals for {year} are outside rule range")
        if year in annual_years:
            raise DataError(f"duplicate annual common-festival year: {year}")
        annual_years.add(year)
        source = document["source"]
        annual_modified = _parse_date(
            source["retrieved"], "source.retrieved"
        ).strftime("%Y%m%dT000000Z")
        for item in document["festivals"]:
            day = _parse_date(item["date"], "festival.date")
            events.append(
                _simple_event(
                    uid=f"{year}-{item['id']}-festival@china-calendar.local",
                    day=day,
                    summary=item["name"],
                    description=f"数据来源：{source['title']}",
                    category=item["category"],
                    modified=annual_modified,
                    url=source["url"],
                )
            )

    return _build_simple_calendar(
        "常用节日",
        "常用文化节日、纪念日和国际习俗节日，不表示法定放假",
        events,
    )

