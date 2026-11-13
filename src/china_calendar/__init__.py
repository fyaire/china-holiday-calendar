"""China mainland holiday calendar generator."""

from .generator import (
    DataError,
    build_calendar,
    build_common_festivals_calendar,
    build_solar_calendar,
    load_common_annual_documents,
    load_common_rules,
    load_documents,
    load_solar_documents,
    validate_common_annual_document,
    validate_common_rules,
    validate_document,
    validate_solar_document,
)

__all__ = [
    "DataError",
    "build_calendar",
    "build_common_festivals_calendar",
    "build_solar_calendar",
    "load_common_annual_documents",
    "load_common_rules",
    "load_documents",
    "load_solar_documents",
    "validate_common_annual_document",
    "validate_common_rules",
    "validate_document",
    "validate_solar_document",
]

