from __future__ import annotations

import time
from typing import Dict, List

from .utils_parser import fetch_html, parse_ids_from_ad_url, parse_open_graph, safe_currency

def _estimate_type_from_og(og: dict) -> str:
    # If an image is present, assume image; otherwise unknown.
    if og.get("image"):
        return "image"
    return "unknown"

def extract_from_ad_urls(
    ad_urls: List[str],
    user_agent: str,
    timeout_sec: float,
    max_retries: int,
) -> List[Dict]:
    """
    For each ad URL:
    - Parse advertiser and creative IDs from the URL path.
    - Attempt to fetch HTML and extract OG tags (headline/description/image).
    - Populate a realistic record even if the page is JS-rendered or blocked.
    """
    records: List[Dict] = []

    for url in ad_urls:
        advertiser_id, creative_id = parse_ids_from_ad_url(url)
        # Fallback IDs if not matched: last path segments
        if not advertiser_id or not creative_id:
            parts = [p for p in url.split("/") if p]
            creative_id = parts[-1] if parts else None
            advertiser_id = parts[-3] if len(parts) >= 3 else None

        og = {}
        try:
            # Best-effort fetch (may return login/JS shell; that's fine for OG extraction)
            result = fetch_html(url, user_agent=user_agent, timeout_sec=timeout_sec)
            if result.html:
                og = parse_open_graph(result.html)
        except Exception:
            # Non-fatal: continue with minimal info
            og = {}

        now = int(time.time())
        record = {
            "ad_advertiser_id": advertiser_id or "",
            "ad_advertiser_name": "",  # Name typically requires JS-rendered content; left blank if unavailable
            "ad_id": creative_id or "",
            "ad_type": _estimate_type_from_og(og),
            # Without trusted server data, we cannot know real dates; include None to signal unknown.
            "ad_start_date": None,
            "ad_end_date": None,
            "ad_number_days_running": None,
            "ad_visible_countries": [],
            "ad_image_link": og.get("image"),
            "ad_spend_range": None,           # Political spend ranges would require API/JS payloads
            "ad_impressions_range": None,     # Same as above
            "ad_spend_currency": safe_currency(None),
            "ad_url": url,
            "headline": og.get("title"),
            "description": og.get("description"),
        }
        records.append(record)

    return records