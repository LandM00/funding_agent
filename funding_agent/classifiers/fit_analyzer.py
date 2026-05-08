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


def _title_text(call: FundingCall) -> str:
    return " ".join(
        [
            call.title or "",
            call.program or "",
            call.call_id or "",
        ]
    ).lower()


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(k.lower() in text for k in keywords)


def _count_groups(text: str, groups: list[list[str]]) -> int:
    return sum(1 for group in groups if _has_any(text, group))


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


def _is_generic_startup_opportunity(
    opportunity_type: str,
    technical: float,
    strategic: float,
    text: str,
) -> bool:
    """
    True quando una call è utile per startup/business, ma non è chiaramente
    verticale su NEX, agritech, AI applicata, CEA, sensoristica, spazio o R&D strategica.
    Serve a evitare che premi/challenge/incubatori generici risultino troppo prioritari.
    """
    if opportunity_type not in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        return False

    strategic_keywords = [
        "agritech",
        "agroalimentare",
        "agriculture",
        "agricoltura",
        "greenhouse",
        "serra",
        "controlled environment",
        "vertical farming",
        "sensor",
        "sensori",
        "iot",
        "monitoring",
        "monitoraggio",
        "artificial intelligence",
        "intelligenza artificiale",
        "machine learning",
        "dss",
        "decision support",
        "automation",
        "automazione",
        "irrigation",
        "irrigazione",
        "fertigation",
        "fertirrigazione",
        "esa",
        "asi",
        "space",
        "spazio",
        "satellite",
        "horizon",
        "eic",
        "eureka",
        "eurostars",
        "deep tech",
        "deep-tech",
    ]

    has_strategic_keyword = _has_any(text, strategic_keywords)

    return technical < 2.0 and strategic < 2.2 and not has_strategic_keyword


def _get_profile(config: dict) -> dict:
    return config.get("project_profile", {}) or {}


def _profile_terms(config: dict, section: str, level: str | None = None) -> list[str]:
    profile = _get_profile(config)

    if section == "keywords":
        keywords = profile.get("keywords", {})
        if level:
            return keywords.get(level, []) or []

        terms = []
        for values in keywords.values():
            terms.extend(values or [])
        return terms

    return profile.get(section, []) or []


