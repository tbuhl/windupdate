"""
WINDWATCH — default source registry.

Each source: id, name, url (RSS/Atom), category, note.
Categories: news, contracts, patents, tech, markets.

Feeds occasionally move or die — the Sources page shows live status per feed,
and any feed can be replaced or supplemented with a custom one.
Google News RSS queries are used where no first-party feed exists; they are
stable and require no API key.
"""

def gnews(query: str) -> str:
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


DEFAULT_SOURCES = [
    # ---------------- Industry news ----------------
    {
        "id": "offshorewind_biz",
        "name": "offshoreWIND.biz",
        "url": "https://www.offshorewind.biz/feed/",
        "category": "news",
        "note": "Offshore wind daily news (Navingo).",
    },
    {
        "id": "renews",
        "name": "reNEWS.biz",
        "url": "https://renews.biz/feed/",
        "category": "news",
        "note": "Renewables business news, strong on wind.",
    },
    {
        "id": "windtech_intl",
        "name": "Windtech International",
        "url": "https://www.windtech-international.com/?format=feed&type=rss",
        "category": "tech",
        "note": "Technical trade magazine — turbines, components, O&M.",
    },
    {
        "id": "cleantechnica_wind",
        "name": "CleanTechnica — Wind",
        "url": "https://cleantechnica.com/category/clean-power/wind-energy/feed/",
        "category": "news",
        "note": "Wind category feed.",
    },
    {
        "id": "nawindpower",
        "name": "North American Windpower",
        "url": "https://nawindpower.com/feed",
        "category": "news",
        "note": "North American market focus.",
    },
    {
        "id": "windeurope",
        "name": "WindEurope newsroom",
        "url": "https://windeurope.org/feed/",
        "category": "markets",
        "note": "Association news, policy, auctions, statistics.",
    },
    {
        "id": "gnews_wind",
        "name": "Google News — wind industry",
        "url": gnews('"wind turbine" OR "wind farm" OR "offshore wind"'),
        "category": "news",
        "note": "Broad catch-all across all outlets.",
    },

    # ---------------- Contracts & orders ----------------
    {
        "id": "gnews_contracts",
        "name": "Google News — contracts & orders",
        "url": gnews('wind ("contract awarded" OR "firm order" OR "turbine order" OR "preferred supplier" OR "supply agreement")'),
        "category": "contracts",
        "note": "Contract awards, firm orders, preferred-supplier picks.",
    },
    {
        "id": "gnews_fid",
        "name": "Google News — FID & financing",
        "url": gnews('"offshore wind" OR "wind farm" ("final investment decision" OR "financial close" OR "reaches FID")'),
        "category": "contracts",
        "note": "Investment decisions and project financing milestones.",
    },

    # ---------------- Patents & IP ----------------
    {
        "id": "gnews_patents",
        "name": "Google News — wind patents & IP",
        "url": gnews('"wind turbine" (patent OR "intellectual property" OR USPTO OR EPO)'),
        "category": "patents",
        "note": "Patent grants, filings and IP litigation in the press.",
    },
    {
        "id": "patentscope_wind",
        "name": "WIPO PATENTSCOPE — wind turbine",
        "url": "https://patentscope.wipo.int/search/rss.jsf?query=EN_TI%3A%28%22wind%20turbine%22%29&sortOption=Pub%20Date%20Desc",
        "category": "patents",
        "note": "Raw publication stream; if the feed is offline, add a saved-search RSS from patentscope.wipo.int.",
    },

    # ---------------- Technology & research ----------------
    {
        "id": "wes_journal",
        "name": "Wind Energy Science (journal)",
        "url": "https://wes.copernicus.org/xml/rss2_0.xml",
        "category": "papers",
        "note": "Peer-reviewed papers — EAWE / Copernicus.",
    },
    {
        "id": "nrel_news",
        "name": "NREL news",
        "url": "https://www.nrel.gov/news/rss.xml",
        "category": "tech",
        "note": "US national-lab research announcements.",
    },
    {
        "id": "gnews_tech",
        "name": "Google News — turbine technology",
        "url": gnews('"wind turbine" (prototype OR certification OR "type certificate" OR blade OR nacelle OR drivetrain OR recyclable)'),
        "category": "tech",
        "note": "Prototypes, certification, components, blade tech.",
    },

    # ---------------- Markets, auctions & policy ----------------
    {
        "id": "gnews_auctions",
        "name": "Google News — auctions & tenders",
        "url": gnews('wind (auction OR tender OR CfD OR "seabed lease" OR "capacity awarded")'),
        "category": "markets",
        "note": "Auction rounds, tenders, CfDs, lease rounds.",
    },
]

CATEGORIES = {
    "contracts": {"label": "Contracts awarded",         "short": "CONTRACT"},
    "patents":   {"label": "Patents",                   "short": "PATENT"},
    "papers":    {"label": "Recent scientific papers",  "short": "PAPER"},
    "tech":      {"label": "Technology development",    "short": "TECH"},
    "markets":   {"label": "Markets & policy",          "short": "MARKET"},
    "news":      {"label": "Industry news",             "short": "NEWS"},
}
