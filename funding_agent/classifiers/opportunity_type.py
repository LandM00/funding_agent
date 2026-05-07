from __future__ import annotations

import re

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


def _title_text(call: FundingCall) -> str:
    """
    Testo più affidabile per capire la natura della call.
    Usiamo soprattutto titolo, call_id e programma per evitare che raw_text,
    menu laterali, link correlati o footer sporchino la classificazione.
    """
    return " ".join(
        [
            call.title or "",
            call.call_id or "",
            call.program or "",
        ]
    ).lower()


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(k.lower() in text for k in keywords)


def _has_space_domain(text: str, call_id: str, program: str) -> bool:
    """
    Riconosce il dominio 'space' evitando falsi positivi come:
    - data space
    - data spaces
    - agricultural data space
    - common european data space

    Questi termini riguardano infrastrutture dati, non lo spazio.
    """
    content = f"{text} {call_id} {program}".lower()

    false_positive_patterns = [
        "data space",
        "data spaces",
        "european data space",
        "european data spaces",
        "agricultural data space",
        "agricultural data spaces",
        "common european data space",
        "common european data spaces",
    ]

    cleaned = content
    for fp in false_positive_patterns:
        cleaned = cleaned.replace(fp, "")

    space_patterns = [
        r"\bspace\b",
        r"\bspazio\b",
        r"\besa\b",
        r"\bspaceport\b",
        r"\blunar\b",
        r"\bmoon\b",
        r"\bmars\b",
        r"\borbit\b",
        r"\bsatellite\b",
        r"\bcopernicus\b",
        r"\bspace farming\b",
        r"\bbioregenerative\b",
        r"\bcontrolled life support\b",
    ]

    return any(re.search(pattern, cleaned) for pattern in space_patterns)