def analyze_fit(call: FundingCall, config: dict) -> dict:
    """
    Valutazione multidimensionale 0-5 + score finale 0-10.

    Logica:
    - technical_fit: quanto il contenuto è vicino al core tecnico di NEX
    - business_fit: quanto può finanziare sviluppo, investimento, startup, scale-up
    - applicant_fit: quanto i beneficiari sono compatibili con NGT/UniBo/partner agricoli
    - feasibility: quanto è realistico candidarsi
    - strategic_value: quanto è utile per la traiettoria strategica NEX
    - timing_score: urgenza / finestra temporale
    """

    text = _text(call)
    title_text = _title_text(call)
    opportunity_type = classify_opportunity_type(call)
    is_watchlist = "WATCH" in (call.call_id or "").upper() or "watchlist" in text

    high_terms = _profile_terms(config, "keywords", "high")
    medium_terms = _profile_terms(config, "keywords", "medium")
    low_terms = _profile_terms(config, "keywords", "low")
    weak_negative = _profile_terms(config, "weak_negative_domains")
    hard_negative = _profile_terms(config, "hard_negative_domains")
    target_applicant = _profile_terms(config, "target_applicant")
    project_goals = _profile_terms(config, "project_goals")

    # ------------------------------------------------------------------
    # CORE NEX GROUPS
    # ------------------------------------------------------------------
    nex_groups = [
        [
            "greenhouse",
            "serra",
            "controlled environment",
            "controlled environment agriculture",
            "vertical farming",
            "cea",
            "indoor farming",
            "fuori suolo",
        ],
        [
            "sensor",
            "sensori",
            "iot",
            "monitoraggio",
            "monitoring",
            "crop monitoring",
            "environmental observations",
        ],
        [
            "automation",
            "automazione",
            "autonomous",
            "controllo",
            "control",
            "robotics",
            "robotica",
        ],
        [
            "decision support",
            "decision support system",
            "dss",
            "artificial intelligence",
            "intelligenza artificiale",
            "ai",
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
            "fertilizer reduction",
            "riduzione fertilizzanti",
        ],
    ]

    nex_group_matches = _count_groups(text, nex_groups)

    # ------------------------------------------------------------------
    # TECHNICAL FIT 0-5
    # ------------------------------------------------------------------
    technical = 0.0

    # Keyword NEX molto specifiche
    technical += min(2.6, sum(1 for t in high_terms if t.lower() in text) * 0.42)
    technical += min(1.2, sum(1 for t in medium_terms if t.lower() in text) * 0.16)
    technical += min(0.4, sum(1 for t in low_terms if t.lower() in text) * 0.04)

    # Bonus per gruppi core NEX
    technical += min(2.0, nex_group_matches * 0.45)

    # Bonus specifici su titolo/call_id, più affidabili del raw_text
    if _has_any(title_text, ["serra", "greenhouse", "controlled environment", "vertical farming"]):
        technical += 1.0

    if _has_any(title_text, ["irrigazione", "irrigation", "fertirrigazione", "fertigation"]):
        technical += 0.8

    if _has_any(title_text, ["digitale", "digital", "sensori", "sensors", "monitoraggio", "monitoring"]):
        technical += 0.8

    # Penalizzazioni
    if _has_any(text, weak_negative):
        technical -= 0.8

    if _has_any(text, hard_negative):
        technical -= 3.0

    if opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
        "REGIONAL_PROMOTION",
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
    }:
        technical -= 1.0

    if opportunity_type in {"REGIONAL_DEMONSTRATION"}:
        technical -= 0.5

    technical = max(0.0, min(5.0, technical))

    # ------------------------------------------------------------------
    # BUSINESS FIT 0-5
    # ------------------------------------------------------------------
    business = 0.0

    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        business += 4.0

    elif opportunity_type == "REGIONAL_INVESTMENT_CROP":
        business += 3.2

    elif opportunity_type == "REGIONAL_INVESTMENT_PROCESSING":
        business += 2.2

    elif opportunity_type == "REGIONAL_INVESTMENT_ENVIRONMENT":
        business += 2.4

    elif opportunity_type == "REGIONAL_INVESTMENT":
        business += 2.6

    elif opportunity_type == "REGIONAL_NON_PRODUCTIVE_ENVIRONMENT":
        business += 1.2

    elif opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_RND_AGRIFOOD_ENVIRONMENT",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_SPACE",
        "EU_DEEPTECH_SCALEUP",
        "EU_RND_CONSORTIUM",
    }:
        business += 2.4

    elif opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        # Non è business funding classico, ma ESA/ASI/BASS possono finanziare PoC,
        # pilot, validazione e sviluppo applicativo.
        business += 1.8

    elif opportunity_type in {
        "REGIONAL_DEMONSTRATION",
        "REGIONAL_KNOWLEDGE_TRANSFER",
        "REGIONAL_COOPERATION",
    }:
        business += 1.0

    elif opportunity_type in {
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
        "REGIONAL_PROMOTION",
        "TRAINING_COMMUNICATION",
        "MARKETING_PROMOTION",
    }:
        business += 0.2

    elif opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
    }:
        business += 0.4

    if _has_any(
        text,
        [
            "fondo perduto",
            "tasso zero",
            "finanziamento agevolato",
            "contributo",
            "grant",
            "sovvenzione",
        ],
    ):
        business += 0.8

    if _has_any(
        text,
        [
            "investimenti",
            "industrializzazione",
            "scale",
            "scalare",
            "commercializzazione",
            "impianti",
            "attrezzature",
        ],
    ):
        business += 0.5

    if _has_any(text, ["promozione", "marketing", "formazione", "informazione"]):
        business -= 0.8

    business = max(0.0, min(5.0, business))

    # ------------------------------------------------------------------
    # APPLICANT FIT 0-5
    # ------------------------------------------------------------------
    applicant = 0.0

    if any(t.lower() in text for t in target_applicant):
        applicant += 2.0

    if _has_any(
        text,
        [
            "startup",
            "start-up",
            "spin-off",
            "spinoff",
            "pmi",
            "sme",
            "impresa innovativa",
            "micro e piccole imprese",
        ],
    ):
        applicant += 2.2

    if _has_any(
        text,
        [
            "università",
            "university",
            "research organisation",
            "research organization",
            "organismi di ricerca",
            "centri di ricerca",
        ],
    ):
        applicant += 1.3

    if _has_any(text, ["aziende agricole", "agricoltori", "imprenditori agricoli", "imprese agricole"]):
        applicant += 1.2

    # Se è solo per agricoltori, il fit per NGT è indiretto: serve azienda partner.
    if _has_any(text, ["aziende agricole", "agricoltori", "imprenditori agricoli"]) and not _has_any(
        text,
        [
            "startup",
            "pmi",
            "sme",
            "ricerca",
            "università",
            "innovation",
            "innovazione",
            "fornitori",
            "technology provider",
            "organismi di ricerca",
        ],
    ):
        applicant -= 0.8

    if opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_RND_AGRIFOOD_ENVIRONMENT",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_SPACE",
        "EU_RND_CONSORTIUM",
        "EU_DEEPTECH_SCALEUP",
        "SPACE_EXTREME_ENVIRONMENT",
    }:
        # Opportunità strategiche UE/ESA/ASI: buone per UniBo, NGT o partner,
        # ma spesso richiedono preparazione o consorzio.
        applicant += 0.8

    applicant = max(0.0, min(5.0, applicant))

    # ------------------------------------------------------------------
    # FEASIBILITY 0-5
    # ------------------------------------------------------------------
    feasibility = 2.5

    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        feasibility += 1.2

    elif opportunity_type in {
        "REGIONAL_INVESTMENT_CROP",
        "REGIONAL_INVESTMENT_PROCESSING",
        "REGIONAL_INVESTMENT_ENVIRONMENT",
        "REGIONAL_INVESTMENT",
    }:
        feasibility += 0.5

    elif opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_RND_AGRIFOOD_ENVIRONMENT",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_SPACE",
        "EU_RND_CONSORTIUM",
    }:
        feasibility -= 0.8

    elif opportunity_type == "EU_DEEPTECH_SCALEUP":
        # EIC/Eureka/scale-up sono strategici ma competitivi.
        feasibility -= 0.4

    elif opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        # ESA/ASI sono meno immediate di una call startup nazionale,
        # ma alcune sono open call/pilot abbastanza praticabili.
        feasibility -= 0.2

    if _has_any(text, ["consortium", "consorzio", "partenariato europeo", "multi-actor"]):
        feasibility -= 0.7

    if opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
        "REGIONAL_PROMOTION",
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
    }:
        feasibility -= 0.4

    days_left = _days_to_deadline(call)

    if (call.deadline_date or "").lower() in {"sportello_aperto", "open"}:
        feasibility += 0.7
    elif days_left is not None:
        if days_left < 0:
            feasibility = 0.0
        elif days_left <= 30:
            feasibility -= 0.8
        elif days_left <= 90:
            feasibility += 0.1
        elif days_left <= 180:
            feasibility += 0.5

    feasibility = max(0.0, min(5.0, feasibility))

    # ------------------------------------------------------------------
    # STRATEGIC VALUE 0-5
    # ------------------------------------------------------------------
    strategic = 0.0

    if any(t.lower() in text for t in project_goals):
        strategic += 1.2

    if nex_group_matches >= 4:
        strategic += 3.2
    elif nex_group_matches == 3:
        strategic += 2.6
    elif nex_group_matches == 2:
        strategic += 1.8
    elif nex_group_matches == 1:
        strategic += 0.9

    if opportunity_type == "REGIONAL_INVESTMENT_CROP":
        strategic += 1.2

    elif opportunity_type == "REGIONAL_INVESTMENT_PROCESSING":
        strategic += 0.7

    elif opportunity_type == "REGIONAL_INVESTMENT_ENVIRONMENT":
        strategic += 0.8

    elif opportunity_type == "EU_RND_AGRIFOOD_DIGITAL":
        strategic += 1.8

    elif opportunity_type == "EU_RND_AGRIFOOD_ENVIRONMENT":
        strategic += 1.2

    elif opportunity_type in {"EU_SPACE", "EU_RND_DIGITAL_INDUSTRY_SPACE"}:
        strategic += 2.0

    elif opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        # Traiettoria strategica: ambienti estremi, spazio, ESA/ASI, space-enabled agritech.
        strategic += 2.2

    elif opportunity_type == "EU_DEEPTECH_SCALEUP":
        strategic += 2.0

    elif opportunity_type in {"REGIONAL_DEMONSTRATION", "REGIONAL_COOPERATION"}:
        strategic += 0.5

    if opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
        "REGIONAL_PROMOTION",
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
        "TRAINING_COMMUNICATION",
        "MARKETING_PROMOTION",
    }:
        strategic -= 1.2

    if _has_any(text, hard_negative):
        strategic -= 3.0

    strategic = max(0.0, min(5.0, strategic))

    # ------------------------------------------------------------------
    # TIMING 0-5
    # ------------------------------------------------------------------
    timing = 2.5

    if (call.deadline_date or "").lower() == "sportello_aperto":
        timing = 4.0
    elif days_left is None:
        timing = 2.5
    elif days_left < 0:
        timing = 0.0
    elif days_left <= 30:
        timing = 2.0
    elif days_left <= 90:
        timing = 4.0
    elif days_left <= 180:
        timing = 4.5
    else:
        timing = 3.0

    # ------------------------------------------------------------------
    # FINAL WEIGHTED SCORE 0-10
    # ------------------------------------------------------------------
    weighted_0_5 = (
        technical * 0.28
        + business * 0.24
        + applicant * 0.16
        + feasibility * 0.14
        + strategic * 0.14
        + timing * 0.04
    )

    final_score = weighted_0_5 * 2

    # ------------------------------------------------------------------
    # CALIBRATION
    # ------------------------------------------------------------------
    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        # Boost business, ma meno aggressivo: evita che call startup generiche
        # superino opportunità davvero verticali su NEX.
        final_score += 0.5

    if opportunity_type == "REGIONAL_INVESTMENT_CROP":
        final_score += 0.6

    if opportunity_type == "REGIONAL_INVESTMENT_PROCESSING":
        final_score += 0.2

    if opportunity_type == "REGIONAL_INVESTMENT_ENVIRONMENT":
        final_score += 0.3

    if opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_SPACE",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_DEEPTECH_SCALEUP",
    }:
        final_score += 0.6

    if opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        final_score += 0.5

    if opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
        "REGIONAL_PROMOTION",
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
        "TRAINING_COMMUNICATION",
        "MARKETING_PROMOTION",
    }:
        final_score -= 1.0

    # Le watchlist sono utili come radar strategico, ma non sono call operative.
    # Evitiamo che superino bandi reali già aperti/candidabili.
    if is_watchlist:
        final_score = min(final_score, 6.4)

    # Evita che call startup generiche risultino troppo alte se non hanno
    # fit tecnico/strategico reale con NEX.
    if _is_generic_startup_opportunity(opportunity_type, technical, strategic, text):
        final_score = min(final_score, 5.9)

    # Se è startup funding ma ha basso fit tecnico e strategico, resta monitorabile
    # ma non deve diventare prioritaria.
    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    } and technical < 1.0 and strategic < 1.5:
        final_score = min(final_score, 6.0)

    final_score = round(max(0.0, min(10.0, final_score)), 1)

    return {
        "opportunity_type": opportunity_type,
        "technical_fit": round(technical, 1),
        "business_fit": round(business, 1),
        "applicant_fit": round(applicant, 1),
        "feasibility": round(feasibility, 1),
        "strategic_value": round(strategic, 1),
        "timing_score": round(timing, 1),
        "nex_core_matches": nex_group_matches,
        "final_score": final_score,
    }