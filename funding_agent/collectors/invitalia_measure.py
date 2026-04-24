import re
from typing import List

import requests
from bs4 import BeautifulSoup

from funding_agent.collectors.base import BaseCollector
from funding_agent.models import FundingCall


class InvitaliaMeasureCollector(BaseCollector):
    def __init__(
        self,
        name: str,
        call_id: str,
        program: str,
        start_urls: List[str],
        funding_type: str,
        eligible_entities: List[str],
        countries: List[str] | None = None,
        timeout: int = 20,
    ):
        self.name = name
        self.call_id = call_id
        self.program = program
        self.start_urls = start_urls
        self.funding_type = funding_type
        self.eligible_entities = eligible_entities
        self.countries = countries or ["Italy"]
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
        pages = []

        for url in self.start_urls:
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"[InvitaliaMeasureCollector] Errore su {url}: {e}")
                continue

            parsed = self._parse_page(url, response.text)
            if parsed:
                pages.append(parsed)

        if not pages:
            return []

        merged_call = self._merge_pages_into_single_call(pages)
        return [merged_call]

    def _parse_page(self, url: str, html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        if not title:
            return None

        text = self._extract_main_text(soup)
        if not text:
            return None

        return {
            "url": url,
            "title": title.strip(),
            "text": text,
            "summary": self._build_summary(text),
            "budget_total": self._extract_budget_upper_bound(text),
            "deadline_date": self._extract_deadline(text),
            "topics": self._infer_topics(text, title),
        }

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
            ".field--name-body",
            ".container",
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

    def _build_summary(self, text: str, max_len: int = 700) -> str:
        summary = text[:max_len].strip()
        if len(text) > max_len:
            summary += "..."
        return summary

    def _extract_budget_upper_bound(self, text: str) -> float | None:
        lowered = text.lower()

        patterns = [
            r"tra\s+[\d\.\,]+\s+euro\s+e\s+([\d\.\,]+)\s+milioni",
            r"fino\s+a\s+([\d\.\,]+)\s+milioni",
            r"fino a\s+([\d\.\,]+)\s+milione",
            r"progetti fino a\s+([\d\.\,]+)\s+milioni",
            r"progetti fino a\s+([\d\.\,]+)\s+milione",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                raw = match.group(1).replace(".", "").replace(",", ".")
                try:
                    return float(raw) * 1_000_000
                except ValueError:
                    return None

        return None

    def _extract_deadline(self, text: str) -> str | None:
        lowered = text.lower()

        if "non ci sono scadenze" in lowered:
            return "sportello_aperto"

        if "senza graduatorie" in lowered:
            return "sportello_aperto"

        if "a sportello" in lowered:
            return "sportello_aperto"

        return None

    def _infer_topics(self, text: str, title: str) -> List[str]:
        content = f"{title} {text}".lower()
        topics = []

        keyword_topic_pairs = [
            ("startup", "startup"),
            ("startup innovative", "startup innovative"),
            ("innovative", "innovazione"),
            ("innovativa", "innovazione"),
            ("tecnolog", "high-tech"),
            ("digit", "digital innovation"),
            ("ricerca", "research valorisation"),
            ("sviluppo", "business development"),
            ("impresa", "impresa innovativa"),
            ("greenhouse", "CEA"),
            ("controlled environment", "CEA"),
            ("agricolt", "agriculture"),
            ("sensor", "sensors"),
            ("sensori", "sensors"),
            ("ai", "AI"),
            ("artificial intelligence", "AI"),
        ]

        for key, topic in keyword_topic_pairs:
            if key in content and topic not in topics:
                topics.append(topic)

        if not topics:
            topics.append("innovation")

        return topics

    def _page_priority(self, url: str, text: str) -> int:
        score = 0
        lowered_url = url.lower()
        lowered_text = text.lower()

        if lowered_url == self.start_urls[0].lower():
            score += 100

        if "/cosa-finanzia" in lowered_url:
            score += 80

        if "/agevolazioni" in lowered_url:
            score += 70

        if "/chi-si-rivolge" in lowered_url:
            score += 60

        if "/come-presentare-la-domanda" in lowered_url:
            score += 10

        if "startup innovative" in lowered_text:
            score += 15

        if "spese" in lowered_text and "euro" in lowered_text:
            score += 10

        if "non ci sono scadenze" in lowered_text:
            score += 10

        return score

    def _merge_pages_into_single_call(self, pages: List[dict]) -> FundingCall:
        best_page = max(
            pages,
            key=lambda p: self._page_priority(p["url"], p["text"])
        )

        all_text_parts = []
        all_topics = []
        budget_total = None
        deadline_date = None

        for page in pages:
            all_text_parts.append(page["text"])

            for topic in page["topics"]:
                if topic not in all_topics:
                    all_topics.append(topic)

            if budget_total is None and page["budget_total"] is not None:
                budget_total = page["budget_total"]

            if deadline_date is None and page["deadline_date"] is not None:
                deadline_date = page["deadline_date"]

        merged_text = "\n\n".join(all_text_parts)
        merged_summary = self._build_summary(merged_text, max_len=900)

        return FundingCall(
            source="Invitalia",
            source_url=best_page["url"],
            call_id=self.call_id,
            title=self.program,
            summary=merged_summary,
            program=self.program,
            opening_date=None,
            deadline_date=deadline_date,
            budget_total=budget_total,
            funding_type=self.funding_type,
            record_type="call",
            eligible_entities=self.eligible_entities,
            countries=self.countries,
            topics=all_topics,
            raw_text=merged_text,
        )