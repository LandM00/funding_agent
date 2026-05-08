from __future__ import annotations

import re
from typing import List

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class EICEurekaCollector(BaseCollector):
    name = "eic_eureka"

    SOURCES = [
        {
            "source_url": "https://eic.ec.europa.eu/funding-opportunities_en",
            "source": "European Innovation Council",
            "program": "EIC",
            "call_id": "EIC-FUNDING-OPPORTUNITIES",
            "title": "European Innovation Council - Funding opportunities",
            "fallback_summary": (
                "Portale EIC con opportunità per innovazione breakthrough, startup, PMI, "
                "scale-up e tecnologie strategiche."
            ),
        },
        {
            "source_url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
            "source": "European Innovation Council",
            "program": "EIC Accelerator",
            "call_id": "EIC-ACCELERATOR",
            "title": "EIC Accelerator",
            "fallback_summary": (
                "Funding EIC Accelerator per startup e PMI con innovazioni breakthrough, "
                "grant e investimento per commercializzazione e scale-up."
            ),
        },
        {
            "source_url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-2026-work-programme_en",
            "source": "European Innovation Council",
            "program": "EIC Work Programme",
            "call_id": "EIC-2026-WORK-PROGRAMME",
            "title": "EIC 2026 Work Programme",
            "fallback_summary": (
                "Programma di lavoro EIC 2026 con opportunità per tecnologie strategiche, "
                "startup, PMI e scale-up innovative."
            ),
        },
        {
            "source_url": "https://www.eurekanetwork.org/",
            "source": "Eureka Network",
            "program": "Eureka / Eurostars",
            "call_id": "EUREKA-OPEN-CALLS",
            "title": "Eureka Network - Open calls for projects",
            "fallback_summary": (
                "Portale Eureka con open calls per progetti innovativi, Eurostars, PMI "
                "innovative e collaborazione internazionale R&D."
            ),
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
                text = self._clean_text(soup.get_text(" ", strip=True))

            if not text:
                text = item["fallback_summary"]

            deadline = self._extract_deadline(text)
            opening = self._extract_opening(text)

            calls.append(
                FundingCall(
                    source=item["source"],
                    source_url=item["source_url"],
                    call_id=item["call_id"],
                    title=item["title"],
                    summary=self._build_summary(text or item["fallback_summary"]),
                    program=item["program"],
                    opening_date=opening,
                    deadline_date=deadline or "open",
                    budget_total=self._extract_budget(text),
                    funding_type=self._infer_funding_type(text),
                    record_type="call",
                    eligible_entities=self._infer_eligible_entities(text),
                    countries=["EU", "Eureka countries"],
                    topics=self._infer_topics(text),
                    raw_text=text,
                )
            )

        return calls

    def _safe_get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[EIC/Eureka] Errore su {url}: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _extract_deadline(self, text: str) -> str | None:
        patterns = [
            r"deadline dates?[:\s]+([0-9]{1,2}\.?[0-9]{0,2}\.?\s*[A-Za-zÀ-ÿ]*\s*[0-9]{4})",
            r"deadline[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"call closes[:\s]+([A-Za-zÀ-ÿ]+\s+[0-9]{1,2}\s+[0-9]{4})",
            r"closes[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        if "open calls" in text.lower() or "call status: open" in text.lower():
            return "open"

        return None

    def _extract_opening(self, text: str) -> str | None:
        patterns = [
            r"call opens[:\s]+([A-Za-zÀ-ÿ]+\s+[0-9]{1,2}\s+[0-9]{4})",
            r"opens[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_budget(self, text: str) -> float | None:
        lowered = text.lower()

        # Non proviamo a normalizzare tutti i casi.
        # Il valore resta None se non è chiaramente un singolo budget.
        if "€1.4 billion" in lowered or "eur 1.4 billion" in lowered:
            return 1_400_000_000.0

        if "eur 220 million" in lowered:
            return 220_000_000.0

        return None

    def _infer_funding_type(self, text: str) -> str:
        lowered = text.lower()

        if "grant" in lowered and "investment" in lowered:
            return "grant + equity/investment"

        if "grant" in lowered:
            return "grant"

        if "investment" in lowered:
            return "investment"

        return "EU innovation funding"

    def _infer_eligible_entities(self, text: str) -> list[str]:
        lowered = text.lower()
        entities = []

        if "start-up" in lowered or "startup" in lowered:
            entities.append("startups")

        if "sme" in lowered or "pmi" in lowered:
            entities.append("SMEs")

        if "research organisation" in lowered or "university" in lowered:
            entities.append("research organisations")

        if "consortia" in lowered or "collaborative" in lowered:
            entities.append("consortia")

        if not entities:
            entities = ["startups", "SMEs", "consortia"]

        return entities

    def _infer_topics(self, text: str) -> list[str]:
        lowered = text.lower()
        topics = []

        mapping = {
            "accelerator": "accelerator",
            "scale-up": "scale-up",
            "deep tech": "deep tech",
            "breakthrough": "breakthrough innovation",
            "sme": "SME innovation",
            "startup": "startup",
            "artificial intelligence": "AI",
            "ai": "AI",
            "digital": "digital",
            "agriculture": "agriculture",
            "agritech": "agritech",
            "climate": "climate",
            "green": "green transition",
            "eurostars": "Eurostars",
            "eureka": "Eureka",
            "international": "international R&D",
            "collaborative": "collaborative R&D",
        }

        for key, value in mapping.items():
            if key in lowered and value not in topics:
                topics.append(value)

        if not topics:
            topics.append("EU innovation")

        return topics

    def _build_summary(self, text: str, max_len: int = 800) -> str:
        text = self._clean_text(text)
        if len(text) <= max_len:
            return text
        return text[:max_len].rstrip() + "..."