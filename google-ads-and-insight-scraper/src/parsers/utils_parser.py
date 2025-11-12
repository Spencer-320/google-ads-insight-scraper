from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

AD_URL_REGEX = re.compile(
    r"https?://(?:www\.)?adstransparency\.google\.com/advertiser/(?P<advertiser>AR[0-9]+)/creative/(?P<creative>CR[0-9]+)/?",
    re.IGNORECASE,
)

@dataclass
class FetchResult:
    url: str
    status: int
    html: Optional[str]
    final_url: str

@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def fetch_html(url: str, user_agent: str, timeout_sec: float) -> FetchResult:
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    resp = requests.get(url, headers=headers, timeout=timeout_sec, allow_redirects=True)
    html = resp.text if resp.ok else None
    return FetchResult(url=url, status=resp.status_code, html=html, final_url=str(resp.url))

def parse_ids_from_ad_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract (advertiser_id, creative_id) from a Google Ads Transparency ad URL.
    """
    m = AD_URL_REGEX.match(url.strip())
    if not m:
        return None, None
    return m.group("advertiser"), m.group("creative")

def parse_open_graph(html: str) -> dict:
    """
    Pull a few useful OG tags if present (best-effort).
    """
    soup = BeautifulSoup(html, "html.parser")
    def _og(name: str) -> Optional[str]:
        tag = soup.find("meta", property=f"og:{name}") or soup.find("meta", attrs={"name": f"og:{name}"})
        return tag.get("content") if tag and tag.get("content") else None

    return {
        "title": _og("title"),
        "description": _og("description"),
        "image": _og("image"),
    }

def safe_currency(spend_range: Optional[str]) -> str:
    # Best-effort: USD default when unknown
    return "USD"