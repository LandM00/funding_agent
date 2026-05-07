import re
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class RegioneERCollector(BaseCollector):
    name = "regione_er"

    HUB_URL = "https://agricoltura.regione.emilia-romagna.it/sviluppo-rurale-23-27/opportunita/bandi"
    BASE_URL = "https://agricoltura.regione.emilia-romagna.it"

    def __init__(self, timeout: int = 25, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )

    def fetch(self) -> List[FundingCall]:
        hub_html = self._safe_get(self.HUB_URL)
        if not hub_html:
            return []

        hub_soup = BeautifulSoup(hub_html, "html.parser")
        bandi_in_corso_url = self._find_bandi_in_corso_url(hub_soup)

        if not bandi_in_corso_url:
            print("[RegioneERCollector] URL 'bandi in corso' non trovato.")
            return []

        return self._fetch_bandi_in_corso(bandi_in_corso_url)

    def _fetch_bandi_in_corso(self, url: str) -> List[FundingCall]:
        html = self._get_dynamic_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        results: List[FundingCall] = []
        seen = set()

        for a in links:
            href = a["href"].strip()
            anchor_text = a.get_text(" ", strip=True)
            full_url = urljoin(self.BASE_URL, href)
            lowered_url = full_url.lower()

            if full_url in seen:
                continue
            seen.add(full_url)

            if not self._is_real_bando_url(lowered_url, anchor_text):
                continue

            print(f"[RER BANDO] {anchor_text} -> {full_url}")

            detail_html = self._safe_get(full_url)
            if not detail_html:
                print(f"[RER SKIP] dettaglio non scaricato: {anchor_text}")
                continue

            detail_soup = BeautifulSoup(detail_html, "html.parser")
            title = self._extract_title(detail_soup) or anchor_text
            text = self._extract_main_text(detail_soup)

            if len(text) < 300:
                print(f"[RER SKIP] testo troppo corto ({len(text)}): {anchor_text}")
                continue

            if not self._looks_like_real_call_page(full_url, title, text):
                if not self._has_bando_code(full_url, title, anchor_text):
                    print(f"[RER SKIP] non sembra bando reale: {anchor_text}")
                    continue

            deadline = self._extract_deadline(text, title, full_url)

            if not deadline:
                deadline = "open"

            if deadline == "closed":
                continue

            call = FundingCall(
                source="Regione Emilia-Romagna",
                source_url=full_url,
                call_id=self._build_call_id(full_url),
                title=self._clean_title(title),
                summary=self._build_summary(text),
                program="Sviluppo rurale 2023-2027",
                opening_date=None,
                deadline_date=deadline,
                budget_total=self._extract_budget(text),
                funding_type="bando regionale",
                record_type="call",
                eligible_entities=[
                    "aziende agricole",
                    "beneficiari sviluppo rurale",
                ],
                countries=["Italy"],
                topics=self._infer_topics(text, title),
                raw_text=text,
            )

            results.append(call)

        return self._deduplicate(results)

    def _get_dynamic_html(self, url: str) -> Optional[str]:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                print(f"[RER] Opening dynamic page: {url}")
                page.goto(url, timeout=60000, wait_until="networkidle")
                page.wait_for_timeout(2500)

                html = page.content()
                browser.close()
                return html

        except Exception as e:
            print(f"[RegioneERCollector] Playwright error su {url}: {e}")
            return None

    def _find_bandi_in_corso_url(self, soup: BeautifulSoup) -> Optional[str]:
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            href = a["href"].strip()
            full_url = urljoin(self.BASE_URL, href)

            if "bandi in corso" in text:
                return full_url

            if "/bandi/bandi-in-corso" in full_url.lower():
                return full_url

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
            "tel:",
        ]

        if any(b in lowered for b in blocked):
            return None

        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text

            except requests.RequestException as e:
                if attempt == self.retries:
                    print(f"[RegioneERCollector] Errore su {url}: {e}")
                    return None

                time.sleep(1.5 * attempt)

        return None

    def _is_real_bando_url(self, lowered_url: str, anchor_text: str) -> bool:
        text = (anchor_text or "").lower()

        if "agricoltura.regione.emilia-romagna.it" not in lowered_url:
            return False

        if "/sviluppo-rurale-23-27/opportunita/bandi/" not in lowered_url:
            return False

        excluded = [
            "bandi-in-corso",
            "bandi-chiusi",
            "bandi-gal",
            "facebook.com",
            "linkedin.com",
            "whatsapp",
            "telegram",
            "mailto:",
            "newsletter",
            "privacy",
            "cookie",
            "accessibilita",
            "info",
        ]

        if any(x in lowered_url for x in excluded):
            return False

        if len(text) < 8:
            return False

        positive_patterns = [
            "/srd",
            "/sra",
            "/srg",
            "/srh",
            "/sre",
            "investimenti",
            "intervento",
            "sostegno",
            "contributi",
            "domande",
        ]

        return any(p in lowered_url or p in text for p in positive_patterns)

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
            "#content",
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

    def _clean_title(self, title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        title = title.replace("—", "-")
        return title

    def _build_summary(self, text: str, max_len: int = 350) -> str:
        text = re.sub(r"\s+", " ", text).strip()

        for noise in [
            "Briciole di pane",
            "Home /",
            "Vai al contenuto",
            "Vai alla navigazione",
        ]:
            text = text.replace(noise, "")

        summary = text[:max_len].strip()
        if len(text) > max_len:
            summary += "..."

        return summary

    def _extract_deadline(self, text: str, title: str, url: str) -> Optional[str]:
        content = f"{title} {text} {url}"
        lowered = content.lower()

        closed_patterns = [
            "bando chiuso",
            "chiuso",
            "scaduto",
            "scaduta",
        ]

        if any(k in lowered for k in closed_patterns):
            return "closed"

        month_names = (
            "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
            "settembre|ottobre|novembre|dicembre"
        )

        patterns = [
            rf"scadenza[^0-9]{{0,120}}(\d{{1,2}}\s+(?:{month_names})\s+\d{{4}})",
            rf"entro[^0-9]{{0,120}}(\d{{1,2}}\s+(?:{month_names})\s+\d{{4}})",
            rf"fino al[^0-9]{{0,120}}(\d{{1,2}}\s+(?:{month_names})\s+\d{{4}})",
            rf"presentazione[^0-9]{{0,150}}(\d{{1,2}}\s+(?:{month_names})\s+\d{{4}})",
            r"scadenza[^0-9]{0,120}(\d{1,2}/\d{1,2}/\d{4})",
            r"entro[^0-9]{0,120}(\d{1,2}/\d{1,2}/\d{4})",
            r"fino al[^0-9]{0,120}(\d{1,2}/\d{1,2}/\d{4})",
            r"presentazione[^0-9]{0,150}(\d{1,2}/\d{1,2}/\d{4})",
            r"scadenza[^0-9]{0,120}(\d{4}-\d{2}-\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                return match.group(1)

        if "in corso" in lowered or "apert" in lowered:
            return "open"

        return None

    def _extract_budget(self, text: str) -> Optional[float]:
        lowered = text.lower()

        patterns = [
            r"dotazione finanziaria[^0-9]{0,100}([\d\.\,]+)\s*(?:euro|€)",
            r"risorse[^0-9]{0,100}([\d\.\,]+)\s*(?:euro|€)",
            r"budget[^0-9]{0,100}([\d\.\,]+)\s*(?:euro|€)",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue

            raw = match.group(1).replace(".", "").replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                continue

        return None

    # -------------------------
    # VALIDATION
    # -------------------------

    def _has_bando_code(self, url: str, title: str, anchor_text: str) -> bool:
        content = f"{url} {title} {anchor_text}".lower()
        return bool(re.search(r"\b(sr[adhge]\d{1,2})\b", content))

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
            "regolamenti comunitari",
        ]

        if any(w in content for w in weak_patterns):
            return False

        strong_patterns = [
            "bando",
            "intervento",
            "srd",
            "sra",
            "srg",
            "srh",
            "sre",
            "beneficiari",
            "spese ammissibili",
            "domande di sostegno",
            "contributo",
            "contributi",
            "investimenti",
            "insediamento",
            "giovani agricoltori",
            "sostegno",
            "presentazione delle domande",
        ]

        return any(p in content for p in strong_patterns)

    def _build_call_id(self, url: str) -> str:
        parsed = urlparse(url)
        slug = parsed.path.rstrip("/").split("/")[-1]
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").upper()
        return f"RER-{clean[:90]}"

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
            "biologico": "organic farming",
            "trasformazione": "transformation",
            "commercializzazione": "commercialization",
        }

        for key, topic in mapping.items():
            if key in content and topic not in topics:
                topics.append(topic)

        if not topics:
            topics.append("regional funding")

        return topics

    def _deduplicate(self, calls: List[FundingCall]) -> List[FundingCall]:
        best = {}

        for call in calls:
            key = call.source_url
            if key not in best:
                best[key] = call

        return list(best.values())