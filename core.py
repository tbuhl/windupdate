"""
WINDWATCH — core engine.

Fetching, parsing, classification and user-config persistence.
No Streamlit UI code in here except the cache decorator.
"""

from __future__ import annotations

import calendar
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import streamlit as st

from sources import DEFAULT_SOURCES

# --------------------------------------------------------------------------
# User configuration (persisted between sessions)
# --------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".windwatch"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    # Sources that appear on the Highlights page, in display order.
    "starred": [
        "offshorewind_biz",
        "renews",
        "gnews_contracts",
        "gnews_fid",
        "gnews_patents",
        "patentscope_wind",
        "wes_journal",
        "windtech_intl",
        "gnews_tech",
        "gnews_auctions",
        "windeurope",
        "gnews_wind",
    ],
    # Keyword alerts — any hit gets flagged on Highlights.
    "keywords": ["Vestas", "Siemens Gamesa", "floating", "15 MW"],
    # User-added feeds: [{id, name, url, category, note}]
    "custom_sources": [],
    # Default source ids the user has removed from view entirely.
    "hidden": [],
}


def load_config() -> dict:
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT_CONFIG))
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in cfg.items() if k in DEFAULT_CONFIG})
    return merged


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def all_sources(cfg: dict) -> list[dict]:
    """Default sources (minus hidden) + user custom sources."""
    hidden = set(cfg.get("hidden", []))
    out = [s for s in DEFAULT_SOURCES if s["id"] not in hidden]
    out += cfg.get("custom_sources", [])
    return out


def source_by_id(cfg: dict) -> dict[str, dict]:
    return {s["id"]: s for s in all_sources(cfg)}


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

TAG_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("contracts", re.compile(
        r"contract award|awarded|firm order|conditional order|turbine order|"
        r"preferred supplier|supply agreement|service agreement|wins order|"
        r"secures? (?:a )?(?:\d[\d.,]* ?[MG]W|order|contract)|"
        r"final investment decision|financial close|\bFID\b|\bPPA\b|power purchase",
        re.I)),
    ("patents", re.compile(
        r"\bpatents?\b|\bpatented\b|\bUSPTO\b|\bEPO\b|intellectual property|"
        r"\bIP dispute|patent infringement", re.I)),
    ("tech", re.compile(
        r"prototype|type certificate|certification|\bDNV\b|blade test|test bench|"
        r"nacelle|drivetrain|gearbox|direct[- ]drive|recyclable|\bR&D\b|research|"
        r"demonstrator|pilot project|world.s (?:largest|most powerful)|"
        r"\b1[4-9](?:\.\d)? ?MW\b|\b2\d(?:\.\d)? ?MW\b|floating (?:wind|foundation|platform)|"
        r"hydrogen|superconduct|\bLiDAR\b|digital twin", re.I)),
    ("markets", re.compile(
        r"auction|tender|\bCfD\b|contracts? for difference|seabed lease|lease round|"
        r"permit|consent|approval|subsid(?:y|ies)|policy|capacity awarded|"
        r"acquisition|acquires|merger|divest|stake in", re.I)),
]

COMPANIES = [
    "Vestas", "Siemens Gamesa", "Siemens Energy", "GE Vernova", "Nordex",
    "Enercon", "Goldwind", "Envision", "Mingyang", "Windey", "SANY",
    "Ørsted", "Orsted", "RWE", "Equinor", "Iberdrola", "Vattenfall",
    "EDP Renewables", "EDPR", "TotalEnergies", "SSE", "EnBW", "Engie",
    "LM Wind Power", "TPI Composites", "ZF", "Winergy", "Hitachi",
    "Copenhagen Infrastructure Partners", "CIP", "BlueFloat", "Corio",
]
COMPANY_RE = re.compile("|".join(re.escape(c) for c in COMPANIES))

TAG_STRIP_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def classify(text: str) -> list[str]:
    return [tag for tag, pat in TAG_PATTERNS if pat.search(text)]


def find_companies(text: str) -> list[str]:
    hits = []
    for m in COMPANY_RE.findall(text):
        norm = "Ørsted" if m == "Orsted" else m
        if norm not in hits:
            hits.append(norm)
    return hits[:4]


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 WINDWATCH/1.0")


@dataclass
class Item:
    title: str
    link: str
    summary: str
    published: datetime | None
    source_id: str
    source_name: str
    source_category: str
    tags: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    keyword_hits: list[str] = field(default_factory=list)


def _clean(text: str, limit: int = 300) -> str:
    text = html.unescape(TAG_STRIP_RE.sub(" ", text or ""))
    text = WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_feed(url: str) -> tuple[list[dict], str]:
    """Fetch one feed. Returns (raw entries, status). Cached 15 min per URL."""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except requests.RequestException as exc:
        return [], f"OFFLINE — {type(exc).__name__}"
    except Exception as exc:  # noqa: BLE001 — feedparser can raise odd things
        return [], f"PARSE ERROR — {type(exc).__name__}"

    if parsed.bozo and not parsed.entries:
        return [], "PARSE ERROR — not a valid feed"
    if not parsed.entries:
        return [], "EMPTY — feed returned no entries"

    entries = []
    for e in parsed.entries[:40]:
        entries.append({
            "title": _clean(e.get("title", ""), 220),
            "link": e.get("link", ""),
            "summary": _clean(e.get("summary", e.get("description", ""))),
            "time": _entry_time(e),
        })
    return entries, "OK"


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:80]


def collect(cfg: dict, keywords: list[str]) -> tuple[list[Item], dict[str, str]]:
    """Fetch all visible sources, classify, dedupe. Returns (items, status per source)."""
    kw_res = [(kw, re.compile(re.escape(kw), re.I)) for kw in keywords if kw.strip()]
    items: list[Item] = []
    status: dict[str, str] = {}
    seen: set[str] = set()

    for src in all_sources(cfg):
        entries, st_msg = fetch_feed(src["url"])
        status[src["id"]] = st_msg
        for e in entries:
            key = _norm_title(e["title"])
            if not key or key in seen:
                continue
            seen.add(key)
            blob = f'{e["title"]} {e["summary"]}'
            items.append(Item(
                title=e["title"],
                link=e["link"],
                summary=e["summary"],
                published=e["time"],
                source_id=src["id"],
                source_name=src["name"],
                source_category=src["category"],
                tags=classify(blob),
                companies=find_companies(blob),
                keyword_hits=[kw for kw, pat in kw_res if pat.search(blob)],
            ))

    epoch = datetime.fromtimestamp(0, tz=timezone.utc)
    items.sort(key=lambda i: i.published or epoch, reverse=True)
    return items, status


def within_hours(item: Item, hours: int) -> bool:
    if item.published is None:
        return True  # keep undated items visible rather than silently dropping
    age = datetime.now(timezone.utc) - item.published
    return age.total_seconds() <= hours * 3600


def rel_time(dt: datetime | None) -> str:
    if dt is None:
        return "——:——"
    sec = (datetime.now(timezone.utc) - dt).total_seconds()
    if sec < 0:
        sec = 0
    if sec < 3600:
        return f"{int(sec // 60):>2} min"
    if sec < 86400:
        return f"{int(sec // 3600):>2} h"
    return f"{int(sec // 86400):>2} d"