def classify_opportunity_type(call: FundingCall) -> str:
    text = _text(call)
    title_text = _title_text(call)

    source = (call.source or "").lower()
    program = (call.program or "").lower()
    call_id = (call.call_id or "").upper()

    if call.record_type == "hub":
        return "HUB"

    if call.record_type == "support_doc":
        return "SUPPORT_DOC"

    # ------------------------------------------------------------------
    # WATCHLIST STRATEGICHE
    # ------------------------------------------------------------------
    # Questi record sono radar strategici, non call operative specifiche.
    # Li classifichiamo prima degli altri blocchi per evitare falsi match.
    if "WATCH" in call_id or "watchlist" in text:
        if "EIC" in call_id:
            return "EU_DEEPTECH_SCALEUP"

        if "EUROSTARS" in call_id:
            return "EU_RND_CONSORTIUM"

        if "SPACE" in call_id or _has_space_domain(text, call_id, program):
            return "EU_SPACE"

        return "EU_RND_CONSORTIUM"

    # ------------------------------------------------------------------
    # INVITALIA / NATIONAL BUSINESS FUNDING
    # ------------------------------------------------------------------
    if "invitalia" in source:
        if _has_any(
            text,
            [
                "smart&start",
                "smart start",
                "startup innovative",
                "startup innovativa",
            ],
        ):
            return "STARTUP_FUNDING"

        if _has_any(
            text,
            [
                "oltre nuove imprese",
                "nuove imprese a tasso zero",
                "tasso zero",
            ],
        ):
            return "NEW_COMPANY_FUNDING"

        if _has_any(text, ["startup", "start-up", "impresa innovativa"]):
            return "STARTUP_FUNDING"

        return "NATIONAL_BUSINESS_FUNDING"

    # ------------------------------------------------------------------
    # REGIONE EMILIA-ROMAGNA / CSR 2023-2027
    # ------------------------------------------------------------------
    if "regione emilia-romagna" in source:
        # SRD - investimenti
        if "SRD" in call_id:
            # Prima casi specifici da call_id/titolo, non dal raw_text completo.
            if "SRD13" in call_id or _has_any(
                title_text,
                [
                    "trasformazione",
                    "commercializzazione",
                    "prodotti agricoli",
                ],
            ):
                return "REGIONAL_INVESTMENT_PROCESSING"

            if "SRD01" in call_id or _has_any(
                title_text,
                [
                    "competitività",
                    "investimenti produttivi agricoli per la competitività",
                ],
            ):
                return "REGIONAL_INVESTMENT_CROP"

            if "SRD02" in call_id and _has_any(
                title_text,
                [
                    "benessere animale",
                    "zootecnia",
                    "allevamenti",
                    "allevatori",
                    "ammoniaca",
                ],
            ):
                return "REGIONAL_INVESTMENT_LIVESTOCK"

            if "SRD04" in call_id or "SRD09" in call_id or _has_any(
                title_text,
                [
                    "non produttivi",
                    "finalità ambientale",
                    "biodiversità",
                    "fauna selvatica",
                    "paesaggio rurale",
                    "aree rurali",
                ],
            ):
                return "REGIONAL_NON_PRODUCTIVE_ENVIRONMENT"

            # Se SRD02 non è chiaramente livestock, trattiamolo come ambiente/clima.
            if "SRD02" in call_id or _has_any(
                title_text,
                [
                    "ambiente",
                    "clima",
                    "gas serra",
                    "riduzione",
                ],
            ):
                return "REGIONAL_INVESTMENT_ENVIRONMENT"

            return "REGIONAL_INVESTMENT"

        # SRA - agro-clima-ambiente
        if "SRA" in call_id:
            if _has_any(
                title_text,
                [
                    "allevatori",
                    "zootecnia",
                    "benessere animale",
                    "agrobiodiversità",
                ],
            ):
                return "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK"

            return "REGIONAL_AGRI_ENVIRONMENT"

        # SRH - conoscenza, formazione, consulenza
        if "SRH" in call_id:
            if "SRH01" in call_id or _has_any(
                title_text,
                [
                    "consulenza",
                    "servizi di consulenza",
                ],
            ):
                return "REGIONAL_CONSULTING"

            if "SRH03" in call_id or _has_any(
                title_text,
                [
                    "formazione",
                    "informazione",
                    "corsi",
                ],
            ):
                return "REGIONAL_TRAINING"

            if "SRH05" in call_id or _has_any(
                title_text,
                [
                    "azioni dimostrative",
                    "dimostrative",
                    "demo",
                ],
            ):
                return "REGIONAL_DEMONSTRATION"

            return "REGIONAL_KNOWLEDGE_TRANSFER"

        # SRG - cooperazione / promozione
        if "SRG" in call_id:
            if "SRG10" in call_id or _has_any(
                title_text,
                [
                    "promozione",
                    "prodotti di qualità",
                    "qualità",
                ],
            ):
                return "REGIONAL_PROMOTION"

            return "REGIONAL_COOPERATION"

        return "REGIONAL_FUNDING"

    # ------------------------------------------------------------------
    # EU / HORIZON / EIC / EUROSTARS
    # ------------------------------------------------------------------
    if (
        "horizon europe" in program
        or "HORIZON" in call_id
        or "EIC" in call_id
        or "EUROSTARS" in call_id
        or "eureka" in program
    ):
        if "EIC" in call_id or _has_any(
            text,
            [
                "eic accelerator",
                "eic transition",
                "eic pathfinder",
                "deeptech",
                "deep tech",
            ],
        ):
            return "EU_DEEPTECH_SCALEUP"

        if "EUROSTARS" in call_id or "eurostars" in text or "eureka" in program:
            return "EU_RND_CONSORTIUM"

        # Attenzione: qui usiamo _has_space_domain() per evitare falsi positivi
        # come "data spaces", che non c'entrano con lo spazio.
        if "SPACE" in call_id or _has_space_domain(text, call_id, program):
            return "EU_SPACE"

        if "CL6" in call_id:
            if _has_any(
                text,
                [
                    "digital solutions",
                    "environmental observations",
                    "agricultural data",
                    "data platform",
                    "data spaces",
                    "monitoring",
                    "sensors",
                    "sensor",
                    "iot",
                    "artificial intelligence",
                    "machine learning",
                    "decision support",
                    "dss",
                    "digital agriculture",
                    "precision agriculture",
                    "crop monitoring",
                    "farm management",
                    "food systems",
                ],
            ):
                return "EU_RND_AGRIFOOD_DIGITAL"

            return "EU_RND_AGRIFOOD_ENVIRONMENT"

        if "CL4" in call_id:
            if _has_space_domain(text, call_id, program):
                return "EU_SPACE"

            return "EU_RND_DIGITAL_INDUSTRY_SPACE"

        return "EU_RND_CONSORTIUM"

    # ------------------------------------------------------------------
    # SPACE / EXTREME ENVIRONMENTS OUTSIDE HORIZON
    # ------------------------------------------------------------------
    if _has_space_domain(text, call_id, program) or _has_any(
        text,
        [
            "extreme environment",
            "ambienti estremi",
        ],
    ):
        return "SPACE_EXTREME_ENVIRONMENT"

    # ------------------------------------------------------------------
    # GENERIC FALLBACK
    # ------------------------------------------------------------------
    if _has_any(text, ["formazione", "informazione", "training"]):
        return "TRAINING_COMMUNICATION"

    if _has_any(text, ["promozione", "marketing"]):
        return "MARKETING_PROMOTION"

    if _has_any(text, ["startup", "start-up", "spin-off", "spinoff"]):
        return "STARTUP_FUNDING"

    return "OTHER_FUNDING"