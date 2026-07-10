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
# Design system — dark control-room, modern grotesque type
# --------------------------------------------------------------------------

TAG_COLORS = {
    "contracts": "#FF6B1A",   # blade-tip signal orange
    "patents":   "#4FC3C7",   # instrument teal
    "papers":    "#B48DF2",   # journal violet
    "tech":      "#8FD14F",   # status green
    "markets":   "#D9B26A",   # ledger sand
    "news":      "#8A97A8",   # neutral
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --bg: #0B0E12; --panel: #12171E; --panel2: #171E27; --line: #232B36;
  --ink: #E9EDF2; --muted: #93A0AF; --dim: #5E6B79;
  --orange: #FF6B1A;
  --body: 'Inter', system-ui, sans-serif;
  --disp: 'Space Grotesk', 'Inter', sans-serif;
}

.stApp { background: var(--bg); }
.stApp::before { content:""; position:fixed; inset:0; pointer-events:none;
  background: radial-gradient(ellipse at 50% -12%, rgba(255,107,26,.07), transparent 55%); }

html, body, [class*="css"] { font-family: var(--body); color: var(--ink); }
h1,h2,h3 { font-family: var(--disp); }
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--orange); }

section[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] * { font-family: var(--body); font-size: 13.5px; }

/* ---------- masthead ---------- */
.ww-mast { display:flex; align-items:center; gap:18px; padding: 8px 0 16px;
  border-bottom: 2px solid var(--orange); margin-bottom: 4px; }
.ww-rotor { width:56px; height:56px; flex:none; }
.ww-rotor svg { animation: ww-spin 10s linear infinite; transform-origin: 50% 50%; }
@media (prefers-reduced-motion: reduce) { .ww-rotor svg { animation: none; } }
@keyframes ww-spin { to { transform: rotate(360deg); } }
.ww-title { font-family: var(--disp); font-weight:700; font-size: 38px;
  letter-spacing:.04em; line-height:1; }
.ww-title span { color: var(--orange); }
.ww-sub { font-size:12.5px; font-weight:500; color: var(--muted);
  letter-spacing:.09em; margin-top:7px; text-transform: uppercase; }

/* ---------- section heads ---------- */
.ww-eyebrow { display:flex; justify-content:space-between; align-items:baseline;
  border-bottom:1px solid var(--line); padding: 20px 0 7px; margin-bottom: 2px; }
.ww-eyebrow b { font-family: var(--disp); font-weight:600; font-size:17px;
  letter-spacing:.02em; color: var(--ink);
  border-left: 3px solid var(--sc, var(--orange)); padding-left: 9px; }
.ww-eyebrow .st { font-size:11.5px; font-weight:500; letter-spacing:.1em;
  text-transform:uppercase; color: var(--dim); }

/* ---------- signal board ---------- */
.ww-board { display:grid; grid-template-columns: repeat(6, 1fr); gap:10px; margin:16px 0 4px; }
.ww-cell { background: var(--panel); border:1px solid var(--line); border-top:2px solid var(--c);
  padding:11px 13px 9px; }
.ww-cell .n { font-family: var(--disp); font-size:30px; font-weight:700; color: var(--c);
  line-height:1; font-variant-numeric: tabular-nums; }
.ww-cell .l { font-size:10.5px; font-weight:600; letter-spacing:.13em;
  color: var(--muted); text-transform:uppercase; margin-top:7px; }
@media (max-width: 1000px) { .ww-board { grid-template-columns: repeat(3, 1fr); } }

/* ---------- event log rows ---------- */
.ww-log { border:1px solid var(--line); background: var(--panel); margin-bottom: 6px; }
.ww-row { display:flex; gap:14px; padding:11px 14px 11px 10px;
  border-bottom:1px solid var(--line); border-left:3px solid var(--rc, var(--line)); }
