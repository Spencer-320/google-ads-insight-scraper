from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

def _derive_regions_from_ads(ads: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate simple region stats from ad records' `ad_visible_countries`.
    """
    region_counter = Counter()
    for ad in ads:
        countries = ad.get("ad_visible_countries") or []
        if not countries:
            continue
        for c in countries:
            region_counter[c] += 1

    regions = []
    for country, count in region_counter.items():
        regions.append({
            "country": country,
            "ads_count": count,
            "estimated_spend": 0,
        })
    return {"regions": regions}

def _guess_query_terms(start_urls: List[str]) -> List[str]:
    terms = []
    for u in start_urls:
        q = parse_qs(urlparse(u).query)
        # Attempt to capture "q", "query", or path fragments as terms
        val = q.get("q") or q.get("query")
        if val:
            terms.extend(val)
        else:
            # fallback to last path segment
            parts = [p for p in urlparse(u).path.split("/") if p]
            if parts:
                terms.append(parts[-1])
    # deduplicate while preserving order
    seen = set()
    out = []
    for t in terms:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

def build_insights_from_ads_or_search(
    ads_records: Optional[List[Dict]],
    start_urls: Optional[List[str]],
) -> Dict:
    """
    Construct a pragmatic insights JSON using either:
    - the already extracted ads (preferred), or
    - search URLs (derive basic metadata)
    """
    ads_records = ads_records or []
    start_urls = start_urls or []

    insights: Dict = {
        "insights_total_ads": len(ads_records),
        "insights_total_ads_spend": 0,  # Unknown without authenticated/API data
        "insights_advertisers": [],
        "insights_regions": [],
        "source": "ads" if ads_records else "search",
        "search_terms": _guess_query_terms(start_urls) if not ads_records else [],
    }

    # Advertiser-level grouping
    advertisers_map: Dict[str, Dict] = defaultdict(lambda: {"advertiser_id": "", "advertiser_name": "", "ads_count": 0, "estimated_spend": 0})
    for ad in ads_records:
        adv_id = ad.get("ad_advertiser_id") or ""
        adv_name = ad.get("ad_advertiser_name") or ""
        key = adv_id or adv_name or "unknown"
        advertisers_map[key]["advertiser_id"] = adv_id
        advertisers_map[key]["advertiser_name"] = adv_name
        advertisers_map[key]["ads_count"] += 1

    insights["insights_advertisers"] = list(advertisers_map.values())

    # Region aggregation
    regions = _derive_regions_from_ads(ads_records)
    insights["insights_regions"] = regions.get("regions", [])

    return insights