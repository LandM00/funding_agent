from __future__ import annotations

from datetime import date
from dateutil import parser

from funding_agent.models import FundingCall


def _text(call: FundingCall) -> str:
    return " ".join(
        [
            call.title or "",
            call.summary or "",
            call.program or "",
            call.raw_text or "",
            " ".join(call.topics or []),
            " ".join(call.eligible_entities or []),
            call.source or "",
            call.call_id or "",
        ]
    ).lower()


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(k.lower() in text for k in keywords)


def _parse_date(value: str | None):
    if not value:
        return None

    raw = value.strip().lower()
    if raw in {"sportello_aperto", "open", "open_section"}:
        return None

    try:
        return parser.parse(value, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _score_thematic_fit(call: FundingCall, text: str) -> float:
    score = 0.0

    # Agritech / agriculture
    if _has_any(text, ["agriculture", "agricoltura", "agritech", "farm", "farming", "food systems"]):
        score += 1.2

    # Fit diretto con NEX
    if _has_any(text, ["greenhouse", "serra", "controlled environment", "cea", "vertical farming"]):
        score += 1.6

    if _has_any(text, ["irrigation", "irrigazione"]):
        score += 1.2

    if _has_any(text, ["fertigation", "fertirrigazione", "fertirrig"]):
        score += 1.3

    if _has_any(text, ["crop monitoring", "monitoraggio colturale", "decision support", "dss"]):
        score += 1.4

    # Ambiente / bioeconomia: rilevante, ma meno diretto
    if _has_any(text, ["bioeconomy", "bioeconomia", "circbio"]):
        score += 0.8

    if _has_any(text, ["climate", "clima", "biodiversity", "biodiversità", "environment", "ambiente", "zero pollution"]):
        score += 0.7

    return min(score, 4.0)


def _score_technology_fit(call: FundingCall, text: str) -> float:
    score = 0.0

    if _has_any(text, ["ai", "artificial intelligence", "intelligenza artificiale"]):
        score += 0.8

    if _has_any(text, ["sensor", "sensori", "iot"]):
        score += 0.7

    if _has_any(text, ["automation", "automazione", "autonomous", "autonomo"]):
        score += 0.7

    if _has_any(text, ["data", "digital", "digitale", "earth observation", "copernicus"]):
        score += 0.5

    if _has_any(text, ["robot", "robotics", "robotica", "drone", "uav"]):
        score += 0.5

    return min(score, 2.0)


def _score_business_fit(call: FundingCall, text: str) -> float:
    score = 0.0
    source = (call.source or "").lower()
    program = (call.program or "").lower()
    call_id = (call.call_id or "").upper()

    # Opportunità molto accessibili per spin-off/startup
    if "invitalia" in source:
        score += 2.2

    if _has_any(text, ["startup innovative", "startup innovativa"]):
        score += 1.2
    elif "startup" in text:
        score += 0.8

    if _has_any(text, ["pmi", "sme", "micro e piccole imprese", "impresa"]):
        score += 0.7

    if _has_any(text, ["finanziamento agevolato", "tasso zero", "fondo perduto", "grant"]):
        score += 0.9

    # Horizon è strategico, ma meno immediato: bonus moderato
    if "horizon europe" in program:
        score += 0.8

    if "EIC" in call_id or "eic" in program:
        score += 1.3

    return min(score, 2.5)


def _score_feasibility(call: FundingCall, text: str) -> float:
    score = 0.0
    source = (call.source or "").lower()
    program = (call.program or "").lower()

    # Accessibilità
    if "invitalia" in source:
        score += 1.6

    if "horizon europe" in program:
        score -= 0.8  # consorzio, proposta lunga, competizione alta

    if _has_any(text, ["consortia", "consortium", "consorzio"]):
        score -= 0.4

    # Timing
    deadline = (call.deadline_date or "").strip().lower()

    if deadline == "sportello_aperto":
        score += 1.4
    else:
        parsed_deadline = _parse_date(call.deadline_date)
        today = date.today()

        if parsed_deadline:
            days_left = (parsed_deadline - today).days

            if days_left < 0:
                score -= 2.0
            elif days_left <= 45:
                score += 0.3  # urgente, ma poco tempo
            elif days_left <= 180:
                score += 1.0  # finestra buona
            else:
                score += 0.7  # tempo lungo, preparabile

    opening = _parse_date(call.opening_date)
    if opening:
        days_to_open = (opening - date.today()).days
        if 0 <= days_to_open <= 180:
            score += 0.7

    return max(-1.5, min(score, 1.5))


def _score_strategic_value(call: FundingCall, text: str) -> float:
    score = 0.0
    call_id = (call.call_id or "").upper()

    # Valore strategico per NEX / Neura GrowTech
    if "CL6" in call_id:
        score += 0.8

    if "GOVERNANCE" in call_id:
        score += 0.6  # dati, osservazioni, digital solutions: molto coerente con piattaforma

    if "CIRCBIO" in call_id:
        score += 0.4

    if "ZEROPOLLUTION" in call_id:
        score += 0.3

    if "BIODIV" in call_id:
        score += 0.3

    if _has_any(text, ["greenhouse", "controlled environment", "irrigation", "fertigation", "dss", "sensor", "ai"]):
        score += 0.8

    return min(score, 1.5)


def score_call(call: FundingCall, config: dict) -> float:
    text = _text(call)

    filters = config.get("filters", {})
    positives = filters.get("keywords_positive", [])
    negatives = filters.get("keywords_negative", [])

    thematic = _score_thematic_fit(call, text)
    technology = _score_technology_fit(call, text)
    business = _score_business_fit(call, text)
    feasibility = _score_feasibility(call, text)
    strategic = _score_strategic_value(call, text)

    keyword_adjust = 0.0

    for kw in positives:
        if kw.lower() in text:
            keyword_adjust += 0.08

    for kw in negatives:
        if kw.lower() in text:
            keyword_adjust -= 0.6

    penalty = 0.0

    if call.record_type == "hub":
        penalty -= 4.0

    if call.record_type == "support_doc":
        penalty -= 2.0

    final_score = thematic + technology + business + feasibility + strategic + keyword_adjust + penalty
    final_score = max(0.0, min(10.0, final_score))

    return round(final_score, 1)