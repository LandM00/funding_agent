import re
from typing import Dict, List

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class EUCallsAPICollector(BaseCollector):
    """
    Collector EU operativo e stabile.

    Invece di dipendere dal rendering JS del portale EU, usa call-level records
    affidabili per Horizon Europe Cluster 6 2026, con URL ufficiali al portale.
    """

    name = "eu_calls_api"

    BASE_CALL_URL = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
        "screen/opportunities/calls-for-proposals"
    )

    CALLS = [
        {
            "call_id": "HORIZON-CL6-2026-01-BIODIV",
            "title": "Horizon Europe Cluster 6 2026 - Biodiversity",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "topics": ["agriculture", "biodiversity", "environment"],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su biodiversità, ecosistemi, "
                "risorse naturali e transizione ambientale. Apertura 17 April 2026, "
                "deadline 17 September 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-01-CIRCBIO",
            "title": "Horizon Europe Cluster 6 2026 - Circular Bioeconomy",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "topics": ["agriculture", "bioeconomy", "environment"],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su bioeconomia circolare, "
                "risorse biologiche, sostenibilità e innovazione ambientale. "
                "Apertura 17 April 2026, deadline 17 September 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-01-ZEROPOLLUTION",
            "title": "Horizon Europe Cluster 6 2026 - Zero Pollution",
            "opening_date": "17 April 2026",
            "deadline_date": "17 September 2026",
            "topics": ["agriculture", "environment", "pollution"],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su zero pollution, sostenibilità "
                "ambientale, gestione delle risorse e riduzione degli impatti. "
                "Apertura 17 April 2026, deadline 17 September 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-04-GOVERNANCE",
            "title": "Horizon Europe Cluster 6 2026 - Governance, environmental observations and digital solutions",
            "opening_date": "25 August 2026",
            "deadline_date": "26 November 2026",
            "topics": [
                "agriculture",
                "governance",
                "data",
                "digital",
                "earth observation",
                "environment",
            ],
            "summary": (
                "Call Horizon Europe Cluster 6 2026 su governance, osservazioni "
                "ambientali, dati, digitalizzazione e soluzioni a supporto del Green Deal. "
                "Apertura 25 August 2026, deadline 26 November 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-01-BIODIV-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Biodiversity two-stage",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "topics": ["agriculture", "biodiversity", "environment"],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su biodiversità. "
                "First stage 16 April 2026, second stage 23 September 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-01-CIRCBIO-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Circular Bioeconomy two-stage",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "topics": ["agriculture", "bioeconomy", "environment"],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su bioeconomia circolare. "
                "First stage 16 April 2026, second stage 23 September 2026."
            ),
        },
        {
            "call_id": "HORIZON-CL6-2026-01-ZEROPOLLUTION-TWO-STAGE",
            "title": "Horizon Europe Cluster 6 2026 - Zero Pollution two-stage",
            "opening_date": "16 April 2026",
            "deadline_date": "23 September 2026",
            "topics": ["agriculture", "environment", "pollution"],
            "summary": (
                "Call two-stage Horizon Europe Cluster 6 2026 su zero pollution. "
                "First stage 16 April 2026, second stage 23 September 2026."
            ),
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
            program="Horizon Europe - Cluster 6",
            opening_date=item["opening_date"],
            deadline_date=item["deadline_date"],
            budget_total=None,
            funding_type="grant",
            record_type="call",
            eligible_entities=[
                "companies",
                "research organisations",
                "consortia",
            ],
            countries=["EU"],
            topics=item["topics"],
            raw_text=self._build_raw_text(item),
        )

    def _build_call_url(self, call_id: str) -> str:
        base_call_id = self._to_portal_call_identifier(call_id)

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

    def _to_portal_call_identifier(self, call_id: str) -> str:
        """
        Trasforma il nostro call_id operativo in callIdentifier del portale.
        Esempio:
        HORIZON-CL6-2026-01-CIRCBIO -> HORIZON-CL6-2026-01
        HORIZON-CL6-2026-04-GOVERNANCE -> HORIZON-CL6-2026-04
        """
        match = re.match(r"(HORIZON-CL6-2026-\d{2})", call_id)
        if match:
            return match.group(1)

        return call_id

    def _build_raw_text(self, item: dict) -> str:
        return "\n".join(
            [
                item["call_id"],
                item["title"],
                item["summary"],
                f"opening_date={item['opening_date']}",
                f"deadline_date={item['deadline_date']}",
                f"topics={', '.join(item['topics'])}",
            ]
        )