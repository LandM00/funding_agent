from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class IncentiviGovCollector(BaseCollector):
    name = "incentivi_gov"

    START_URL = "https://www.incentivi.gov.it/it/catalogo"
    BASE_URL = "https://www.incentivi.gov.it"

    def __init__(self, timeout: int = 25, max_details: int = 80):
        self.timeout = timeout
        self.max_details = max_details
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
        html = self._safe_get(self.START_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        urls = self._extract_catalog_urls(soup)

        calls = []

        for url in urls[: self.max_details]:
            detail_html = self._safe_get(url)
            if not detail_html:
                continue

            detail_soup = BeautifulSoup(detail_html, "html.parser")
            title = self._extract_title(detail_soup)

            if not title:
                continue

            text = self._clean_text(detail_soup.get_text(" ", strip=True))

            if not self._is_relevant_enough(text):
                continue

            calls.append(
                FundingCall(
                    source="Incentivi.gov.it",
                    source_url=url,
                    call_id=self._build_call_id(title),
                    title=title,
                    summary=self._build_summary(text),
                    program=self._infer_program(text),
                    opening_date=self._extract_opening(text),
                    deadline_date=self._extract_deadline(text),
                    budget_total=None,
                    funding_type=self._infer_funding_type(text),
                    record_type="call",
                    eligible_entities=self._infer_eligible_entities(text),
                    countries=["Italy"],
                    topics=self._infer_topics(text),
                    raw_text=text,
                )
            )

        return self._deduplicate(calls)

    def _safe_get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[IncentiviGov] Errore su {url}: {e}")
            return None

    def _extract_catalog_urls(self, soup: BeautifulSoup) -> list[str]:
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            url = urljoin(self.BASE_URL, href)

            if "/it/catalogo/" not in url:
                continue

            if url not in urls:
                urls.append(url)

        return urls

    def _extract_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(" ", strip=True)

        title = soup.find("title")
        if title:
            return title.get_text(" ", strip=True).replace("| Incentivi", "").strip()

        return ""

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _is_relevant_enough(self, text: str) -> bool:
        lowered = text.lower()

        positive = [
            "startup",
            "start-up",
            "pmi",
            "micro",
            "piccole imprese",
            "innovazione",
            "ricerca",
            "sviluppo",
            "digitale",
            "digitalizzazione",
            "transizione ecologica",
            "agricoltura",
            "agroalimentare",
            "investimenti",
            "fondo perduto",
            "finanziamento agevolato",
            "contributo",
        ]

        negative = [
            "persone fisiche",
            "famiglie",
            "bonus psicologo",
            "pensione",
            "sociale",
        ]

        if any(n in lowered for n in negative) and not any(p in lowered for p in positive):
            return False

        return any(p in lowered for p in positive)

    def _extract_deadline(self, text: str) -> str | None:
        lowered = text.lower()

        if "sportello" in lowered or "fino a esaurimento" in lowered:
            return "sportello_aperto"

        patterns = [
            r"data chiusura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"chiusura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
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
            r"data apertura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"apertura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"dal\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _infer_program(self, text: str) -> str:
        lowered = text.lower()

        if "invitalia" in lowered:
            return "Invitalia"

        if "ministero" in lowered:
            return "Ministero / Incentivi.gov.it"

        if "regione emilia-romagna" in lowered:
            return "Regione Emilia-Romagna"

        return "Incentivi.gov.it"

    def _infer_funding_type(self, text: str) -> str:
        lowered = text.lower()

        if "fondo perduto" in lowered:
            return "grant"

        if "finanziamento agevolato" in lowered or "tasso zero" in lowered:
            return "soft loan"

        if "credito d'imposta" in lowered or "credito di imposta" in lowered:
            return "tax credit"

        if "voucher" in lowered:
            return "voucher"

        return "incentive"

    def _infer_eligible_entities(self, text: str) -> list[str]:
        lowered = text.lower()
        entities = []

        if "startup" in lowered or "start-up" in lowered:
            entities.append("startups")

        if "pmi" in lowered or "piccole e medie imprese" in lowered:
            entities.append("SMEs")

        if "micro" in lowered:
            entities.append("micro-enterprises")

        if "imprese agricole" in lowered or "aziende agricole" in lowered:
            entities.append("agricultural companies")

        if "università" in lowered or "organismi di ricerca" in lowered:
            entities.append("research organisations")

        if not entities:
            entities = ["companies"]

        return entities

    def _infer_topics(self, text: str) -> list[str]:
        lowered = text.lower()
        topics = []

        mapping = {
            "startup": "startup",
            "innovazione": "innovation",
            "ricerca": "R&D",
            "sviluppo": "R&D",
            "digitale": "digital",
            "digitalizzazione": "digital",
            "agricoltura": "agriculture",
            "agroalimentare": "agri-food",
            "transizione ecologica": "green transition",
            "ambiente": "environment",
            "energia": "energy",
            "internazionalizzazione": "internationalisation",
            "investimenti": "investment",
        }

        for key, value in mapping.items():
            if key in lowered and value not in topics:
                topics.append(value)

        if not topics:
            topics.append("public incentive")

        return topics

    def _build_summary(self, text: str, max_len: int = 700) -> str:
        text = self._clean_text(text)
        if len(text) <= max_len:
            return text
        return text[:max_len].rstrip() + "..."

    def _build_call_id(self, title: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", title.upper()).strip("-")
        slug = slug[:90] or "INCENTIVO"
        return f"INCENTIVI-GOV-{slug}"

    def _deduplicate(self, calls: List[FundingCall]) -> List[FundingCall]:
        best = {}

        for call in calls:
            key = call.source_url
            prev = best.get(key)

            if prev is None or len(call.raw_text or "") > len(prev.raw_text or ""):
                best[key] = call

        return list(best.values())