from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from dateutil import parser

from funding_agent.models import FundingCall


OPENING_WINDOW_DAYS = 183  # circa 6 mesi

IT_MONTHS = {
    "gennaio": "january",
    "febbraio": "february",
    "marzo": "march",
    "aprile": "april",
    "maggio": "may",
    "giugno": "june",
    "luglio": "july",
    "agosto": "august",
    "settembre": "september",
    "ottobre": "october",
    "novembre": "november",
    "dicembre": "december",
}


def _today() -> date:
    return date.today()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None

    raw = value.strip().lower()

    if raw in {"sportello_aperto", "open", "open_section"}:
        return None

    for it_month, en_month in IT_MONTHS.items():
        raw = raw.replace(it_month, en_month)

    try:
        parsed = parser.parse(raw, dayfirst=True, fuzzy=True)
        return parsed.date()
    except Exception:
        return None


def is_open_call(call: FundingCall) -> bool:
    deadline = (call.deadline_date or "").strip().lower()

    if deadline in {"sportello_aperto", "open", "open_section"}:
        return True

    parsed_deadline = _parse_date(call.deadline_date)

    if parsed_deadline and parsed_deadline >= _today():
        return True

    return False


def is_opening_within_six_months(call: FundingCall) -> bool:
    parsed_opening = _parse_date(call.opening_date)

    if not parsed_opening:
        return False

    today = _today()

    if parsed_opening < today:
        return False

    return parsed_opening <= today + timedelta(days=OPENING_WINDOW_DAYS)


def should_show_call(call: FundingCall) -> bool:
    if call.record_type != "call":
        return False

    return is_open_call(call) or is_opening_within_six_months(call)