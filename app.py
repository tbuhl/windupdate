"""
WINDWATCH — daily operations brief for the wind industry.

Run:  streamlit run app.py
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

from core import (
    Item, all_sources, collect, load_config, rel_time, save_config,
    source_by_id, within_hours,
)
from sources import CATEGORIES

st.set_page_config(
    page_title="WINDWATCH — wind industry brief",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Design system — SCADA night-ops instrument panel
# --------------------------------------------------------------------------

TAG_COLORS = {
    "contracts": "#FF6B1A",   # blade-tip signal orange
    "patents":   "#4FC3C7",   # instrument teal
    "tech":      "#8FD14F",   # status green
    "markets":   "#D9B26A",   # ledger sand
    "news":      "#8593A2",   # neutral
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap');

:root {
  --bg: #0B0E12; --panel: #12171E; --panel2: #161C24; --line: #222B36;
  --ink: #E7ECF1; --muted: #8593A2; --dim: #5A6774;
  --orange: #FF6B1A; --teal: #4FC3C7; --green: #8FD14F; --sand: #D9B26A;
  --mono: 'IBM Plex Mono', monospace;
  --sans: 'IBM Plex Sans', sans-serif;
  --cond: 'IBM Plex Sans Condensed', sans-serif;
}

.stApp { background: var(--bg);
  background-image: linear-gradient(var(--line) 1px, transparent 1px),
                    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 48px 48px; background-attachment: fixed;
  background-position: -1px -1px; }
.stApp::before { content:""; position:fixed; inset:0; pointer-events:none;
  background: radial-gradient(ellipse at 50% -10%, rgba(255,107,26,.06), transparent 55%); }

html, body, [class*="css"] { font-family: var(--sans); color: var(--ink); }
h1,h2,h3 { font-family: var(--cond); letter-spacing: .02em; }
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--orange); }

section[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] * { font-family: var(--mono); font-size: 13px; }

/* ---------- masthead ---------- */
.ww-mast { display:flex; align-items:center; gap:18px; padding: 6px 0 14px;
  border-bottom: 2px solid var(--orange); margin-bottom: 4px; }
.ww-rotor { width:54px; height:54px; flex:none; }
.ww-rotor svg { animation: ww-spin 9s linear infinite; transform-origin: 50% 50%; }
@media (prefers-reduced-motion: reduce) { .ww-rotor svg { animation: none; } }
@keyframes ww-spin { to { transform: rotate(360deg); } }
.ww-title { font-family: var(--cond); font-weight:700; font-size: 40px;
  letter-spacing:.06em; line-height:1; }
.ww-title span { color: var(--orange); }
.ww-sub { font-family: var(--mono); font-size:12px; color: var(--muted);
  letter-spacing:.14em; margin-top:6px; text-transform: uppercase; }

/* ---------- eyebrows / section heads ---------- */
.ww-eyebrow { font-family: var(--mono); font-size:12px; letter-spacing:.18em;
  text-transform: uppercase; color: var(--muted); border-bottom:1px solid var(--line);
  padding: 18px 0 6px; margin-bottom: 2px; display:flex; justify-content:space-between; }
.ww-eyebrow b { color: var(--ink); font-weight:600; }
.ww-eyebrow .st { color: var(--dim); letter-spacing:.08em; }

/* ---------- signal board ---------- */
.ww-board { display:grid; grid-template-columns: repeat(5, 1fr); gap:10px; margin:14px 0 4px; }
.ww-cell { background: var(--panel); border:1px solid var(--line); border-top:2px solid var(--c);
  padding:10px 12px 8px; }
.ww-cell .n { font-family: var(--mono); font-size:30px; font-weight:600; color: var(--c); line-height:1; }
.ww-cell .l { font-family: var(--mono); font-size:10.5px; letter-spacing:.14em;
  color: var(--muted); text-transform:uppercase; margin-top:6px; }
@media (max-width: 900px) { .ww-board { grid-template-columns: repeat(2, 1fr); } }

/* ---------- event log rows ---------- */
.ww-log { border:1px solid var(--line); background: var(--panel); margin-bottom: 6px; }
.ww-row { display:flex; gap:14px; padding:10px 14px 10px 10px;
  border-bottom:1px solid var(--line); border-left:3px solid var(--rc, var(--line));
  background: var(--panel); }
.ww-row:last-child { border-bottom:none; }
.ww-row:hover { background: var(--panel2); }
.ww-row.hit { border-left-color: var(--orange); background: rgba(255,107,26,.05); }
.ww-t { font-family: var(--mono); font-size:12px; color: var(--dim); flex:none;
  width:52px; text-align:right; padding-top:3px; }
.ww-row.hit .ww-t { color: var(--orange); }
.ww-b { min-width:0; }
.ww-h { font-size:15px; font-weight:600; line-height:1.35; }
.ww-s { font-size:13px; color: var(--muted); line-height:1.45; margin-top:3px; }
.ww-m { font-family: var(--mono); font-size:10.5px; letter-spacing:.08em; color: var(--dim);
  margin-top:6px; display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center; }
.ww-tag { color: var(--tc); border:1px solid var(--tc); padding:1px 6px; }
.ww-kw { color: var(--orange); font-weight:600; }
.ww-co { color: var(--muted); }

/* ---------- status LEDs ---------- */
.ww-led { display:inline-block; width:8px; height:8px; border-radius:50%;
  margin-right:8px; vertical-align:middle; }
.ww-ok  { background: var(--green); box-shadow:0 0 6px var(--green); }
.ww-bad { background: var(--orange); box-shadow:0 0 6px var(--orange); }
.ww-src { font-family: var(--mono); font-size:12.5px; padding:7px 4px;
  border-bottom:1px solid var(--line); display:flex; gap:10px; align-items:baseline; }
.ww-src .nm { color: var(--ink); min-width:230px; }
.ww-src .stt { color: var(--dim); }

/* Streamlit widget restyling */
.stButton button { font-family: var(--mono); letter-spacing:.08em; text-transform: uppercase;
  background: var(--panel); color: var(--ink); border:1px solid var(--line); border-radius:0; }
.stButton button:hover { border-color: var(--orange); color: var(--orange); }
div[data-baseweb="select"], .stTextInput input, .stTextArea textarea {
  font-family: var(--mono) !important; border-radius:0 !important; }
</style>
"""

