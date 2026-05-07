from __future__ import annotations

from funding_agent.models import FundingCall
from funding_agent.classifiers.opportunity_type import classify_opportunity_type


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


def _add_unique(reasons: list[str], reason: str) -> None:
    if reason and reason not in reasons:
        reasons.append(reason)


def build_why_relevant(call: FundingCall) -> list[str]:
    """
    Genera motivazioni leggibili e coerenti con il tipo di opportunità.

    Nota:
    - Non deve solo spiegare perché è interessante.
    - Deve anche spiegare quando NON è prioritario.
    """

    text = _text(call)
    title_text = _title_text(call)
    opportunity_type = classify_opportunity_type(call)

    call_id = (call.call_id or "").upper()
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # STARTUP / BUSINESS FUNDING
    # ------------------------------------------------------------------
    if opportunity_type in {
        "STARTUP_FUNDING",
        "NEW_COMPANY_FUNDING",
        "NATIONAL_BUSINESS_FUNDING",
    }:
        if opportunity_type == "STARTUP_FUNDING":
            _add_unique(reasons, "utile per startup innovative o spin-off")

        if opportunity_type == "NEW_COMPANY_FUNDING":
            _add_unique(reasons, "utile per nuova imprenditorialità e costituzione/crescita d'impresa")

        if _has_any(text, ["micro e piccole imprese", "micro e piccole imp", "pmi", "sme"]):
            _add_unique(reasons, "compatibile con micro, piccole imprese o PMI")

        if _has_any(text, ["tasso zero", "finanziamento agevolato"]):
            _add_unique(reasons, "include strumenti di finanza agevolata")

        if _has_any(text, ["fondo perduto", "contributo a fondo perduto"]):
            _add_unique(reasons, "può prevedere una componente a fondo perduto")

        if call.deadline_date == "sportello_aperto":
            _add_unique(reasons, "misura attiva a sportello, quindi pianificabile senza scadenza immediata")

        return reasons[:5]

    # ------------------------------------------------------------------
    # REGIONAL INVESTMENT - CROP / FARM
    # ------------------------------------------------------------------
    if opportunity_type == "REGIONAL_INVESTMENT_CROP":
        _add_unique(reasons, "bando agricolo produttivo potenzialmente utilizzabile da aziende pilota")

        if _has_any(text, ["investimenti", "impianti", "attrezzature", "macchine"]):
            _add_unique(reasons, "può finanziare investimenti, impianti o attrezzature aziendali")

        if _has_any(text, ["innovazione", "digitale", "agricoltura di precisione", "sensori", "irrigazione"]):
            _add_unique(reasons, "da verificare per possibili spese su tecnologie digitali, sensori o automazione")

        if _has_any(text, ["aziende agricole", "imprese agricole", "agricoltori"]):
            _add_unique(reasons, "fit indiretto: probabilmente richiede un'azienda agricola beneficiaria/partner")

        return reasons[:5]

    # ------------------------------------------------------------------
    # REGIONAL PROCESSING / COMMERCIALIZATION
    # ------------------------------------------------------------------
    if opportunity_type == "REGIONAL_INVESTMENT_PROCESSING":
        _add_unique(reasons, "centrato su trasformazione e commercializzazione, quindi non core per NEX")

        if _has_any(text, ["filiera", "commercializzazione", "trasformazione"]):
            _add_unique(reasons, "può essere utile solo se collegato a una filiera o azienda partner")

        if _has_any(text, ["serra", "greenhouse", "controlled environment", "cea"]):
            _add_unique(reasons, "possibile interesse indiretto se il progetto riguarda produzioni in serra o CEA")

        if _has_any(text, ["automazione", "digitale", "monitoraggio", "controllo qualità"]):
            _add_unique(reasons, "da verificare se ammette componenti di automazione o controllo di processo")

        return reasons[:5]

    # ------------------------------------------------------------------
    # REGIONAL ENVIRONMENT / RESOURCE EFFICIENCY
    # ------------------------------------------------------------------
    if opportunity_type == "REGIONAL_INVESTMENT_ENVIRONMENT":
        _add_unique(reasons, "potenziale fit indiretto su ambiente, clima o riduzione input")

        if _has_any(text, ["gas serra", "emissioni", "ammoniaca"]):
            _add_unique(reasons, "tema ambientale specifico: verificare se include tecnologie di monitoraggio o controllo")

        if _has_any(text, ["risparmio idrico", "irrigazione", "efficienza", "fertilizzanti"]):
            _add_unique(reasons, "possibile collegamento con efficienza idrica o riduzione input")

        return reasons[:5]

    # ------------------------------------------------------------------
    # LIVESTOCK / NON CORE
    # ------------------------------------------------------------------
    if opportunity_type in {
        "REGIONAL_INVESTMENT_LIVESTOCK",
        "REGIONAL_AGRI_ENVIRONMENT_LIVESTOCK",
    }:
        _add_unique(reasons, "non prioritario per NEX: bando centrato su zootecnia o benessere animale")
        _add_unique(reasons, "fit tecnico debole con coltivazione autonoma, serre, DSS e fertirrigazione")

        if _has_any(text, ["aziende agricole", "pmi", "micro e piccole imprese"]):
            _add_unique(reasons, "la compatibilità dei beneficiari non basta: il dominio applicativo è fuori focus")

        return reasons[:5]

    # ------------------------------------------------------------------
    # NON PRODUCTIVE / ENVIRONMENT
    # ------------------------------------------------------------------
    if opportunity_type == "REGIONAL_NON_PRODUCTIVE_ENVIRONMENT":
        _add_unique(reasons, "non prioritario: investimento non produttivo o ambientale")
        _add_unique(reasons, "fit debole con sviluppo prodotto, validazione tecnologica o industrializzazione NEX")
        return reasons[:5]

    # ------------------------------------------------------------------
    # TRAINING / CONSULTING / DEMO / PROMOTION
    # ------------------------------------------------------------------
    if opportunity_type == "REGIONAL_DEMONSTRATION":
        _add_unique(reasons, "azione dimostrativa: utile solo se permette demo tecnologiche in aziende/living lab")
        _add_unique(reasons, "non finanzia direttamente sviluppo prodotto o industrializzazione")
        return reasons[:5]

    if opportunity_type in {
        "REGIONAL_TRAINING",
        "REGIONAL_CONSULTING",
        "TRAINING_COMMUNICATION",
    }:
        _add_unique(reasons, "non prioritario: misura centrata su formazione, consulenza o trasferimento conoscenze")
        _add_unique(reasons, "utile solo come supporto indiretto, non per sviluppo tecnologico NEX")
        return reasons[:5]

    if opportunity_type in {
        "REGIONAL_PROMOTION",
        "MARKETING_PROMOTION",
    }:
        _add_unique(reasons, "non prioritario: misura centrata su promozione o prodotti di qualità")
        _add_unique(reasons, "fit molto debole con DSS, sensori, automazione e piattaforma NEX")
        return reasons[:5]

    # ------------------------------------------------------------------
    # EU / HORIZON / SPACE
    # ------------------------------------------------------------------
    if opportunity_type in {
        "EU_RND_AGRIFOOD_DIGITAL",
        "EU_RND_AGRIFOOD_ENVIRONMENT",
        "EU_RND_DIGITAL_INDUSTRY_SPACE",
        "EU_SPACE",
        "EU_DEEPTECH_SCALEUP",
        "EU_RND_CONSORTIUM",
    }:
        if opportunity_type == "EU_RND_AGRIFOOD_DIGITAL":
            _add_unique(reasons, "opportunità strategica UE su agrifood, dati, osservazioni ambientali o soluzioni digitali")

        elif opportunity_type == "EU_RND_AGRIFOOD_ENVIRONMENT":
            _add_unique(reasons, "opportunità strategica UE su agrifood, ambiente o sostenibilità")

        elif opportunity_type in {"EU_SPACE", "EU_RND_DIGITAL_INDUSTRY_SPACE"}:
            _add_unique(reasons, "potenzialmente rilevante per applicazioni NEX in spazio, digitale o ambienti estremi")

        elif opportunity_type == "EU_DEEPTECH_SCALEUP":
            _add_unique(reasons, "potenzialmente rilevante per scale-up deeptech o innovazione ad alto contenuto tecnologico")

        if _has_any(text, ["digital solutions", "data", "monitoring", "environmental observations", "sensors"]):
            _add_unique(reasons, "coerente con monitoraggio, dati, sensori o osservazioni ambientali")

        if _has_any(text, ["artificial intelligence", "ai", "machine learning", "decision support"]):
            _add_unique(reasons, "possibile collegamento con AI, DSS o sistemi decisionali")

        if _has_any(text, ["consortium", "consorzio", "multi-actor"]):
            _add_unique(reasons, "richiede probabilmente partenariato/consorzio: non è una quick win")

        return reasons[:5]

    # ------------------------------------------------------------------
    # SPACE / EXTREME ENVIRONMENTS GENERIC
    # ------------------------------------------------------------------
    if opportunity_type == "SPACE_EXTREME_ENVIRONMENT":
        _add_unique(reasons, "strategico per estendere NEX verso ambienti estremi o applicazioni spaziali")
        _add_unique(reasons, "utile soprattutto per ricerca, validazione avanzata e partnership")
        return reasons[:5]

    # ------------------------------------------------------------------
    # FALLBACK GENERICO
    # ------------------------------------------------------------------
    if _has_any(text, ["agricolt", "agriculture", "agritech"]):
        _add_unique(reasons, "potenzialmente utile in ambito agritech")

    if _has_any(text, ["digit", "artificial intelligence", "intelligenza artificiale", "innovazione"]):
        _add_unique(reasons, "possibile collegamento con innovazione o digitale")

    if _has_any(text, ["serra", "greenhouse", "controlled environment", "cea"]):
        _add_unique(reasons, "vicino ai temi CEA / serra")

    if _has_any(text, ["irrigazione", "irrigation", "fertirrig", "fertigation"]):
        _add_unique(reasons, "vicino ai temi irrigazione / fertirrigazione")

    if not reasons:
        _add_unique(reasons, "rilevanza da verificare manualmente")

    return reasons[:5]