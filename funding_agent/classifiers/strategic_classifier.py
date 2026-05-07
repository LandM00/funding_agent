from __future__ import annotations

from datetime import date
from dateutil import parser

from funding_agent.models import FundingCall
from funding_agent.classifiers.opportunity_type import classify_opportunity_type


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

    for it, en in IT_MONTHS.items():
        raw = raw.replace(it, en)

    try:
        return parser.parse(raw, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _days_to_deadline(call: FundingCall) -> int | None:
    deadline = _parse_date(call.deadline_date)
    if not deadline:
        return None

    return (deadline - date.today()).days


def _nex_core_matches(text: str) -> int:
    groups = [
        [
            "greenhouse",
            "serra",
            "cea",
            "controlled environment",
            "vertical farming",
            "indoor farming",
            "fuori suolo",
        ],
        [
            "sensor",
            "sensori",
            "iot",
            "monitoring",
            "monitoraggio",
            "crop monitoring",
        ],
        [
            "automation",
            "automazione",
            "autonomous",
            "controllo",
            "control",
        ],
        [
            "decision support",
            "dss",
            "ai",
            "artificial intelligence",
            "intelligenza artificiale",
            "machine learning",
        ],
        [
            "irrigation",
            "irrigazione",
            "fertigation",
            "fertirrigazione",
            "fertirrig",
        ],
        [
            "water saving",
            "risparmio idrico",
            "resource efficiency",
            "efficienza risorse",
        ],
    ]

    return sum(1 for group in groups if _has_any(text, group))


def _timing_label(call: FundingCall) -> str:
    days_left = _days_to_deadline(call)

    if (call.deadline_date or "").lower() in {"sportello_aperto", "open"}:
        return "Sempre aperto"

    if days_left is None:
        return "Data non chiara"

    if days_left < 0:
        return "Scaduto"

    if days_left <= 30:
        return "Urgente"

    if days_left <= 90:
        return "Breve termine"

    if days_left <= 180:
        return "Medio termine"

    return "Lungo termine"


def classify_call_strategy(call: FundingCall, score: float) -> dict:
    text = _text(call)
    opportunity_type = classify_opportunity_type(call)
    timing = _timing_label(call)
    nex_matches = _nex_core_matches(text)

    is_watchlist = "WATCH" in (call.call_id or "").upper() or "watchlist" in text

    strategy = "LOW_PRIORITY"
    decision = "IGNORE"
    priority = "LOW"
    next_action = "Ignora, salvo interesse specifico."

    # ------------------------------------------------------------------
    # STARTUP / NATIONAL BUSINESS FUNDING
    # ------------------------------------------------------------------
    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        strategy = "STARTUP_BUSINESS_FUNDING"

        if score >= 7.5:
            decision = "EVALUATE"
            priority = "HIGH"
            next_action = "Analizzare requisiti, spese ammissibili e compatibilità con Neura GrowTech."
        elif score >= 6.0:
            decision = "MONITOR"
            priority = "MEDIUM"
            next_action = "Valutare requisiti e compatibilità con spin-off / startup."
        else:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Tenere in lista: utile come misura business, ma non verticale su NEX."

    # ------------------------------------------------------------------
    # REGIONAL INVESTMENT - CROP / FARM / GREENHOUSE
    # ------------------------------------------------------------------
    elif opportunity_type == "REGIONAL_INVESTMENT_CROP":
        strategy = "REGIONAL_CROP_INVESTMENT"

        if score >= 7.0 or nex_matches >= 2:
            decision = "EVALUATE"
            priority = "HIGH"
            next_action = (
                "Verificare subito beneficiari e spese ammissibili: può essere utile "
                "per aziende pilota che acquistano o integrano NEX."
            )
        elif score >= 5.5:
            decision = "MONITOR"
            priority = "MEDIUM"
            next_action = (
                "Monitorare: bando agricolo produttivo, potenzialmente utile tramite "
                "azienda partner o pilota."
            )
        else:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Utile solo se emerge una chiara voce per tecnologie digitali, sensori o automazione."

    # ------------------------------------------------------------------
    # REGIONAL PROCESSING / COMMERCIALIZATION
    # ------------------------------------------------------------------
    elif opportunity_type == "REGIONAL_INVESTMENT_PROCESSING":
        strategy = "REGIONAL_PROCESSING_INVESTMENT"

        if score >= 7.0 and nex_matches >= 2:
            decision = "EVALUATE"
            priority = "MEDIUM"
            next_action = (
                "Valutare solo se NEX viene integrato in un progetto di filiera, "
                "tracciabilità, controllo qualità o automazione di processo."
            )
        elif score >= 5.0:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = (
                "Non è core NEX: monitorare solo per possibili aziende partner "
                "in trasformazione/commercializzazione."
            )
        else:
            decision = "IGNORE"
            priority = "LOW"
            next_action = (
                "Poco prioritario: centrato più su trasformazione/commercializzazione "
                "che su coltivazione autonoma."
            )

    # ------------------------------------------------------------------
    # REGIONAL ENVIRONMENT INVESTMENT
    # ------------------------------------------------------------------
    elif opportunity_type == "REGIONAL_INVESTMENT_ENVIRONMENT":
        strategy = "REGIONAL_ENVIRONMENT_INVESTMENT"

        if score >= 6.5 or nex_matches >= 2:
            decision = "EVALUATE"
            priority = "MEDIUM"
            next_action = (
                "Valutare se sono ammissibili tecnologie per riduzione input, "
                "risparmio idrico, clima o monitoraggio ambientale."
            )
        elif score >= 5.0:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Monitorare: possibile fit indiretto su clima, efficienza risorse o sostenibilità."
        else:
            decision = "IGNORE"
            priority = "LOW"
            next_action = "Fit debole con NEX."

    # ------------------------------------------------------------------
    # REGIONAL LIVESTOCK / NON-CORE
    # ------------------------------------------------------------------
    elif opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
    }:
        strategy = "REGIONAL_LIVESTOCK_NON_CORE"
        decision = "IGNORE"
        priority = "LOW"
        next_action = "Non prioritario per NEX: bando centrato su zootecnia / benessere animale."

    elif opportunity_type == "REGIONAL_NON_PRODUCTIVE_ENVIRONMENT":
        strategy = "REGIONAL_NON_PRODUCTIVE_ENVIRONMENT"
        decision = "IGNORE"
        priority = "LOW"
        next_action = "Non prioritario: investimento non produttivo/ambientale, difficilmente utile per sviluppo NEX."

    # ------------------------------------------------------------------
    # TRAINING / DEMO / CONSULTING / PROMOTION
    # ------------------------------------------------------------------
    elif opportunity_type in {
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
        "REGIONAL_PROMOTION",
        "TRAINING_COMMUNICATION",
        "MARKETING_PROMOTION",
    }:
        strategy = "LOW_CORE_REGIONAL"
        decision = "IGNORE"
        priority = "LOW"
        next_action = "Non prioritario per NEX: utile soprattutto per formazione, consulenza, comunicazione o promozione."

    elif opportunity_type == "REGIONAL_DEMONSTRATION":
        strategy = "REGIONAL_DEMONSTRATION_LOW_CORE"

        if score >= 5.5 and nex_matches >= 1:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = (
                "Monitorare solo se consente dimostrazioni tecnologiche in aziende agricole "
                "o living lab."
            )
        else:
            decision = "IGNORE"
            priority = "LOW"
            next_action = "Non prioritario: azioni dimostrative generiche, non sviluppo tecnologico diretto."

    elif opportunity_type in {
        "REGIONAL_KNOWLEDGE_TRANSFER",
        "REGIONAL_COOPERATION",
    }:
        strategy = "REGIONAL_SOFT_MEASURE"

        if score >= 6.0 and nex_matches >= 1:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Possibile interesse solo se collegato a partenariati, demo o trasferimento tecnologico."
        else:
            decision = "IGNORE"
            priority = "LOW"
            next_action = "Misura soft: non prioritaria per NEX."

    # ------------------------------------------------------------------
    # EU / HORIZON / SPACE
    # ------------------------------------------------------------------
    elif opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_RND_AGRIFOOD_ENVIRONMENT",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_SPACE",
        "EU_DEEPTECH_SCALEUP",
        "EU_RND_CONSORTIUM",
    }:
        strategy = "STRATEGIC_EU_RND"

        if opportunity_type in {"EU_SPACE", "EU_RND_DIGITAL_INDUSTRY_SPACE"}:
            strategy = "STRATEGIC_SPACE_DIGITAL"

        if opportunity_type == "EU_DEEPTECH_SCALEUP":
            strategy = "EU_DEEPTECH_SCALEUP"

        if score >= 7.0 or nex_matches >= 3:
            decision = "MONITOR_STRATEGIC"
            priority = "HIGH"
            next_action = (
                "Analizzare topic e cercare partner/consorzio: opportunità strategica, "
                "non quick win."
            )
        elif score >= 5.0 or nex_matches >= 1:
            decision = "MONITOR_STRATEGIC"
            priority = "MEDIUM"
            next_action = (
                "Monitorare strategicamente: utile per traiettoria ricerca/UE, ma richiede "
                "partner e lavoro preparatorio."
            )
        else:
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Tenere in osservazione, ma non avviare lavoro ora."

    # ------------------------------------------------------------------
    # SPACE / EXTREME ENVIRONMENTS GENERIC
    # ------------------------------------------------------------------
    elif opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        strategy = "SPACE_EXTREME_ENVIRONMENT"
        decision = "MONITOR_STRATEGIC"
        priority = "MEDIUM"
        next_action = "Valutare come opportunità strategica per applicazioni NEX in ambienti estremi/spazio."

    # ------------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------------
    else:
        if score >= 8.0:
            strategy = "HIGH_FIT"
            decision = "APPLY_NOW"
            priority = "HIGH"
            next_action = "Analizzare immediatamente la call."
        elif score >= 6.0:
            strategy = "MEDIUM_FIT"
            decision = "EVALUATE"
            priority = "MEDIUM"
            next_action = "Valutare con scheda sintetica requisiti / costi / effort."
        elif score >= 4.0:
            strategy = "LOW_FIT"
            decision = "MONITOR_LOW"
            priority = "LOW"
            next_action = "Tenere in osservazione, ma non prioritario."
        else:
            strategy = "LOW_PRIORITY"
            decision = "IGNORE"
            priority = "LOW"
            next_action = "Ignora, salvo interesse specifico."

    # ------------------------------------------------------------------
    # TIMING ADJUSTMENTS
    # ------------------------------------------------------------------
    if timing == "Urgente":
        if decision in {"APPLY_NOW", "EVALUATE"}:
            priority = "HIGH"
            next_action = "Scadenza ravvicinata: verificare subito fattibilità reale."
        elif decision in {"MONITOR", "MONITOR_STRATEGIC"}:
            priority = "HIGH"
            next_action = (
                "Scadenza ravvicinata: fare rapidamente un pre-screening, "
                "oppure scartare se non ci sono beneficiari/partner pronti."
            )

    if timing == "Scaduto":
        decision = "IGNORE"
        priority = "LOW"
        next_action = "Bando scaduto: non considerare."

    # ------------------------------------------------------------------
    # WATCHLIST ADJUSTMENT
    # ------------------------------------------------------------------
    # Le watchlist sono radar strategici, non call operative specifiche.
    # Non devono uscire come HIGH priority anche se il fit tecnico è alto.
    # Restano utili, ma come monitoraggio periodico.
    if is_watchlist and timing != "Scaduto":
        decision = "MONITOR_STRATEGIC"
        priority = "MEDIUM"
        next_action = (
            "Tenere come radar strategico: verificare periodicamente quando escono "
            "call/topic reali e cercare eventuali partner."
        )

    return {
        "strategy": strategy,
        "decision": decision,
        "priority": priority,
        "timing": timing,
        "next_action": next_action,
        "nex_core_matches": nex_matches,
    }