from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from dateutil import parser

from funding_agent.models import FundingCall


TODAY = date.today()
OPENING_WINDOW_DAYS = 183  # circa 6 mesi


NON_CALL_TITLES = {
    "strumenti utili",
    "tutti i settori",
    "percorso di accelerazione",
    "premio economico",
    "scienze della vita",
    "innovazione sociale",
    "energia e ambiente",
    "meccanica e materiali",
    "icc - industrie culturali e creative",
    "industrie culturali e creative",
    "agroalimentare",
    "costruzioni",
}


NON_CALL_URL_PARTS = [
    "/categoria/",
    "/tipologia-bando/",
    "/settore-bando/",
    "/tag/",
    "/taxonomy/",
    "/pagine/strumenti-utili",
]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None

    raw = value.strip().lower()

    if raw in {"sportello_aperto", "open", "open_section"}:
        return None

    try:
        parsed = parser.parse(value, dayfirst=True, fuzzy=True)
        return parsed.date()
    except Exception:
        return None


def _is_non_call_record(call: FundingCall) -> bool:
    title = (call.title or "").strip().lower()
    url = (call.source_url or "").strip().lower()

    if title in NON_CALL_TITLES:
        return True

    if any(part in url for part in NON_CALL_URL_PARTS):
        return True

    return False


def is_open_call(call: FundingCall) -> bool:
    deadline = (call.deadline_date or "").strip().lower()

    if deadline in {"sportello_aperto", "open", "open_section"}:
        return True

    parsed_deadline = _parse_date(call.deadline_date)
    if parsed_deadline and parsed_deadline >= TODAY:
        return True

    return False


def is_opening_within_six_months(call: FundingCall) -> bool:
    parsed_opening = _parse_date(call.opening_date)
    if not parsed_opening:
        return False

    if parsed_opening < TODAY:
        return False

    return parsed_opening <= TODAY + timedelta(days=OPENING_WINDOW_DAYS)


def should_show_call(call: FundingCall) -> bool:
    if call.record_type != "call":
        return False

    if _is_non_call_record(call):
        return False

    return is_open_call(call) or is_opening_within_six_months(call)