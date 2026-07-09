# WINDWATCH — daily operations brief for the wind industry

A self-hosted Streamlit dashboard that aggregates wind-industry news, patents,
technology development, market/auction activity and contract awards from RSS
feeds, classifies every item, and lets you compose your own highlight page.

## Run

    pip install -r requirements.txt
    streamlit run app.py

## Pages

- **HIGHLIGHTS** — your composed front page: 24 h signal board, keyword alerts
  (▲, orange rail), then your starred sources in the order you picked them.
- **ALL ITEMS** — the full deduplicated event log, filterable by class
  (CONTRACT / PATENT / TECH / MARKET / NEWS) and free-text search.
- **SOURCES & SETUP** — live feed status LEDs, star/order sources, edit the
  keyword watchlist, add or remove any RSS/Atom feed.

## How it works

- Feeds are fetched with a 10 s timeout and cached for 15 minutes; a failing
  feed shows an orange LED with the reason and never breaks the page.
- Every item is auto-classified by regex (contract awards, FID/financing,
  patents/IP, prototypes/certification/components, auctions/tenders/policy)
  and scanned against a built-in OEM/developer watchlist (Vestas, Siemens
  Gamesa, GE Vernova, Ørsted, …).
- Items are deduplicated across sources by normalized title.
- Your setup persists in `~/.windwatch/config.json`.

## Notes on sources

First-party feeds are included where the outlet publishes one; where none
exists (contract awards, patents, auctions), keyless Google News RSS queries
are used. Some outlets (e.g. Recharge, Windpower Monthly) are subscription
sites without stable public feeds — add them as custom feeds if you have
access, or add a Google News query per outlet:
`https://news.google.com/rss/search?q=site:rechargenews.com wind`

For a raw patent-publication stream, save a search on
patentscope.wipo.int and add its RSS URL as a custom PATENT feed.
