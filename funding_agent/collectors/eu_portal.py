import re
from typing import List

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class EUPortalCollector(BaseCollector):
    name = "eu_portal"

    START_URLS = [
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals",
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/funding-updates",
    ]

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
        calls = []

        for start_url in self.START_URLS:
            html = self._safe_get(start_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            main_text = self._extract_main_text(soup)

            hub_title = self._extract_title(soup) or "EU Funding & Tenders Portal"
            hub_program = self._infer_program(hub_title, main_text)

            hub_call = FundingCall(
                source="EU Funding & Tenders",
                source_url=start_url,
                call_id=self._build_hub_id(start_url),
                title=hub_title,
                summary=self._build_summary(main_text),
                program=hub_program,
                opening_date=None,
                deadline_date=None,
                budget_total=None,
                funding_type="hub / portal page",
                record_type="hub",
                eligible_entities=["research organisations", "companies", "consortia"],
                countries=["EU"],
                topics=self._infer_topics(hub_title, main_text),
                raw_text=main_text,
            )

            calls.append(hub_call)

        return self._deduplicate(calls)

    def _safe_get(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[EUPortalCollector] Errore su {url}: {e}")
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
            ".page-content",
            ".eui-u-content-block",
            ".container",
        ]

        candidates = []

        for selector in selectors:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 200:
                    candidates.append(text)

        if candidates:
            return max(candidates, key=len)

        fallback = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", fallback).strip()

    def _build_summary(self, text: str, max_len: int = 700) -> str:
        summary = text[:max_len].strip()
        if len(text) > max_len:
            summary += "..."
        return summary

    def _build_hub_id(self, url: str) -> str:
        lowered = url.lower()

        if "calls-for-proposals" in lowered:
            return "EU-HUB-CALLS-FOR-PROPOSALS"

        if "funding-updates" in lowered:
            return "EU-HUB-FUNDING-UPDATES"

        return "EU-HUB"

    def _infer_program(self, title: str, text: str) -> str:
        content = f"{title} {text}".lower()

        if "horizon europe" in content and "cluster 6" in content:
            return "Horizon Europe - Cluster 6"

        if "horizon europe" in content and "digital, industry and space" in content:
            return "Horizon Europe - Cluster 4"

        if "horizon europe" in content:
            return "Horizon Europe"

        if "eic" in content:
            return "EIC"

        return "EU Funding & Tenders"

    def _infer_topics(self, title: str, text: str) -> List[str]:
        content = f"{title} {text}".lower()
        topics = []

        mapping = {
            "agriculture": "agriculture",
            "food": "food systems",
            "bioeconomy": "bioeconomy",
            "environment": "environment",
            "greenhouse": "CEA",
            "irrigation": "irrigation",
            "fertigation": "fertigation",
            "sensor": "sensors",
            "robot": "robotics",
            "artificial intelligence": "AI",
            "ai": "AI",
            "space": "space",
            "satellite": "space",
            "copernicus": "earth observation",
            "innovation": "innovation",
            "cluster 6": "cluster 6",
            "cluster 4": "cluster 4",
        }

        for key, topic in mapping.items():
            if key in content and topic not in topics:
                topics.append(topic)

        if not topics:
            topics.append("eu funding")

        return topics

    def _deduplicate(self, calls: List[FundingCall]) -> List[FundingCall]:
        best = {}

        for call in calls:
            key = call.call_id or call.source_url
            prev = best.get(key)

            if prev is None or len(call.raw_text) > len(prev.raw_text):
                best[key] = call

        return list(best.values())