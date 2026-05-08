from __future__ import annotations

import re
from typing import List

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class SpaceOpportunitiesCollector(BaseCollector):
    """
    Collector strategico per opportunità spazio / ambienti estremi.

    Obiettivo:
    - monitorare fonti ESA / ASI / ESA BIC rilevanti per applicazioni space-enabled;
    - intercettare opportunità utili per una traiettoria NEX in ambienti estremi,
      space farming, remote monitoring, autonomia, sensori e sistemi decisionali;
    - evitare dipendenza da pagine troppo dinamiche: se il parsing non trova dettagli,
      mantiene comunque una call strategica "radar" con testo fallback.
    """

    name = "space_opportunities"

    SOURCES = [
        {
            "source": "ESA Business Applications",
            "source_url": "https://business.esa.int/funding",
            "program": "ESA Business Applications",
            "call_id": "ESA-BASS-FUNDING",
            "title": "ESA Business Applications - Funding opportunities",
            "fallback_summary": (
                "ESA Business Applications funding opportunities for space-enabled "
                "commercial services, feasibility studies, demonstration projects and "
                "thematic calls. Potentially relevant for NEX applications involving "
                "remote monitoring, autonomous crop management, space-enabled agriculture, "
                "extreme environments and decision support systems."
            ),
            "funding_type": "ESA funding / commercial applications",
        },
        {
            "source": "ESA Business Applications",
            "source_url": "https://business.esa.int/OpenCfPlist",
            "program": "ESA Business Applications - Open Calls",
            "call_id": "ESA-BASS-OPEN-CALLS",
            "title": "ESA Business Applications - Open calls for proposals",
            "fallback_summary": (
                "Live ESA Business Applications open calls and thematic opportunities. "
                "Useful as a radar for space-enabled services and commercial pilots "
                "potentially connected to agriculture, environment, monitoring, resilience "
                "and autonomous systems."
            ),
            "funding_type": "ESA open call",
        },
        {
            "source": "ESA Business Applications",
            "source_url": "https://business.esa.int/funding/open-call-for-proposals-proof-concept-studies-and-pilot-projects",
            "program": "ESA Business Applications - Proof of Concept / Pilot Projects",
            "call_id": "ESA-BASS-POC-PILOT-OPEN-CALL",
            "title": "ESA Business Applications - Proof-of-concept studies and pilot projects",
            "fallback_summary": (
                "ESA open call for proof-of-concept studies and pilot projects. "
                "Potentially relevant for validating NEX-inspired services in space-enabled "
                "agriculture, environmental monitoring, controlled environment agriculture, "
                "remote sensing integration or autonomous decision-support workflows."
            ),
            "funding_type": "ESA proof-of-concept / pilot funding",
        },
        {
            "source": "ESA OSIP",
            "source_url": "https://ideas.esa.int/",
            "program": "ESA Open Space Innovation Platform",
            "call_id": "ESA-OSIP",
            "title": "ESA OSIP - Open Space Innovation Platform",
            "fallback_summary": (
                "ESA Open Space Innovation Platform for innovative ideas and campaigns "
                "related to space technologies, exploration, sustainability, autonomy, "
                "extreme environments and future space systems. Strategic radar source "
                "for NEX space/extreme-environment applications."
            ),
            "funding_type": "ESA innovation opportunity",
        },
        {
            "source": "ESA BIC Italy",
            "source_url": "https://www.esabic-italy.it/",
            "program": "ESA BIC Italy",
            "call_id": "ESA-BIC-ITALY",
            "title": "ESA BIC Italy - Business incubation opportunities",
            "fallback_summary": (
                "ESA Business Incubation Centre Italy opportunities for startups using "
                "space technologies, satellite data or space-enabled services. Potentially "
                "relevant if NEURA GrowTech develops a space-enabled agritech or extreme "
                "environment application line."
            ),
            "funding_type": "space business incubation",
        },
        {
            "source": "ESA BIC Milan",
            "source_url": "https://www.esabic-milan.it/",
            "program": "ESA BIC Milan",
            "call_id": "ESA-BIC-MILAN",
            "title": "ESA BIC Milan - Space startup incubation",
            "fallback_summary": (
                "ESA BIC Milan incubation opportunities for startups with space-enabled "
                "technologies and services. Useful for monitoring potential incubation "
                "routes for NEURA GrowTech space/agritech positioning."
            ),
            "funding_type": "space business incubation",
        },
        {
            "source": "ESA BIC Turin",
            "source_url": "https://www.esabic-turin.it/",
            "program": "ESA BIC Turin",
            "call_id": "ESA-BIC-TURIN",
            "title": "ESA BIC Turin - Space startup incubation",
            "fallback_summary": (
                "ESA BIC Turin incubation opportunities for startups developing space-related "
                "products, services or applications. Useful as a radar for startup support "
                "in the Italian space ecosystem."
            ),
            "funding_type": "space business incubation",
        },
        {
            "source": "ASI",
            "source_url": "https://www.asi.it/portale-della-ricerca-spaziale/iniziative-in-corso-per-le-start-up-spaziali/",
            "program": "ASI - Startup spaziali",
            "call_id": "ASI-STARTUP-SPAZIALI",
            "title": "ASI - Iniziative in corso per le start-up spaziali",
            "fallback_summary": (
                "Italian Space Agency initiatives for space startups. Strategic source "
                "for monitoring opportunities connected to space economy, startup support, "
                "technology transfer and space-enabled innovation."
            ),
            "funding_type": "space startup opportunity",
        },
        {
            "source": "ASI",
            "source_url": "https://www.asi.it/bandi_e_concorsi/",
            "program": "ASI - Bandi e concorsi",
            "call_id": "ASI-BANDI-CONCORSI",
            "title": "ASI - Bandi e concorsi",
            "fallback_summary": (
                "ASI official page for calls and opportunities. Useful as a radar source "
                "for space economy, research, technology development, innovation and "
                "potential space-enabled agritech opportunities."
            ),
            "funding_type": "space call / tender",
        },
    ]

    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            }
        )

    def fetch(self) -> List[FundingCall]:
        calls = []

        for item in self.SOURCES:
            html = self._safe_get(item["source_url"])
            text = ""

            if html:
                soup = BeautifulSoup(html, "html.parser")
                text = self._extract_main_text(soup)

            if not text or len(text) < 120:
                text = item["fallback_summary"]

            combined_text = self._clean_text(
                " ".join(
                    [
                        item["title"],
                        item["program"],
                        item["fallback_summary"],
                        text,
                    ]
                )
            )

            call = FundingCall(
                source=item["source"],
                source_url=item["source_url"],
                call_id=item["call_id"],
                title=item["title"],
                summary=self._build_summary(combined_text),
                program=item["program"],
                opening_date=self._extract_opening(combined_text),
                deadline_date=self._extract_deadline(combined_text),
                budget_total=self._extract_budget(combined_text),
                funding_type=item["funding_type"],
                record_type="call",
                eligible_entities=self._infer_eligible_entities(combined_text),
                countries=self._infer_countries(item["source"], combined_text),
                topics=self._infer_topics(combined_text),
                raw_text=combined_text,
            )

            calls.append(call)

        return self._deduplicate(calls)

    def _safe_get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[SpaceOpportunities] Errore su {url}: {e}")
            return None

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        selectors = [
            "main",
            "article",
            ".content",
            ".page-content",
            ".entry-content",
            ".container",
        ]

        candidates = []

        for selector in selectors:
            for node in soup.select(selector):
                text = self._clean_text(node.get_text(" ", strip=True))
                if len(text) > 200:
                    candidates.append(text)

        if candidates:
            return max(candidates, key=len)

        return self._clean_text(soup.get_text(" ", strip=True))

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _extract_deadline(self, text: str) -> str | None:
        lowered = text.lower()

        always_open_markers = [
            "always open",
            "open call",
            "open calls",
            "permanently open",
            "continuously open",
            "sempre aperto",
            "sportello",
        ]

        if any(marker in lowered for marker in always_open_markers):
            return "open"

        patterns = [
            r"deadline[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"deadline[:\s]+([A-Za-zÀ-ÿ]+\s+[0-9]{1,2},?\s+[0-9]{4})",
            r"closing date[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"closes[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"scadenza[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"entro\s+il\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_opening(self, text: str) -> str | None:
        patterns = [
            r"opening date[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"opens[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"apertura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_budget(self, text: str) -> float | None:
        lowered = text.lower()

        if "€" not in lowered and "eur" not in lowered:
            return None

        patterns = [
            r"€\s*([0-9]+(?:[.,][0-9]+)?)\s*million",
            r"eur\s*([0-9]+(?:[.,][0-9]+)?)\s*million",
            r"€\s*([0-9]+(?:[.,][0-9]+)?)\s*milioni",
            r"eur\s*([0-9]+(?:[.,][0-9]+)?)\s*milioni",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).replace(",", ".")
                try:
                    return float(value) * 1_000_000
                except ValueError:
                    return None

        return None

    def _infer_eligible_entities(self, text: str) -> list[str]:
        lowered = text.lower()
        entities = []

        if "startup" in lowered or "start-up" in lowered:
            entities.append("startups")

        if "sme" in lowered or "pmi" in lowered:
            entities.append("SMEs")

        if "company" in lowered or "companies" in lowered or "impresa" in lowered:
            entities.append("companies")

        if "research" in lowered or "university" in lowered or "università" in lowered:
            entities.append("research organisations")

        if "consortium" in lowered or "consortia" in lowered or "partnership" in lowered:
            entities.append("consortia")

        if not entities:
            entities = ["startups", "SMEs", "companies", "research organisations"]

        return entities

    def _infer_countries(self, source: str, text: str) -> list[str]:
        source_lower = source.lower()
        text_lower = text.lower()

        if "asi" in source_lower or "italy" in text_lower or "italia" in text_lower:
            return ["Italy"]

        if "esa bic italy" in source_lower:
            return ["Italy"]

        return ["ESA Member States", "EU"]

    def _infer_topics(self, text: str) -> list[str]:
        lowered = text.lower()
        topics = []

        mapping = {
            "space": "space",
            "spazio": "space",
            "esa": "ESA",
            "asi": "ASI",
            "satellite": "satellite",
            "earth observation": "earth observation",
            "osservazione della terra": "earth observation",
            "remote sensing": "remote sensing",
            "downstream": "space downstream",
            "business applications": "space business applications",
            "incubation": "incubation",
            "bic": "business incubation",
            "startup": "startup",
            "sme": "SME",
            "agriculture": "agriculture",
            "agricoltura": "agriculture",
            "agritech": "agritech",
            "environment": "environment",
            "ambiente": "environment",
            "climate": "climate",
            "monitoring": "monitoring",
            "monitoraggio": "monitoring",
            "autonomous": "autonomous systems",
            "autonomia": "autonomous systems",
            "decision support": "decision support",
            "dss": "decision support",
            "artificial intelligence": "AI",
            "ai": "AI",
            "extreme environment": "extreme environments",
            "ambienti estremi": "extreme environments",
            "controlled environment": "controlled environment agriculture",
            "greenhouse": "greenhouse",
            "serra": "greenhouse",
            "pilot": "pilot project",
            "proof-of-concept": "proof of concept",
            "proof of concept": "proof of concept",
        }

        for key, value in mapping.items():
            if key in lowered and value not in topics:
                topics.append(value)

        if not topics:
            topics.append("space opportunity")

        return topics

    def _build_summary(self, text: str, max_len: int = 800) -> str:
        text = self._clean_text(text)

        if len(text) <= max_len:
            return text

        return text[:max_len].rstrip() + "..."

    def _deduplicate(self, calls: List[FundingCall]) -> List[FundingCall]:
        best = {}

        for call in calls:
            key = call.source_url
            prev = best.get(key)

            if prev is None or len(call.raw_text or "") > len(prev.raw_text or ""):
                best[key] = call

        return list(best.values())