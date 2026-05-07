import re
from typing import Dict, List

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class EUCallsAPICollector(BaseCollector):
    """
    Collector EU/Horizon stabile.

    Nota importante:
    - Non è ancora uno scraper dinamico del portale EU.
    - Usa una lista curata di call Horizon/EU strategiche per NEX.
    - Ogni record contiene raw_text ricco per permettere allo scoring di valutare meglio
      AI, DSS, sensori, CEA, irrigazione, monitoraggio, spazio e ambienti estremi.

    Vantaggio:
    - stabile, veloce, non dipende dal rendering JavaScript del portale EU.

    Limite:
    - le call vanno aggiornate manualmente quando escono nuovi topic rilevanti.
    """

    name = "eu_calls_api"

    BASE_CALL_URL = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
        "screen/opportunities/calls-for-proposals"
    )

    CALLS = [
        # ------------------------------------------------------------------
        # HORIZON EUROPE - CLUSTER 6 2026
        # ------------------------------------------------------------------
        {
            "call_id": "HORIZON-CL6-2026-04-GOVERNANCE",
            "title": "Horizon Europe Cluster 6 2026 - Governance, environmental observations and digital solutions",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "25 August 2026",
            "deadline_date": "26 November 2026",
            "funding_type": "grant / RIA-IA",
            "topics": [
                "agriculture",
                "digital agriculture",
                "environmental observations",
                "data",
                "digital solutions",
                "sensors",
                "monitoring",
                "AI",
                "DSS",
                "decision support",
                "precision agriculture",
                "resource efficiency",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
                "technology providers",
            ],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su governance, osservazioni ambientali, dati, "
                "digitalizzazione e soluzioni a supporto del Green Deal. Per NEX è potenzialmente "
                "strategica perché può collegarsi a digital agriculture, sistemi di monitoraggio, "
                "sensori, AI, DSS, decision support, crop monitoring, environmental observations, "
                "data platforms, farm management, resource efficiency e tecnologie digitali per la "
                "gestione colturale."
            ),
            "nex_relevance": (
                "Alta rilevanza strategica per NEX se i topic specifici includono digital farming, "
                "environmental monitoring, decision support systems, agricultural data, sensors, "
                "AI-based advisory systems, crop monitoring o piattaforme dati per agricoltura."
            ),
            "applicant_note": (
                "Probabile necessità di consorzio europeo. Buona candidabilità tramite Università, "
                "organismi di ricerca, aziende tech, SME e partner agricoli. Non è una quick win."
            ),
            "keywords": [
                "digital agriculture",
                "digital farming",
                "environmental observations",
                "earth observation",
                "agricultural data",
                "data spaces",
                "data platform",
                "sensors",
                "IoT",
                "AI",
                "artificial intelligence",
                "machine learning",
                "decision support system",
                "DSS",
                "crop monitoring",
                "farm management",
                "monitoring",
                "precision agriculture",
                "resource efficiency",
                "water saving",
                "fertilizer reduction",
                "climate adaptation",
                "greenhouse",
                "controlled environment agriculture",
                "CEA",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-ZEROPOLLUTION",
            "title": "Horizon Europe Cluster 6 2026 - Zero Pollution",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "funding_type": "grant / RIA-IA",
            "topics": [
                "agriculture",
                "environment",
                "pollution",
                "resource efficiency",
                "fertilizer reduction",
                "water quality",
                "monitoring",
                "sustainability",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
            ],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su zero pollution, sostenibilità ambientale, "
                "riduzione degli impatti, uso efficiente delle risorse, qualità dell'acqua, "
                "riduzione degli input e monitoraggio ambientale. Per NEX può essere interessante "
                "solo se i topic specifici finanziano tecnologie per riduzione fertilizzanti, "
                "ottimizzazione fertirrigazione, monitoraggio degli input, gestione dell'acqua "
                "o decision support per ridurre emissioni e contaminazione."
            ),
            "nex_relevance": (
                "Rilevanza media: collegamento possibile con fertirrigazione, riduzione input, "
                "water saving, fertilizer reduction, monitoring e DSS ambientale. Meno core se "
                "il topic è puramente ambientale o normativo."
            ),
            "applicant_note": (
                "Richiede probabilmente consorzio europeo. Più adatto a una candidatura Università + partner "
                "tecnologici/agricoli che a una candidatura diretta NGT."
            ),
            "keywords": [
                "zero pollution",
                "fertilizer reduction",
                "water saving",
                "water quality",
                "nutrient management",
                "fertigation",
                "irrigation",
                "environmental monitoring",
                "sensors",
                "decision support",
                "DSS",
                "resource efficiency",
                "sustainable agriculture",
                "precision agriculture",
                "crop monitoring",
                "climate adaptation",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-ZEROPOLLUTION-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Zero Pollution two-stage",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "funding_type": "grant / RIA two-stage",
            "topics": [
                "agriculture",
                "environment",
                "pollution",
                "resource efficiency",
                "fertilizer reduction",
                "water quality",
                "monitoring",
                "sustainability",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
            ],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su zero pollution. Possibile interesse "
                "per NEX solo se i topic specifici includono riduzione degli input, ottimizzazione "
                "della fertirrigazione, gestione sostenibile dell'acqua, sensoristica, DSS, "
                "monitoraggio colturale o decision support per ridurre l'impatto ambientale."
            ),
            "nex_relevance": (
                "Rilevanza media-bassa senza topic specifici. Da monitorare per eventuali topic su "
                "fertigation, irrigation, water saving, fertilizer reduction, sensors e DSS."
            ),
            "applicant_note": (
                "Schema two-stage: utile da monitorare, ma richiede preparazione consortile e topic molto coerente."
            ),
            "keywords": [
                "zero pollution",
                "fertilizer reduction",
                "fertigation",
                "irrigation",
                "water saving",
                "water quality",
                "resource efficiency",
                "environmental monitoring",
                "sensors",
                "DSS",
                "decision support",
                "precision agriculture",
                "sustainable agriculture",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-CIRCBIO",
            "title": "Horizon Europe Cluster 6 2026 - Circular Bioeconomy",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "funding_type": "grant / RIA-IA",
            "topics": [
                "agriculture",
                "bioeconomy",
                "circular bioeconomy",
                "sustainability",
                "resource efficiency",
                "food systems",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
                "food system actors",
            ],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su bioeconomia circolare, risorse biologiche, "
                "sostenibilità, food systems e innovazione ambientale. Per NEX il fit è indiretto: "
                "può essere utile se il topic riguarda efficienza delle risorse, sistemi produttivi "
                "circolari, riduzione input, gestione dati agricoli, digital farming o tecnologie "
                "per produzioni controllate."
            ),
            "nex_relevance": (
                "Rilevanza medio-bassa: interessante solo se emergono topic su CEA, resource efficiency, "
                "controlled production, data-driven agriculture o riduzione input."
            ),
            "applicant_note": (
                "Probabile consorzio europeo. Più adatto come opportunità strategica di ricerca che come quick win."
            ),
            "keywords": [
                "circular bioeconomy",
                "bioeconomy",
                "resource efficiency",
                "sustainable agriculture",
                "food systems",
                "digital agriculture",
                "controlled environment agriculture",
                "greenhouse",
                "CEA",
                "input reduction",
                "fertilizer reduction",
                "water saving",
                "monitoring",
                "DSS",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-CIRCBIO-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Circular Bioeconomy two-stage",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "funding_type": "grant / RIA two-stage",
            "topics": [
                "agriculture",
                "bioeconomy",
                "circular bioeconomy",
                "sustainability",
                "resource efficiency",
                "food systems",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
                "food system actors",
            ],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su bioeconomia circolare. Per NEX è "
                "da monitorare solo se i topic specifici riguardano sistemi agricoli digitali, "
                "efficienza delle risorse, CEA, riduzione input, water saving, monitoring o DSS."
            ),
            "nex_relevance": (
                "Rilevanza medio-bassa, dipendente dal topic specifico. Possibile interesse per progetti "
                "di resource efficiency, CEA e sistemi digitali di gestione colturale."
            ),
            "applicant_note": (
                "Richiede consorzio europeo e allineamento forte al topic specifico."
            ),
            "keywords": [
                "circular bioeconomy",
                "bioeconomy",
                "resource efficiency",
                "digital agriculture",
                "greenhouse",
                "controlled environment agriculture",
                "CEA",
                "water saving",
                "fertilizer reduction",
                "monitoring",
                "DSS",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-BIODIV",
            "title": "Horizon Europe Cluster 6 2026 - Biodiversity",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "funding_type": "grant / RIA-IA",
            "topics": [
                "agriculture",
                "biodiversity",
                "ecosystems",
                "environment",
                "monitoring",
                "sustainability",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
            ],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su biodiversità, ecosistemi, risorse naturali "
                "e transizione ambientale. Per NEX il fit è generalmente basso, salvo topic su "
                "monitoraggio ambientale, sensoristica, data platforms, agricultural monitoring "
                "o gestione sostenibile dei sistemi colturali."
            ),
            "nex_relevance": (
                "Rilevanza bassa o indiretta: interessante solo se include monitoring, sensors, "
                "environmental observations, data e agricoltura digitale."
            ),
            "applicant_note": (
                "Più adatto a ricerca ambientale/Università che a sviluppo prodotto NEX."
            ),
            "keywords": [
                "biodiversity",
                "ecosystems",
                "environmental monitoring",
                "sensors",
                "data",
                "environmental observations",
                "agricultural monitoring",
                "sustainable agriculture",
            ],
        },
        {
            "call_id": "HORIZON-CL6-2026-01-BIODIV-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Biodiversity two-stage",
            "program": "Horizon Europe - Cluster 6",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "funding_type": "grant / RIA two-stage",
            "topics": [
                "agriculture",
                "biodiversity",
                "ecosystems",
                "environment",
                "monitoring",
                "sustainability",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "farms",
            ],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su biodiversità. Per NEX è una "
                "opportunità generalmente indiretta, da considerare solo se emergono topic su "
                "monitoraggio, sensori, data-driven agriculture o environmental observations."
            ),
            "nex_relevance": (
                "Rilevanza bassa o indiretta. Possibile interesse solo per componenti di monitoraggio "
                "ambientale o sensoristica."
            ),
            "applicant_note": (
                "Richiede consorzio europeo e forte fit ambientale."
            ),
            "keywords": [
                "biodiversity",
                "ecosystems",
                "environmental monitoring",
                "sensors",
                "data",
                "environmental observations",
                "agricultural monitoring",
            ],
        },
        # ------------------------------------------------------------------
        # HORIZON / SPACE / EXTREME ENVIRONMENTS - STRATEGIC WATCHLIST
        # ------------------------------------------------------------------
        {
            "call_id": "HORIZON-CL4-2026-SPACE-WATCH",
            "title": "Horizon Europe Cluster 4 2026 - Space and extreme environments watchlist",
            "program": "Horizon Europe - Cluster 4",
            "opening_date": "2026",
            "deadline_date": "open",
            "funding_type": "grant / strategic watchlist",
            "topics": [
                "space",
                "extreme environments",
                "controlled environment",
                "bioregenerative systems",
                "autonomous systems",
                "AI",
                "sensors",
                "monitoring",
            ],
            "eligible_entities": [
                "companies",
                "SMEs",
                "research organisations",
                "universities",
                "consortia",
                "space actors",
            ],
            "summary": (
                "Record strategico di monitoraggio per call Horizon Cluster 4 collegate a spazio, "
                "sistemi autonomi, ambienti estremi, space farming, bioregenerative systems, "
                "controlled life support, sensoristica, AI, monitoraggio e automazione. "
                "Per NEX è rilevante come traiettoria di lungo periodo per serre autonome, "
                "CEA, coltivazione in ambienti estremi e validazione di sistemi autonomi."
            ),
            "nex_relevance": (
                "Alta rilevanza strategica, ma non necessariamente quick win. Da usare per intercettare "
                "topic su space farming, controlled environment, autonomous cultivation, sensors, "
                "AI, DSS e bioregenerative life support systems."
            ),
            "applicant_note": (
                "Probabile necessità di partner spaziali, Università, consorzio europeo e forte narrativa "
                "su ambienti estremi."
            ),
            "keywords": [
                "space",
                "spazio",
                "space farming",
                "extreme environment",
                "ambienti estremi",
                "controlled environment",
                "controlled environment agriculture",
                "CEA",
                "greenhouse",
                "bioregenerative systems",
                "controlled life support",
                "lunar",
                "mars",
                "autonomous cultivation",
                "autonomous systems",
                "sensors",
                "AI",
                "DSS",
                "monitoring",
                "robotics",
                "resource efficiency",
                "water recycling",
            ],
        },
        {
            "call_id": "EIC-2026-AGRITECH-DEEPTECH-WATCH",
            "title": "EIC 2026 - Agritech deeptech and autonomous cultivation watchlist",
            "program": "EIC / Horizon Europe",
            "opening_date": "2026",
            "deadline_date": "open",
            "funding_type": "grant / accelerator / transition watchlist",
            "topics": [
                "startup",
                "deeptech",
                "agritech",
                "AI",
                "robotics",
                "sensors",
                "automation",
                "DSS",
                "scale-up",
                "commercialisation",
            ],
            "eligible_entities": [
                "startups",
                "SMEs",
                "spin-offs",
                "research organisations",
                "companies",
            ],
            "summary": (
                "Record strategico di monitoraggio per opportunità EIC Accelerator, EIC Transition "
                "o EIC Pathfinder collegate ad agritech deeptech, AI, sensoristica, automazione, "
                "robotica, DSS, edge computing, sistemi autonomi e commercializzazione di tecnologie "
                "innovative. Per NEX può essere molto rilevante in fase di startup/spin-off e scale-up."
            ),
            "nex_relevance": (
                "Alta rilevanza per Neura GrowTech se NEX viene posizionato come deeptech agritech "
                "con autonomia decisionale, AI/DSS, sensori, edge computing e potenziale di mercato europeo."
            ),
            "applicant_note": (
                "Potenziale candidatura diretta come startup/PMI innovativa o tramite percorso di trasferimento "
                "tecnologico. Richiede forte business case, TRL, IP e validazione."
            ),
            "keywords": [
                "EIC",
                "EIC Accelerator",
                "EIC Transition",
                "EIC Pathfinder",
                "startup",
                "SME",
                "spin-off",
                "deeptech",
                "agritech",
                "AI",
                "artificial intelligence",
                "DSS",
                "decision support system",
                "sensors",
                "IoT",
                "edge computing",
                "automation",
                "autonomous systems",
                "robotics",
                "greenhouse",
                "controlled environment agriculture",
                "CEA",
                "scale-up",
                "commercialisation",
                "market uptake",
                "industrialization",
            ],
        },
        {
            "call_id": "EUROSTARS-2026-AGRITECH-SME-WATCH",
            "title": "Eurostars 2026 - Agritech SME innovation watchlist",
            "program": "Eurostars / Eureka",
            "opening_date": "2026",
            "deadline_date": "open",
            "funding_type": "grant / SME collaborative R&D watchlist",
            "topics": [
                "SME",
                "startup",
                "agritech",
                "digital agriculture",
                "sensors",
                "AI",
                "DSS",
                "automation",
                "international collaboration",
            ],
            "eligible_entities": [
                "SMEs",
                "startups",
                "companies",
                "research organisations",
                "international consortia",
            ],
            "summary": (
                "Record strategico di monitoraggio per bandi Eurostars/Eureka su innovazione SME "
                "e collaborazione internazionale. Per NEX è rilevante se emergono call o partnership "
                "su agritech, digital agriculture, AI, sensoristica, DSS, automazione, CEA, "
                "irrigazione/fertirrigazione e sviluppo prototipale con partner industriali."
            ),
            "nex_relevance": (
                "Rilevanza medio-alta per sviluppo con partner internazionali e SME. Potenzialmente "
                "più accessibile di Horizon classico, ma richiede consorzio internazionale."
            ),
            "applicant_note": (
                "Interessante per Neura GrowTech come SME/startup con partner esteri. Da monitorare quando "
                "NGT avrà soggetto giuridico e partner industriali."
            ),
            "keywords": [
                "Eurostars",
                "Eureka",
                "SME",
                "startup",
                "international collaboration",
                "agritech",
                "digital agriculture",
                "AI",
                "DSS",
                "sensors",
                "IoT",
                "automation",
                "controlled environment agriculture",
                "greenhouse",
                "CEA",
                "irrigation",
                "fertigation",
                "prototype",
                "market-oriented R&D",
            ],
        },
    ]

    def fetch(self) -> List[FundingCall]:
        calls: Dict[str, FundingCall] = {}

        for item in self.CALLS:
            call = self._build_call(item)
            calls[call.call_id] = call

        return list(calls.values())

    def _build_call(self, item: dict) -> FundingCall:
        call_id = item["call_id"]

        return FundingCall(
            source="EU Funding & Tenders",
            source_url=self._build_call_url(call_id),
            call_id=call_id,
            title=item["title"],
            summary=item["summary"],
            program=item.get("program", "Horizon Europe"),
            opening_date=item.get("opening_date"),
            deadline_date=item.get("deadline_date"),
            budget_total=None,
            funding_type=item.get("funding_type", "grant"),
            record_type="call",
            eligible_entities=item.get(
                "eligible_entities",
                [
                    "companies",
                    "research organisations",
                    "consortia",
                ],
            ),
            countries=["EU"],
            topics=item.get("topics", []),
            raw_text=self._build_raw_text(item),
        )

    def _build_call_url(self, call_id: str) -> str:
        # Per record watchlist non sempre esiste un callIdentifier specifico.
        # In questi casi mandiamo comunque alla pagina ufficiale del portale,
        # filtrata il più possibile sul programma.
        base_call_id = self._to_portal_call_identifier(call_id)

        if base_call_id:
            return (
                f"{self.BASE_CALL_URL}"
                f"?callIdentifier={base_call_id}"
                f"&frameworkProgramme=43108390"
                f"&isExactMatch=true"
                f"&order=DESC"
                f"&pageNumber=1"
                f"&pageSize=50"
                f"&sortBy=startDate"
                f"&status=31094501%2C31094502%2C31094503"
            )

        return (
            f"{self.BASE_CALL_URL}"
            f"?frameworkProgramme=43108390"
            f"&order=DESC"
            f"&pageNumber=1"
            f"&pageSize=50"
            f"&sortBy=startDate"
            f"&status=31094501%2C31094502%2C31094503"
        )

    def _to_portal_call_identifier(self, call_id: str) -> str | None:
        """
        Trasforma il nostro call_id operativo in callIdentifier del portale.

        Esempio:
        HORIZON-CL6-2026-01-CIRCBIO -> HORIZON-CL6-2026-01
        HORIZON-CL6-2026-04-GOVERNANCE -> HORIZON-CL6-2026-04

        Per watchlist generiche, ritorna None.
        """
        match = re.match(r"(HORIZON-CL\d-2026-\d{2})", call_id)
        if match:
            return match.group(1)

        return None

    def _build_raw_text(self, item: dict) -> str:
        fields = [
            item.get("call_id", ""),
            item.get("title", ""),
            item.get("program", ""),
            item.get("summary", ""),
            item.get("nex_relevance", ""),
            item.get("applicant_note", ""),
            f"opening_date={item.get('opening_date', '')}",
            f"deadline_date={item.get('deadline_date', '')}",
            f"funding_type={item.get('funding_type', '')}",
            f"topics={', '.join(item.get('topics', []))}",
            f"eligible_entities={', '.join(item.get('eligible_entities', []))}",
            f"keywords={', '.join(item.get('keywords', []))}",
        ]

        return "\n".join(str(field) for field in fields if field)