.ww-row:last-child { border-bottom:none; }
.ww-row:hover { background: var(--panel2); }
.ww-row.hit { border-left-color: var(--orange); background: rgba(255,107,26,.05); }
.ww-row.old { opacity:.62; }
.ww-t { font-size:12px; font-weight:500; color: var(--dim); flex:none;
  width:50px; text-align:right; padding-top:3px; font-variant-numeric: tabular-nums; }
.ww-row.hit .ww-t { color: var(--orange); }
.ww-b { min-width:0; }
.ww-h { font-size:15px; font-weight:600; line-height:1.4; letter-spacing:-.005em; }
.ww-s { font-size:13px; color: var(--muted); line-height:1.5; margin-top:3px; }
.ww-m { font-size:10.5px; font-weight:600; letter-spacing:.09em; text-transform:uppercase;
  color: var(--dim); margin-top:7px; display:flex; flex-wrap:wrap; gap:6px 12px; align-items:center; }
.ww-tag { color: var(--tc); border:1px solid var(--tc); padding:1.5px 7px; border-radius:2px; }
.ww-oldflag { color: #D9B26A; border:1px dashed #D9B26A; padding:1.5px 7px; border-radius:2px; }
.ww-kw { color: var(--orange); }
.ww-co { color: var(--muted); text-transform:none; letter-spacing:.02em; }

/* ---------- status LEDs ---------- */
.ww-led { display:inline-block; width:8px; height:8px; border-radius:50%;
  margin-right:8px; vertical-align:middle; }
.ww-ok  { background: #8FD14F; box-shadow:0 0 6px #8FD14F; }
.ww-bad { background: var(--orange); box-shadow:0 0 6px var(--orange); }
.ww-src { font-size:13px; padding:8px 4px; border-bottom:1px solid var(--line);
  display:flex; gap:10px; align-items:baseline; }
.ww-src .nm { color: var(--ink); font-weight:500; min-width:250px; }
.ww-src .stt { color: var(--dim); font-size:11.5px; letter-spacing:.06em; text-transform:uppercase; }

/* Streamlit widget restyling */
.stButton button { font-family: var(--body); font-weight:600; font-size:12.5px;
  letter-spacing:.08em; text-transform: uppercase;
  background: var(--panel); color: var(--ink); border:1px solid var(--line); border-radius:3px; }
.stButton button:hover { border-color: var(--orange); color: var(--orange); }
div[data-baseweb="select"], .stTextInput input, .stTextArea textarea { border-radius:3px !important; }
</style>
"""

# Three blades at exact 120° spacing, tapered from hub to tip
ROTOR_SVG = """
<div class="ww-rotor"><svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<g fill="#FF6B1A">
<path d="M48.6 46 C46.2 34 46.8 20 50 8.5 C53.2 20 53.8 34 51.4 46 Z"/>
<path d="M48.6 46 C46.2 34 46.8 20 50 8.5 C53.2 20 53.8 34 51.4 46 Z" transform="rotate(120 50 50)"/>
<path d="M48.6 46 C46.2 34 46.8 20 50 8.5 C53.2 20 53.8 34 51.4 46 Z" transform="rotate(240 50 50)"/>
<circle cx="50" cy="50" r="6.5"/>
</g>
<circle cx="50" cy="50" r="47" fill="none" stroke="#232B36" stroke-width="2"/>
</svg></div>
"""

SECTION_ORDER = ["contracts", "patents", "papers", "tech", "markets", "news"]
MIN_PER_SECTION = 5

WINDOWS = {168: "1 WEEK", 720: "1 MONTH", 8760: "1 YEAR"}


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def primary_tag(item: Item) -> str:
    if item.source_category == "papers":
        return "papers"
    for t in ("contracts", "patents", "tech", "markets"):
        if t in item.tags:
            return t
    return item.source_category if item.source_category in TAG_COLORS else "news"


def render_rows(items: list[Item], window_h: int | None = None,
                show_source: bool = True, show_class: bool = True) -> str:
    if not items:
        return ('<div class="ww-log"><div class="ww-row"><div class="ww-b">'
                '<div class="ww-s">Nothing here yet — check the Sources page for '
                'offline feeds, or press REFRESH.</div></div></div></div>')
    rows = []
    for it in items:
        tag = primary_tag(it)
        color = TAG_COLORS[tag]
        outside = window_h is not None and not within_hours(it, window_h)
        cls = " hit" if it.keyword_hits else ""
        cls += " old" if outside else ""
        meta = []
        if show_class:
            meta.append(f'<span class="ww-tag" style="--tc:{color}">'
                        f'{CATEGORIES.get(tag, {"short": tag.upper()})["short"]}</span>')
        if outside:
            meta.append('<span class="ww-oldflag">Older than window</span>')
        if show_source:
            meta.append(f'<span>{esc(it.source_name)}</span>')
        if it.keyword_hits:
            meta.append('<span class="ww-kw">▲ ' + esc(" · ".join(it.keyword_hits)) + '</span>')
        if it.companies:
            meta.append('<span class="ww-co">' + esc(" / ".join(it.companies)) + '</span>')
        summary = f'<div class="ww-s">{esc(it.summary)}</div>' if it.summary and it.summary != it.title else ""
        rows.append(
            f'<div class="ww-row{cls}" style="--rc:{color}">'
            f'<div class="ww-t">{rel_time(it.published)}</div>'
            f'<div class="ww-b"><div class="ww-h"><a href="{esc(it.link)}" target="_blank">{esc(it.title)}</a></div>'
            f'{summary}<div class="ww-m">{"".join(meta)}</div></div></div>'
        )
    return '<div class="ww-log">' + "".join(rows) + "</div>"


def eyebrow(label: str, right: str = "", color: str = "#FF6B1A") -> None:
    st.markdown(f'<div class="ww-eyebrow" style="--sc:{color}"><b>{esc(label)}</b>'
                f'<span class="st">{esc(right)}</span></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# App state
# --------------------------------------------------------------------------

if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
cfg = st.session_state.cfg

st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**WINDWATCH**")
    page = st.radio("Page", ["HIGHLIGHTS", "ALL ITEMS", "OEM ORDERS YTD", "SOURCES & SETUP"],
                    label_visibility="collapsed")
    st.divider()
    window = st.selectbox("Time window", list(WINDOWS), index=0,
                          format_func=WINDOWS.get)
    query = st.text_input("Search", placeholder="filter titles + summaries…")
    if st.button("↻  REFRESH FEEDS", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if page == "OEM ORDERS YTD":
    items, status = [], {}
else:
    with st.spinner("Polling sources…"):
        items, status = collect(cfg, cfg["keywords"])

online = sum(1 for s in status.values() if s == "OK")
if query.strip():
    q = query.strip().lower()
    items = [i for i in items if q in i.title.lower() or q in i.summary.lower()]
windowed = [i for i in items if within_hours(i, window)]

# Masthead
now = datetime.now(timezone.utc)
sub = (f"OEM order intake · year-to-date {now.year}"
       if page == "OEM ORDERS YTD" else
       f"Daily operations brief · {online}/{len(status)} sources online · "
       f"{len(windowed)} items in window")
st.markdown(
    f'<div class="ww-mast">{ROTOR_SVG}<div>'
    f'<div class="ww-title">WIND<span>WATCH</span></div>'
    f'<div class="ww-sub">{now:%a %d %b %Y · %H:%M} UTC · {sub}</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

if page == "HIGHLIGHTS":
    # Pool = starred sources only (your composed page); fall back to everything
    starred = set(cfg["starred"])
    pool = [i for i in items if i.source_id in starred] if starred else items

    # Signal board — 24 h counts by class
    day = [i for i in pool if within_hours(i, 24)]
    counts = {t: 0 for t in TAG_COLORS}
    for i in day:
        counts[primary_tag(i)] += 1
    cells = "".join(
        f'<div class="ww-cell" style="--c:{TAG_COLORS[t]}"><div class="n">{counts[t]:02d}</div>'
        f'<div class="l">{CATEGORIES[t]["short"]} / 24H</div></div>'
        for t in SECTION_ORDER
    )
    st.markdown(f'<div class="ww-board">{cells}</div>', unsafe_allow_html=True)

    # Keyword signals
    kw_hits = [i for i in pool if i.keyword_hits and within_hours(i, window)][:10]
    eyebrow("Keyword signals", "watch: " + (", ".join(cfg["keywords"]) or "none set"))
    st.markdown(render_rows(kw_hits, window_h=window), unsafe_allow_html=True)

    # Category sections — min 5 entries each, backfilled + flagged beyond window
    cols = st.columns(2)
    for n, cat in enumerate(SECTION_ORDER):
        cat_items = [i for i in pool if primary_tag(i) == cat]
        in_win = [i for i in cat_items if within_hours(i, window)]
        section = in_win[:8]
        if len(section) < MIN_PER_SECTION:
            older = [i for i in cat_items if i not in section]
            section += older[: MIN_PER_SECTION - len(section)]
        with cols[n % 2]:
            eyebrow(CATEGORIES[cat]["label"],
                    f"{len(in_win)} in window", TAG_COLORS[cat])
            st.markdown(render_rows(section, window_h=window, show_class=False),
                        unsafe_allow_html=True)

elif page == "ALL ITEMS":
    cat = st.radio("Class filter", ["ALL"] + SECTION_ORDER,
                   horizontal=True, label_visibility="collapsed",
                   format_func=lambda c: "ALL" if c == "ALL" else CATEGORIES[c]["short"])
    shown = windowed if cat == "ALL" else [i for i in windowed if primary_tag(i) == cat]
    eyebrow("Event log", f"{len(shown)} items · newest first")
    st.markdown(render_rows(shown[:150], window_h=window), unsafe_allow_html=True)

elif page == "OEM ORDERS YTD":
    from oem import collect_oem_orders

    with st.spinner("Polling OEM announcement streams…"):
        data = collect_oem_orders()

    total_mw = sum(d["mw_total"] for d in data.values())
    total_n = sum(d["n"] for d in data.values())
    ranked = sorted(data.items(), key=lambda kv: kv[1]["mw_total"], reverse=True)
    max_mw = max((d["mw_total"] for d in data.values()), default=0) or 1

    eyebrow("Announced order intake — top OEMs",
            f"YTD {now.year} · {total_n} announcements · {total_mw:,.0f} MW identified")

    # Horizontal bar board, one row per OEM
    bars = []
    for oem_name, d in ranked:
        pct = 100 * d["mw_total"] / max_mw
        cov = (f"since {d['earliest']:%d %b}" if d["earliest"] else "no dated items")
        flag = "" if d["complete"] else ' <span class="ww-oldflag">Partial coverage</span>'
        mw_lbl = f'{d["mw_total"]:,.0f} MW' if d["mw_total"] else "MW n/a"
        bars.append(
            f'<div class="ww-obar"><div class="hd"><span class="nm">{esc(oem_name)}</span>'
            f'<span class="val" style="color:{d["color"]}">{mw_lbl}'
            f' <span class="n">· {d["n"]} orders · {d["mw_known"]}/{d["n"]} with MW · {cov}{flag}</span></span></div>'
            f'<div class="tr"><div class="fl" style="width:{pct:.1f}%;background:{d["color"]}"></div></div></div>'
        )
    st.markdown(
        '<style>.ww-obar{margin:14px 0}.ww-obar .hd{display:flex;justify-content:space-between;'
        'align-items:baseline;font-size:14px;font-weight:600;margin-bottom:5px}'
        '.ww-obar .val{font-variant-numeric:tabular-nums}'
        '.ww-obar .n{color:var(--dim);font-size:11px;font-weight:500;letter-spacing:.05em;text-transform:uppercase}'
        '.ww-obar .tr{height:10px;background:var(--panel);border:1px solid var(--line)}'
        '.ww-obar .fl{height:100%}</style>' + "".join(bars),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ww-s" style="margin-top:10px">MW figures are parsed from announcement '
        'headlines; orders quoted only in turbine counts are tallied but excluded from the MW sum. '
        'News feeds have limited look-back — an OEM is marked <i>partial coverage</i> unless its '
        'stream reaches back to mid-January. Vestas is additionally pulled directly from '
        'vestas.com/…/wind-turbines-orders when reachable.</div>',
        unsafe_allow_html=True,
    )

    # Per-OEM announcement lists
    for oem_name, d in ranked:
        with st.expander(f"{oem_name} — {d['n']} announcements  ·  feed: "
                         + " / ".join(d["status"])):
            if not d["orders"]:
                st.markdown('<div class="ww-s">No order announcements found YTD — '
                            'source may be offline.</div>', unsafe_allow_html=True)
            rows = []
            for o in d["orders"][:40]:
                when = f'{o["time"]:%d %b}' if o["time"] else "—"
                mw = f'{o["mw"]:,.0f} MW' if o["mw"] else "MW n/a"
                rows.append(
                    f'<div class="ww-row" style="--rc:{d["color"]}">'
                    f'<div class="ww-t">{when}</div><div class="ww-b">'
                    f'<div class="ww-h"><a href="{esc(o["link"])}" target="_blank">{esc(o["title"])}</a></div>'
                    f'<div class="ww-m"><span class="ww-tag" style="--tc:{d["color"]}">{mw}</span></div>'
                    f'</div></div>')
            if rows:
                st.markdown('<div class="ww-log">' + "".join(rows) + "</div>",
                            unsafe_allow_html=True)

else:  # SOURCES & SETUP
    eyebrow("Feed status", f"{online}/{len(status)} online · cache 15 min")
    rows = []
    for src in all_sources(cfg):
        s = status.get(src["id"], "—")
        led = "ww-ok" if s == "OK" else "ww-bad"
        rows.append(f'<div class="ww-src"><span><span class="ww-led {led}"></span></span>'
                    f'<span class="nm">{esc(src["name"])}</span>'
                    f'<span class="stt">{esc(CATEGORIES[src["category"]]["short"])} · {esc(s)}</span></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)

    eyebrow("Compose your highlight page", "these sources feed the highlights")
    src_map = source_by_id(cfg)
    starred_valid = [s for s in cfg["starred"] if s in src_map]
    picked = st.multiselect(
        "Starred sources", options=list(src_map),
        default=starred_valid,
        format_func=lambda sid: src_map[sid]["name"],
        label_visibility="collapsed",
    )

    eyebrow("Keyword watchlist", "one per line — flags ▲ on highlights")
    kw_text = st.text_area("Keywords", value="\n".join(cfg["keywords"]),
                           height=120, label_visibility="collapsed")

    if st.button("SAVE SETUP"):
        cfg["starred"] = picked
        cfg["keywords"] = [k.strip() for k in kw_text.splitlines() if k.strip()]
        save_config(cfg)
        st.success("Setup saved to ~/.windwatch/config.json")
        st.rerun()

    eyebrow("Add a custom feed", "any RSS or Atom URL")
    c1, c2, c3 = st.columns([2, 3, 1.4])
    with c1:
        new_name = st.text_input("Name", placeholder="e.g. Recharge — wind")
    with c2:
        new_url = st.text_input("Feed URL", placeholder="https://…/feed")
    with c3:
        new_cat = st.selectbox("Class", SECTION_ORDER,
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
        eyebrow("Remove a custom feed")
        rm = st.selectbox("Remove", ["—"] + [s["id"] for s in cfg["custom_sources"]],
                          format_func=lambda sid: "—" if sid == "—" else
                          next(s["name"] for s in cfg["custom_sources"] if s["id"] == sid),
                          label_visibility="collapsed")
        if rm != "—" and st.button("REMOVE FEED"):
            cfg["custom_sources"] = [s for s in cfg["custom_sources"] if s["id"] != rm]
            cfg["starred"] = [s for s in cfg["starred"] if s != rm]
            save_config(cfg)
            st.rerun()
