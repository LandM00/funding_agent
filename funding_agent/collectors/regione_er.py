import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class RegioneERCollector(BaseCollector):
    name = "regione_er"

    HUB_URL = "https://agricoltura.regione.emilia-romagna.it/sviluppo-rurale-23-27/opportunita/bandi"
    BASE_URL = "https://agricoltura.regione.emilia-romagna.it"

    def __init__(self, timeout: int = 20):
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
        hub_html = self._safe_get(self.HUB_URL)
        if not hub_html:
            return []

        hub_soup = BeautifulSoup(hub_html, "html.parser")
        hub_text = self._extract_main_text(hub_soup)

        bandi_in_corso_url = self._find_bandi_in_corso_url(hub_soup)

        if bandi_in_corso_url:
            calls = self._fetch_bandi_in_corso(bandi_in_corso_url)
            if calls:
                return calls

        hub_call = FundingCall(
            source="Regione Emilia-Romagna",
            source_url=self.HUB_URL,
            call_id="RER-BANDI-HUB",
            title="Bandi - Sviluppo rurale 2023-2027",
            summary=self._build_summary(hub_text),
            program="Sviluppo rurale 2023-2027",
            opening_date=None,
            deadline_date=None,
            budget_total=None,
            funding_type="bando / hub informativo",
            record_type="hub",
            eligible_entities=["aziende agricole", "beneficiari sviluppo rurale"],
            countries=["Italy"],
            topics=self._infer_topics(hub_text, "Bandi - Sviluppo rurale 2023-2027"),
            raw_text=hub_text,
        )
        return [hub_call]

    def _fetch_bandi_in_corso(self, url: str) -> List[FundingCall]:
        html = self._safe_get(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        results = []
        seen = set()

        for a in links:
            href = a["href"].strip()
            text = a.get_text(" ", strip=True)
            full_url = urljoin(self.BASE_URL, href)

            if not self._is_candidate_call_link(full_url, text):
                continue

            if full_url in seen:
                continue

            seen.add(full_url)

            detail_html = self._safe_get(full_url)
            if not detail_html:
                continue

            detail_soup = BeautifulSoup(detail_html, "html.parser")
            detail_title = self._extract_title(detail_soup) or text
            detail_text = self._extract_main_text(detail_soup)

            if not self._looks_like_real_call_page(full_url, detail_title, detail_text):
                continue

            call = FundingCall(
                source="Regione Emilia-Romagna",
                source_url=full_url,
                call_id=self._build_call_id(full_url),
                title=detail_title,
                summary=self._build_summary(detail_text),
                program="Sviluppo rurale 2023-2027",
                opening_date=None,
                deadline_date=self._extract_deadline(detail_text, detail_title, full_url),
                budget_total=None,
                funding_type="bando",
                record_type="call",
                eligible_entities=["aziende agricole", "beneficiari sviluppo rurale"],
                countries=["Italy"],
                topics=self._infer_topics(detail_text, detail_title),
                raw_text=detail_text,
            )
            results.append(call)

        return results

    def _find_bandi_in_corso_url(self, soup: BeautifulSoup) -> Optional[str]:
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            href = a["href"].strip()
            full_url = urljoin(self.BASE_URL, href).lower()

            if "bandi in corso" in text:
                return urljoin(self.BASE_URL, href)

            if "/bandi/bandi-in-corso" in full_url:
                return urljoin(self.BASE_URL, href)

        return None

    def _safe_get(self, url: str) -> Optional[str]:
        lowered = url.lower()

        blocked = [
            "facebook.com",
            "api.whatsapp.com",
            "t.me/share",
            "linkedin.com",
            "twitter.com",
            "x.com",
            "mailto:",
            "javascript:",
        ]
        if any(b in lowered for b in blocked):
            return None

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[RegioneERCollector] Errore su {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(" ", strip=True)

        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(" ", strip=True)

        return ""

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        selectors = [
            "main",
            "article",
            ".content",
            ".container",
            ".documentFirstHeading",
        ]

        candidates = []

        for selector in selectors:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 250:
                    candidates.append(text)

        if candidates:
            return max(candidates, key=len)

        fallback = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", fallback).strip()

    def _build_summary(self, text: str, max_len: int = 600) -> str:
        summary = text[:max_len].strip()
        if len(text) > max_len:
            summary += "..."
        return summary

    def _extract_deadline(self, text: str, title: str, url: str) -> str | None:
        content = f"{title} {text} {url}".lower()

        if "chius" in content:
            return "closed"

        if "apert" in content or "in corso" in content:
            return "open"

        return None

    def _is_candidate_call_link(self, url: str, text: str) -> bool:
        lowered_url = url.lower()
        lowered_text = text.lower()
        parsed = urlparse(url)

        if lowered_url.startswith("mailto:"):
            return False
        if lowered_url.startswith("javascript:"):
            return False
        if parsed.fragment:
            return False

        if any(x in lowered_url for x in [
            "facebook.com",
            "api.whatsapp.com",
            "t.me/share",
            "linkedin.com",
            "twitter.com",
            "x.com",
        ]):
            return False

        if "agricoltura.regione.emilia-romagna.it" not in lowered_url:
            return False

        excluded_fragments = [
            "/newsletter",
            "/accessibilita",
            "/info",
            "/crediti",
            "/privacy",
            "/cookie",
            "/regolamenti",
            "/cronoprogramma",
            "/organismo-di-coordinamento-akis-regionale",
            "/piano-strategico-nazionale-pac",
            "/bandi-chiusi",
            "/bandi-gal",
            "/programma/comunicazione",
            "/programma/comitato-di-monitoraggio",
            "/programma/complemento-programmazione",
            "/programma/interventi",
            "/disposizioni-attuative-regionali/prezziario-opere-agricoltura",
            "/disposizioni-attuative-regionali/costi-standard",
            "/disposizioni-attuative-regionali/documenti-regionali",
            "/disposizioni-attuative-regionali/delimitazioni",
            "/disposizioni-attuative-regionali/check-lists",
        ]
        if any(x in lowered_url for x in excluded_fragments):
            return False

        excluded_texts = {
            "",
            "-",
            "newsletter",
            "telegram: share web page",
            "compartilhe no whatsapp",
            "vai al footer",
            "vai alla navigazione",
            "vai al contenuto",
            "opportunità",
            "bandi in corso",
            "bandi",
            "comunicazione",
            "complemento di programmazione",
            "interventi",
            "regolamenti comunitari",
            "prezziario per opere in agricoltura",
            "costi standard",
            "delimitazioni territoriali",
            "comitato di monitoraggio",
        }
        if lowered_text in excluded_texts:
            return False

        positive = [
            "intervento",
            "srd",
            "sra",
            "srg",
            "sre",
            "investimenti",
            "insediamento",
            "giovani",
            "agricoltori",
            "forest",
            "zootec",
        ]

        if any(p in lowered_text for p in positive):
            return True

        if any(p in lowered_url for p in positive):
            return True

        return False

    def _looks_like_real_call_page(self, url: str, title: str, text: str) -> bool:
        content = f"{url} {title} {text}".lower()

        weak_patterns = [
            "prezziario",
            "costi standard",
            "complemento di programmazione",
            "comitato di monitoraggio",
            "comunicazione",
            "check lists",
            "delimitazioni",
            "documenti regionali",
        ]
        if any(w in content for w in weak_patterns):
            return False

        strong_patterns = [
            "intervento",
            "srd",
            "sra",
            "srg",
            "sre",
            "beneficiari",
            "spese ammissibili",
            "domande di sostegno",
            "contributo",
            "investimenti",
            "insediamento",
            "giovani agricoltori",
        ]

        return any(p in content for p in strong_patterns)

    def _build_call_id(self, url: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-").upper()
        return f"RER-{clean[:80]}"

    def _infer_topics(self, text: str, title: str) -> List[str]:
        content = f"{title} {text}".lower()
        topics = []

        mapping = {
            "agricol": "agriculture",
            "sviluppo rurale": "rural development",
            "giovani": "young farmers",
            "investimenti": "investments",
            "insediamento": "new farm setup",
            "ambiente": "environment",
            "innovazione": "innovation",
            "digit": "digital innovation",
            "irrig": "irrigation",
            "serra": "CEA",
            "sostenib": "sustainability",
            "forest": "forestry",
            "zootec": "livestock",
        }

        for key, topic in mapping.items():
            if key in content and topic not in topics:
                topics.append(topic)

        if not topics:
            topics.append("regional funding")

        return topics