from funding_agent.models import FundingCall


def build_why_relevant(call: FundingCall) -> list[str]:
    text = " ".join(
        [
            call.title or "",
            call.summary or "",
            call.program or "",
            call.raw_text or "",
            " ".join(call.topics),
            " ".join(call.eligible_entities),
        ]
    ).lower()

    title = (call.title or "").lower()
    program = (call.program or "").lower()
    funding_type = (call.funding_type or "").lower()
    call_id = (call.call_id or "").upper()

    reasons = []

    # -------------------------
    # TARGET / BENEFICIARI
    # -------------------------
    if "startup innovative" in text:
        reasons.append("coerente con startup innovative")
    elif "startup" in text:
        reasons.append("rilevante per nuove imprese")

    if any(k in text for k in ["micro e piccole imprese", "micro e piccole imp", "pmi"]):
        reasons.append("utile per micro e piccole imprese")

    if "impresa innovativa" in text or "innovazione" in text:
        reasons.append("coerente con impresa innovativa")

    # Solo per ON
    if call_id == "INVITALIA-ON" or "oltre nuove imprese a tasso zero" in program or "oltre nuove imprese a tasso zero" in title:
        reasons.append("mirato a nuova imprenditorialità giovanile o femminile")

    # -------------------------
    # MECCANICA FINANZIARIA
    # -------------------------
    # Tasso zero: solo per ON o se davvero esplicito come misura principale
    if call_id == "INVITALIA-ON" or "oltre nuove imprese a tasso zero" in program or "oltre nuove imprese a tasso zero" in title:
        reasons.append("include finanziamento a tasso zero")
    elif "finanziamento agevolato" in funding_type or "finanziamento agevolato" in text:
        reasons.append("include finanza agevolata")

    # Fondo perduto: solo se esplicito davvero
    if "fondo perduto" in funding_type or "fondo perduto" in text:
        reasons.append("prevede contributo a fondo perduto")

    if call.deadline_date == "sportello_aperto":
        reasons.append("misura attiva a sportello")

    # -------------------------
    # COERENZA TEMATICA
    # -------------------------
    if any(k in text for k in ["agricolt", "agriculture", "agritech"]):
        reasons.append("potenzialmente utile in ambito agritech")

    if any(k in text for k in ["digit", "artificial intelligence", "intelligenza artificiale", "innovazione"]):
        reasons.append("coerente con innovazione e digitale")

    if any(k in text for k in ["serra", "greenhouse", "controlled environment", "cea"]):
        reasons.append("vicino ai temi CEA / serra")

    if any(k in text for k in ["irrigazione", "irrigation", "fertirrig", "fertigation"]):
        reasons.append("vicino ai temi irrigazione / fertirrigazione")

    # -------------------------
    # HUB
    # -------------------------
    if call.record_type == "hub":
        reasons.append("pagina indice da monitorare")

    # -------------------------
    # DEDUPLICA
    # -------------------------
    unique_reasons = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            unique_reasons.append(reason)
            seen.add(reason)

    return unique_reasons[:4]