from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class EmiliaRomagnaStartupCollector(BaseCollector):
    name = "emiliaromagna_startup"

    START_URL = "https://www.emiliaromagnastartup.it/it/bandi"
    BASE_URL = "https://www.emiliaromagnastartup.it"

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
        html = self._safe_get(self.START_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        calls = []

        for link in soup.find_all("a", href=True):
            link_title = link.get_text(" ", strip=True)
            href = link["href"]

            if not link_title or len(link_title) < 8:
                continue

            url = urljoin(self.BASE_URL, href)

            if not self._is_valid_opportunity_url(url):
                continue

            if self._is_noise(link_title):
                # Non scartiamo subito: spesso il link è "Vai alla scheda di dettaglio",
                # ma la pagina contiene un titolo vero. Lo recuperiamo dalla pagina dettaglio.
                pass

            detail_html = self._safe_get(url)
            if not detail_html:
                continue

            detail_soup = BeautifulSoup(detail_html, "html.parser")

            detail_title = self._extract_detail_title(detail_soup)
            if not detail_title:
                detail_title = link_title

            detail_title = self._clean_title(detail_title)

            if not detail_title or len(detail_title) < 8:
                continue

            if self._is_noise(detail_title):
                continue

            if self._is_category_like_title(detail_title):
                continue

            detail_text = self._extract_main_text(detail_soup)
            combined_text = self._clean_text(f"{detail_title} {detail_text}")

            if not self._looks_like_opportunity(combined_text):
                continue

            deadline = self._extract_deadline(combined_text)
            opening = self._extract_opening(combined_text)
            topics = self._infer_topics(combined_text)
            funding_type = self._infer_funding_type(combined_text)

            calls.append(
                FundingCall(
                    source="EmiliaRomagnaStartup",
                    source_url=url,
                    call_id=self._build_call_id(detail_title, url),
                    title=detail_title,
                    summary=self._build_summary(combined_text),
                    program="EmiliaRomagnaStartup / ART-ER",
                    opening_date=opening,
                    deadline_date=deadline,
                    budget_total=None,
                    funding_type=funding_type,
                    record_type="call",
                    eligible_entities=self._infer_eligible_entities(combined_text),
                    countries=["Italy"],
                    topics=topics,
                    raw_text=combined_text,
                )
            )

        return self._deduplicate(calls)

    def _safe_get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[EmiliaRomagnaStartup] Errore su {url}: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _clean_title(self, title: str) -> str:
        title = self._clean_text(title)

        replacements = [
            "| EmiliaRomagnaStartUp",
            "| EmiliaRomagnaStartup",
            "EmiliaRomagnaStartUp",
            "EmiliaRomagnaStartup",
        ]

        for item in replacements:
            title = title.replace(item, "")

        title = re.sub(r"\s+", " ", title).strip(" -|")
        return title.strip()

    def _extract_detail_title(self, soup: BeautifulSoup) -> str:
        """
        Estrae il titolo reale della scheda.
        Serve a evitare titoli sporchi come 'Vai alla scheda di dettaglio'.
        """
        selectors = [
            "h1",
            ".page-title",
            ".node-title",
            ".field--name-title",
            "article h2",
            "main h2",
        ]

        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                title = self._clean_title(node.get_text(" ", strip=True))
                if title and not self._is_noise(title):
                    return title

        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_title(title_tag.get_text(" ", strip=True))
            if title and not self._is_noise(title):
                return title

        return ""

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """
        Estrae il testo principale della pagina evitando, per quanto possibile,
        menu, footer e contenuti laterali.
        """
        selectors = [
            "main",
            "article",
            ".content",
            ".page-content",
            ".field--name-body",
            ".node__content",
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

    def _is_valid_opportunity_url(self, url: str) -> bool:
        lowered = url.lower()

        # Escludiamo pagine categoria/settore/tipologia: non sono bandi singoli.
        excluded_patterns = [
            "/it/categoria/",
            "/categoria/",
            "/tipologia-bando/",
            "/settore-bando/",
            "/tag/",
            "/taxonomy/",
        ]

        if any(pattern in lowered for pattern in excluded_patterns):
            return False

        # Teniamo solo schede bando/opportunità vere.
        accepted_patterns = [
            "/it/innovative/bandi/",
            "/it/bandi/",
        ]

        return any(pattern in lowered for pattern in accepted_patterns)

    def _is_noise(self, title: str) -> bool:
        lowered = title.lower().strip()

        noise_exact = {
            "leggi tutto",
            "vai alla scheda",
            "vai alla scheda di dettaglio",
            "scopri di più",
            "privacy",
            "cookie",
            "login",
            "registrati",
            "home",
            "contatti",
            "newsletter",
            "facebook",
            "linkedin",
            "instagram",
            "twitter",
            "youtube",
            "cerca",
            "menu",
            "bandi",
            "opportunità",
            "opportunita",
        }

        noise_contains = [
            "vai alla scheda",
            "scheda di dettaglio",
            "cookie",
            "privacy",
        ]

        return lowered in noise_exact or any(n in lowered for n in noise_contains)

    def _is_category_like_title(self, title: str) -> bool:
        lowered = title.lower().strip()

        category_titles = {
            "premio economico",
            "scienze della vita",
            "innovazione sociale",
            "energia e ambiente",
            "meccanica e materiali",
            "icc - industrie culturali e creative",
            "industrie culturali e creative",
            "digitale",
            "ict",
            "agroalimentare",
            "ambiente",
            "energia",
            "finanziamenti",
            "contributi",
            "accelerazione",
            "incubazione",
            "strumenti utili",
            "tutti i settori",
            "percorso di accelerazione",
        }

        return lowered in category_titles

    def _looks_like_opportunity(self, text: str) -> bool:
        lowered = text.lower()

        keywords = [
            "bando",
            "call",
            "startup",
            "start-up",
            "start cup",
            "contributo",
            "finanziamento",
            "accelerazione",
            "opportunità",
            "opportunita",
            "fondo",
            "voucher",
            "premio",
            "innovazione",
            "chiusura",
            "scadenza",
            "candidature",
            "domande",
            "application",
            "deadline",
        ]

        return any(k in lowered for k in keywords)

    def _extract_deadline(self, text: str) -> str | None:
        patterns = [
            r"chiusura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"scadenza[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"deadline[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"entro\s+il\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"fino\s+al\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"entro\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        lowered = text.lower()
        if "sempre aperto" in lowered or "sportello" in lowered:
            return "sportello_aperto"

        return None

    def _extract_opening(self, text: str) -> str | None:
        patterns = [
            r"apertura[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"apre[:\s]+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
            r"dal\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _infer_topics(self, text: str) -> list[str]:
        lowered = text.lower()
        topics = []

        mapping = {
            "startup": "startup",
            "start-up": "startup",
            "spin-off": "spin-off",
            "spinoff": "spin-off",
            "innovazione": "innovation",
            "deep-tech": "deep tech",
            "deep tech": "deep tech",
            "digitale": "digital",
            "ict": "ICT",
            "generative ai": "AI",
            "llm": "AI",
            "intelligenza artificiale": "AI",
            "artificial intelligence": "AI",
            "agroalimentare": "agri-food",
            "agritech": "agritech",
            "ambiente": "environment",
            "energia": "energy",
            "clima": "climate",
            "green": "green transition",
            "accelerazione": "accelerator",
            "incubazione": "incubation",
            "ricerca": "R&D",
            "sviluppo": "R&D",
            "internazionalizzazione": "internationalisation",
            "eic": "EIC",
            "eureka": "Eureka",
            "eurostars": "Eurostars",
            "esa": "ESA",
            "spazio": "space",
            "space": "space",
        }

        for key, value in mapping.items():
            if key in lowered and value not in topics:
                topics.append(value)

        if not topics:
            topics.append("startup funding")

        return topics

    def _infer_funding_type(self, text: str) -> str:
        lowered = text.lower()

        if "accelerazione" in lowered or "accelerator" in lowered:
            return "accelerator"

        if "incubazione" in lowered or "incubator" in lowered:
            return "incubation"

        if "fondo" in lowered:
            return "fund"

        if "premio" in lowered or "competition" in lowered or "award" in lowered:
            return "competition / award"

        if "voucher" in lowered:
            return "voucher"

        if "contributo" in lowered or "cofinanziamento" in lowered:
            return "grant / co-financing"

        if "finanziamento" in lowered:
            return "funding"

        return "startup opportunity"

    def _infer_eligible_entities(self, text: str) -> list[str]:
        lowered = text.lower()
        entities = []

        if "startup" in lowered or "start-up" in lowered:
            entities.append("startups")

        if "spin-off" in lowered or "spinoff" in lowered:
            entities.append("spin-offs")

        if "pmi" in lowered or "sme" in lowered or "piccole e medie imprese" in lowered:
            entities.append("SMEs")

        if "università" in lowered or "organismi di ricerca" in lowered or "ricerca" in lowered:
            entities.append("research organisations")

        if "studenti" in lowered or "neolaureati" in lowered:
            entities.append("students / graduates")

        if not entities:
            entities = ["startups", "SMEs"]

        return entities

    def _build_summary(self, text: str, max_len: int = 700) -> str:
        text = self._clean_text(text)
        if len(text) <= max_len:
            return text
        return text[:max_len].rstrip() + "..."

    def _build_call_id(self, title: str, url: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", title.upper()).strip("-")
        slug = slug[:90] or "OPPORTUNITY"
        return f"ERS-{slug}"

    def _deduplicate(self, calls: List[FundingCall]) -> List[FundingCall]:
        best = {}

        for call in calls:
            key = call.source_url
            prev = best.get(key)

            if prev is None or len(call.raw_text or "") > len(prev.raw_text or ""):
                best[key] = call

        return list(best.values())