"""
WINDWATCH — OEM order-intake tracker (YTD).

Pulls turbine-order announcements per OEM, extracts announced MW from
headlines where possible, and aggregates a year-to-date summary.

Sources per OEM:
  1. A direct adapter where the OEM publishes a clean orders page
     (currently Vestas' wind-turbine-orders announcement list).
  2. Google News RSS queries (site-restricted + name-based) as backbone
     and fallback.

Honesty notes surfaced in the UI:
  - Feeds have limited look-back, so "coverage since" is tracked per OEM;
    a YTD total is only complete if coverage reaches back to 1 January.
  - MW is parsed from announcement text. Orders quoted in units-of-turbines
    only are counted as orders but excluded from the MW sum.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import requests
import streamlit as st

from core import fetch_feed, _clean, UA
from sources import gnews

VESTAS_ORDERS_URL = "https://www.vestas.com/en/investor/announcements/wind-turbines-orders"

OEMS = {
    "Vestas": {
        "direct": "vestas",
        "feeds": [gnews('"Vestas" ("MW order" OR "firm order")')],
        "color": "#FF6B1A",
    },
    "Siemens Gamesa": {
        "feeds": [gnews('"Siemens Gamesa" ("order" OR "contract") MW')],
        "color": "#4FC3C7",
    },
    "GE Vernova": {
        "feeds": [gnews('"GE Vernova" wind ("order" OR "contract") MW')],
        "color": "#8FD14F",
    },
    "Nordex": {
        "feeds": [gnews('"Nordex" ("order" OR "orders") MW')],
        "color": "#D9B26A",
    },
    "Goldwind": {
        "feeds": [gnews('"Goldwind" ("order" OR "contract") MW')],
        "color": "#B48DF2",
    },
    "Envision": {
        "feeds": [gnews('"Envision Energy" ("order" OR "contract") MW')],
        "color": "#93A0AF",
    },
    "Mingyang": {
        "feeds": [gnews('"Mingyang" ("order" OR "contract") MW')],
        "color": "#E5586B",
    },
}

ORDER_RE = re.compile(
    r"\border(s|ed)?\b|firm order|conditional order|contract|supply agreement|"
    r"preferred supplier|secures?\b|wins?\b|\bdeal\b|\bawards?\b|\bawarded\b|"
    r"\blands?\b|\bbooks?\b|\bsigns?\b", re.I)

# Things that look like orders but aren't single turbine-supply awards
EXCLUDE_RE = re.compile(
    r"share buy-?back|annual report|interim (?:financial )?report|"
    r"quarterly|capital markets day|AGM|remuneration|"
    r"order intake (?:of|reach|rose|fell|grew|hit|in|for)|"
    r"\bQ[1-4]\s?20\d{2}|first quarter|second quarter|third quarter|fourth quarter|"
    r"half[- ]year|first half|full[- ]year|order backlog|orders? in 20\d{2}", re.I)

NUM_UNIT_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{1,4}(?:[.,]\d{1,3})?)[\s\u00A0-]*(GW|MW)\b", re.I)
ORDER_CONTEXT_RE = re.compile(
    r"\b(order|orders|contract|deal|agreement|project|wind farm|park|intake)\b", re.I)
TURBINE_RATING_RE = re.compile(r"MW\s*(?:wind\s*)?(turbine|platform|model|machine|prototype)s?\b", re.I)


def _to_mw(num: str, unit: str) -> float | None:
    s = num.strip()
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):          # 1,092 → thousands sep
        val = float(s.replace(",", ""))
    else:
        val = float(s.replace(",", "."))                 # 1,2 → European decimal
    if unit.upper() == "GW":
        val *= 1000.0
    return val if 0.5 <= val <= 20000 else None          # sanity bounds


def extract_mw(text: str) -> float | None:
    """Best-effort announced-order MW from an announcement title/summary."""
    candidates = []
    for m in NUM_UNIT_RE.finditer(text):
        # Skip turbine-rating mentions like "15 MW turbines"
        tail = text[m.end(2) - 2: m.end(2) + 24]
        if TURBINE_RATING_RE.match(tail):
            continue
        mw = _to_mw(m.group(1), m.group(2))
        if mw is None:
            continue
        # Strong candidate if an order-ish word appears near the figure
        ctx = text[max(0, m.start() - 30): m.end() + 45]
        candidates.append((bool(ORDER_CONTEXT_RE.search(ctx)), mw))
    if not candidates:
        return None
    strong = [mw for ok, mw in candidates if ok]
    if strong:
        return max(strong)
    return candidates[0][1] if len(candidates) == 1 else None


# ---------------------------------------------------------------------------
# Direct Vestas orders-page adapter (best effort; falls back to feeds)
# ---------------------------------------------------------------------------

VESTAS_LINK_RE = re.compile(
    r'href="(?P<href>[^"]*?)"[^>]*>(?P<title>[^<]{15,220})</a>', re.I)
DATE_RE = re.compile(
    r"\b(\d{1,2})[./\-\s]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[./\-\s,]+(\d{4})\b"
    r"|\b(\d{4})-(\d{2})-(\d{2})\b", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_vestas_orders() -> tuple[list[dict], str]:
    """Scrape the Vestas wind-turbine-orders announcement list. Tolerant, cached 1 h."""
    try:
        resp = requests.get(VESTAS_ORDERS_URL, headers={"User-Agent": UA}, timeout=12)
        resp.raise_for_status()
        html_text = resp.text
    except requests.RequestException as exc:
        return [], f"OFFLINE — {type(exc).__name__}"

    entries, seen = [], set()
    for m in VESTAS_LINK_RE.finditer(html_text):
        title = _clean(m.group("title"), 220)
        if not ORDER_RE.search(title) or EXCLUDE_RE.search(title):
            continue
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        # try to find a date within 400 chars after the link
        when = None
        dm = DATE_RE.search(html_text[m.end(): m.end() + 400])
        if dm:
            try:
                if dm.group(4):  # ISO
                    when = datetime(int(dm.group(4)), int(dm.group(5)), int(dm.group(6)),
                                    tzinfo=timezone.utc)
                else:
                    when = datetime(int(dm.group(3)), MONTHS[dm.group(2)[:3].lower()],
                                    int(dm.group(1)), tzinfo=timezone.utc)
            except (ValueError, KeyError):
                when = None
        href = m.group("href")
        if href.startswith("/"):
            href = "https://www.vestas.com" + href
        entries.append({"title": title, "link": href, "summary": "", "time": when})
    if not entries:
        return [], "PARSE — page layout not recognised, using news fallback"
    return entries[:80], "OK (direct)"


# ---------------------------------------------------------------------------
# Order-level clustering — many articles, one order
# ---------------------------------------------------------------------------

STOP = {
    "with", "from", "that", "this", "will", "wind", "turbine", "turbines",
    "order", "orders", "contract", "secures", "secure", "wins", "win",
    "receives", "receive", "power", "energy", "farm", "project", "deal",
    "firm", "supply", "supplies", "agreement", "megawatt", "gigawatt",
    "announces", "announced", "lands", "signs", "signed", "awarded",
    "large", "major", "another", "more", "first", "biggest",
}

COUNTRY_MAP = {
    "usa": "us", "u.s.": "us", "united states": "us", "america": "us", "american": "us",
    "germany": "de", "german": "de", "australia": "au", "australian": "au",
    "india": "in", "indian": "in", "brazil": "br", "brazilian": "br",
    "canada": "ca", "canadian": "ca", "spain": "es", "spanish": "es",
    "sweden": "se", "swedish": "se", "finland": "fi", "finnish": "fi",
    "poland": "pl", "polish": "pl", "turkey": "tr", "türkiye": "tr", "turkish": "tr",
    "china": "cn", "chinese": "cn", "japan": "jp", "japanese": "jp",
    "south africa": "za", "uk": "gb", "britain": "gb", "british": "gb",
    "france": "fr", "french": "fr", "italy": "it", "italian": "it",
    "greece": "gr", "greek": "gr", "netherlands": "nl", "dutch": "nl",
    "denmark": "dk", "danish": "dk", "norway": "no", "norwegian": "no",
    "vietnam": "vn", "taiwan": "tw", "south korea": "kr", "korean": "kr",
    "argentina": "ar", "chile": "cl", "mexico": "mx", "colombia": "co",
    "saudi arabia": "sa", "egypt": "eg", "morocco": "ma", "kazakhstan": "kz",
    "uzbekistan": "uz", "philippines": "ph", "thailand": "th",
}
COUNTRY_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in COUNTRY_MAP) + r")\b", re.I)

CLUSTER_MW_DAYS = 45      # same OEM + same MW within this window → same order
CLUSTER_TXT_DAYS = 21     # reworded no-MW coverage window
OVERLAP_MIN = 0.6      # |A∩B| / min(|A|,|B|)
MIN_SHARED = 2         # guard against merging on a lone country token


def _tokens(text: str, oem: str) -> set[str]:
    oem_words = set(oem.lower().split())
    return {w for w in re.findall(r"[a-zà-ÿ]{4,}", text.lower())
            if w not in STOP and w not in oem_words}


def _countries(text: str) -> set[str]:
    return {COUNTRY_MAP[m.lower()] for m in COUNTRY_RE.findall(text)}


def _same_mw(a: float, b: float) -> bool:
    return abs(a - b) <= max(3.0, 0.02 * max(a, b))


def cluster_orders(items: list[dict], oem: str) -> list[dict]:
    """Group announcements about the same order. Input items need
    title/link/summary/time/mw/direct. Returns one record per order."""
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    items = sorted(items, key=lambda o: o["time"] or epoch)
    clusters: list[dict] = []
    for it in items:
        blob = f'{it["title"]} {it.get("summary", "")}'
        toks, ctry = _tokens(blob, oem), _countries(blob)
        home = None
        for c in clusters:
            dt_days = (abs((it["time"] - c["time"]).days)
                       if it["time"] and c["time"] else 9999)
            # Rule 1: matching MW figures close in time (country conflict splits)
            if (it["mw"] and c["mw"] and dt_days <= CLUSTER_MW_DAYS
                    and _same_mw(it["mw"], c["mw"])
                    and not (ctry and c["ctry"] and ctry.isdisjoint(c["ctry"]))):
                home = c
                break
            # Rule 2: reworded coverage — token overlap close in time.
            # Overlap coefficient handles short titles vs a grown cluster;
            # MIN_SHARED stops merges on a lone shared token like a country.
            shared = len(toks & c["toks"])
            denom = min(len(toks), len(c["toks"])) or 1
            if (dt_days <= CLUSTER_TXT_DAYS and shared >= MIN_SHARED
                    and shared / denom >= OVERLAP_MIN
                    and not (it["mw"] and c["mw"] and not _same_mw(it["mw"], c["mw"]))):
                home = c
                break
        if home is None:
            clusters.append({**it, "reports": 1, "toks": toks, "ctry": ctry})
        else:
            home["reports"] += 1
            home["toks"] |= toks
            home["ctry"] |= ctry
            if home["mw"] is None:
                home["mw"] = it["mw"]
            # Prefer the OEM's own announcement as the representative
            if it.get("direct") and not home.get("direct"):
                home.update(title=it["title"], link=it["link"],
                            time=it["time"] or home["time"], direct=True)
    for c in clusters:
        c.pop("toks", None)
        c.pop("ctry", None)
    clusters.sort(key=lambda o: o["time"] or epoch, reverse=True)
    return clusters


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", t.lower())[:80]


def collect_oem_orders() -> dict:
    """Returns {oem: {orders: [...], status: [...], n, mw_total, mw_known,
                      earliest, latest}} for the current year. One record per
                      order — multi-outlet coverage is clustered."""
    year = datetime.now(timezone.utc).year
    jan1 = datetime(year, 1, 1, tzinfo=timezone.utc)
    out = {}
    for oem, spec in OEMS.items():
        raw, statuses = [], []
        if spec.get("direct") == "vestas":
            e, s = fetch_vestas_orders()
            raw += [{**x, "direct": True} for x in e]
            statuses.append(f"vestas.com: {s}")
        for url in spec["feeds"]:
            e, s = fetch_feed(url)
            raw += [{**x, "direct": False} for x in e]
            statuses.append(f"news: {s}")

        seen, candidates = set(), []
        for e in raw:
            key = _norm(e["title"])
            if not key or key in seen:      # drop verbatim duplicates first
                continue
            seen.add(key)
            blob = f'{e["title"]} {e.get("summary", "")}'
            if not ORDER_RE.search(blob) or EXCLUDE_RE.search(blob):
                continue
            if e["time"] is not None and e["time"] < jan1:
                continue
            candidates.append({**e, "mw": extract_mw(blob)})

        orders = cluster_orders(candidates, oem)

        dated = [o["time"] for o in orders if o["time"]]
        mw_vals = [o["mw"] for o in orders if o["mw"]]
        out[oem] = {
            "orders": orders,
            "status": statuses,
            "n": len(orders),
            "n_reports": sum(o["reports"] for o in orders),
            "mw_total": sum(mw_vals),
            "mw_known": len(mw_vals),
            "earliest": min(dated) if dated else None,
            "latest": max(dated) if dated else None,
            "color": spec["color"],
            "complete": bool(dated) and min(dated) <= datetime(year, 1, 15, tzinfo=timezone.utc),
        }
    return out