ROTOR_SVG = """
<div class="ww-rotor"><svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<g fill="#FF6B1A"><circle cx="50" cy="50" r="6"/>
<path d="M50 50 L46 14 Q50 6 54 14 Z"/>
<path d="M50 50 L81 66 Q86 74 77 73 L50 56 Z" transform="rotate(-30 50 50)"/>
<path d="M50 50 L19 66 Q14 74 23 73 L50 56 Z" transform="rotate(30 50 50)"/></g>
<circle cx="50" cy="50" r="47" fill="none" stroke="#222B36" stroke-width="2"/>
</svg></div>
"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def primary_tag(item: Item) -> str:
    for t in ("contracts", "patents", "tech", "markets"):
        if t in item.tags:
            return t
    return item.source_category if item.source_category in TAG_COLORS else "news"


def render_rows(items: list[Item], show_source: bool = True) -> str:
    if not items:
        return ('<div class="ww-log"><div class="ww-row"><div class="ww-b">'
                '<div class="ww-s">No items in this window. Widen the time window, '
                'check the Sources page, or press REFRESH.</div></div></div></div>')
    rows = []
    for it in items:
        tag = primary_tag(it)
        color = TAG_COLORS[tag]
        hit = " hit" if it.keyword_hits else ""
        meta = [f'<span class="ww-tag" style="--tc:{color}">{CATEGORIES.get(tag, {"short": tag.upper()})["short"]}</span>']
        if show_source:
            meta.append(f'<span>{esc(it.source_name)}</span>')
        if it.keyword_hits:
            meta.append('<span class="ww-kw">▲ ' + esc(" · ".join(it.keyword_hits)) + '</span>')
        if it.companies:
            meta.append('<span class="ww-co">' + esc(" / ".join(it.companies)) + '</span>')
        summary = f'<div class="ww-s">{esc(it.summary)}</div>' if it.summary and it.summary != it.title else ""
        rows.append(
            f'<div class="ww-row{hit}" style="--rc:{color}">'
            f'<div class="ww-t">{rel_time(it.published)}</div>'
            f'<div class="ww-b"><div class="ww-h"><a href="{esc(it.link)}" target="_blank">{esc(it.title)}</a></div>'
            f'{summary}<div class="ww-m">{"".join(meta)}</div></div></div>'
        )
    return '<div class="ww-log">' + "".join(rows) + "</div>"


def eyebrow(label: str, right: str = "") -> None:
    st.markdown(f'<div class="ww-eyebrow"><b>{esc(label)}</b><span class="st">{esc(right)}</span></div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------
# App state
# --------------------------------------------------------------------------

if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
cfg = st.session_state.cfg

st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**WINDWATCH / NAV**")
    page = st.radio("Page", ["HIGHLIGHTS", "ALL ITEMS", "SOURCES & SETUP"],
                    label_visibility="collapsed")
    st.divider()
    window = st.selectbox("Time window", [24, 48, 72, 168, 720], index=1,
                          format_func=lambda h: f"LAST {h} H" if h < 168 else f"LAST {h//24} D")
    query = st.text_input("Search", placeholder="filter titles + summaries…")
    if st.button("↻  REFRESH FEEDS", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Polling sources…"):
    items, status = collect(cfg, cfg["keywords"])

online = sum(1 for s in status.values() if s == "OK")
if query.strip():
    q = query.strip().lower()
    items = [i for i in items if q in i.title.lower() or q in i.summary.lower()]
windowed = [i for i in items if within_hours(i, window)]

# Masthead
now = datetime.now(timezone.utc)
st.markdown(
    f'<div class="ww-mast">{ROTOR_SVG}<div>'
    f'<div class="ww-title">WIND<span>WATCH</span></div>'
    f'<div class="ww-sub">Daily operations brief · {now:%a %d %b %Y · %H:%M} UTC · '
    f'{online}/{len(status)} sources online · {len(windowed)} items in window</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

if page == "HIGHLIGHTS":
    # Signal board — 24 h counts by class
    day = [i for i in items if within_hours(i, 24)]
    counts = {t: 0 for t in TAG_COLORS}
    for i in day:
        counts[primary_tag(i)] += 1
    cells = "".join(
        f'<div class="ww-cell" style="--c:{TAG_COLORS[t]}"><div class="n">{counts[t]:02d}</div>'
        f'<div class="l">{CATEGORIES[t]["label"]} / 24H</div></div>'
        for t in ("contracts", "patents", "tech", "markets", "news")
    )
    st.markdown(f'<div class="ww-board">{cells}</div>', unsafe_allow_html=True)

    # Keyword signals
    kw_hits = [i for i in windowed if i.keyword_hits][:12]
    eyebrow("KEYWORD SIGNALS", "watch: " + (", ".join(cfg["keywords"]) or "none set"))
    st.markdown(render_rows(kw_hits), unsafe_allow_html=True)

    # Starred source sections, two columns, in the user's order
    starred = [sid for sid in cfg["starred"] if sid in source_by_id(cfg)]
    if not starred:
        st.info("No sources starred yet — pick your favourites on the SOURCES & SETUP page.")
    src_map = source_by_id(cfg)
    cols = st.columns(2)
    for n, sid in enumerate(starred):
        with cols[n % 2]:
            src = src_map[sid]
            sub = status.get(sid, "—")
            eyebrow(src["name"], sub if sub != "OK" else CATEGORIES[src["category"]]["label"])
            block = [i for i in windowed if i.source_id == sid][:5]
            st.markdown(render_rows(block, show_source=False), unsafe_allow_html=True)

elif page == "ALL ITEMS":
    cat = st.radio("Class filter",
                   ["ALL"] + list(CATEGORIES),
                   horizontal=True, label_visibility="collapsed",
                   format_func=lambda c: "ALL" if c == "ALL" else CATEGORIES[c]["short"])
    shown = windowed if cat == "ALL" else [i for i in windowed if primary_tag(i) == cat]
    eyebrow("EVENT LOG", f"{len(shown)} items · newest first")
    st.markdown(render_rows(shown[:120]), unsafe_allow_html=True)

else:  # SOURCES & SETUP
    eyebrow("FEED STATUS", f"{online}/{len(status)} online · cache 15 min")
    rows = []
    for src in all_sources(cfg):
        s = status.get(src["id"], "—")
        led = "ww-ok" if s == "OK" else "ww-bad"
        rows.append(f'<div class="ww-src"><span><span class="ww-led {led}"></span></span>'
                    f'<span class="nm">{esc(src["name"])}</span>'
                    f'<span class="stt">{esc(CATEGORIES[src["category"]]["short"])} · {esc(s)}</span></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)

    eyebrow("COMPOSE YOUR HIGHLIGHT PAGE", "selection order = display order")
    src_map = source_by_id(cfg)
    starred_valid = [s for s in cfg["starred"] if s in src_map]
    picked = st.multiselect(
        "Starred sources", options=list(src_map),
        default=starred_valid,
        format_func=lambda sid: src_map[sid]["name"],
        label_visibility="collapsed",
    )

    eyebrow("KEYWORD WATCHLIST", "one per line — flags ▲ on highlights")
    kw_text = st.text_area("Keywords", value="\n".join(cfg["keywords"]),
                           height=120, label_visibility="collapsed")

    if st.button("SAVE SETUP"):
        cfg["starred"] = picked
        cfg["keywords"] = [k.strip() for k in kw_text.splitlines() if k.strip()]
        save_config(cfg)
        st.success("Setup saved to ~/.windwatch/config.json")
        st.rerun()

    eyebrow("ADD A CUSTOM FEED", "any RSS or Atom URL")
    c1, c2, c3 = st.columns([2, 3, 1.4])
    with c1:
        new_name = st.text_input("Name", placeholder="e.g. Recharge — wind")
    with c2:
        new_url = st.text_input("Feed URL", placeholder="https://…/feed")
    with c3:
        new_cat = st.selectbox("Class", list(CATEGORIES),
                               format_func=lambda c: CATEGORIES[c]["short"])
    if st.button("ADD FEED") and new_name.strip() and new_url.strip():
        sid = "custom_" + "".join(ch for ch in new_name.lower() if ch.isalnum())[:24]
        if sid in src_map:
            st.warning("A source with that name already exists.")
        else:
            cfg["custom_sources"].append({
                "id": sid, "name": new_name.strip(), "url": new_url.strip(),
                "category": new_cat, "note": "custom",
            })
            cfg["starred"].append(sid)
            save_config(cfg)
            st.cache_data.clear()
            st.rerun()

    if cfg["custom_sources"]:
        eyebrow("REMOVE A CUSTOM FEED")
        rm = st.selectbox("Remove", ["—"] + [s["id"] for s in cfg["custom_sources"]],
                          format_func=lambda sid: "—" if sid == "—" else
                          next(s["name"] for s in cfg["custom_sources"] if s["id"] == sid),
                          label_visibility="collapsed")
        if rm != "—" and st.button("REMOVE FEED"):
            cfg["custom_sources"] = [s for s in cfg["custom_sources"] if s["id"] != rm]
            cfg["starred"] = [s for s in cfg["starred"] if s != rm]
            save_config(cfg)
            st.rerun()
