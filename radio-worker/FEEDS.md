# Vetted starter feeds

A short, curated list of real emergency-chatter sources to pre-populate the
system with. Each entry notes coverage, format, how to plug it in, and caveats.

> **Vetting method / honesty note:** these were corroborated via web search
> (descriptions, post counts, feed formats, documented clients) but **not**
> live-fetched from the build sandbox, whose network egress is allowlisted and
> blocked every one of these hosts. They should be reachable from your
> deployment — do a quick manual check (open the URL) before enabling, and
> confirm the feed is still live.

## Tier A — drop-in now (no code changes)

These work with the existing `mastodon` and `rss` sources.

| Source | Coverage | Type | Plug in as |
|--------|----------|------|-----------|
| **Baraboo Scanner** | Sauk / Columbia County, WI | Mastodon (human-curated scanner relay) | `mastodon`: `@BarabooScanner@mastodon.social` — or `rss`: `https://mastodon.social/@BarabooScanner.rss` |
| **Lancaster County-Wide Communications** | Lancaster County, PA | Official 911 CAD live-incident RSS | `rss`: `https://www.lcwc911.us/live-incident-list` |
| **Tampa Police calls** | Tampa, FL | Official police calls-for-service RSS | `rss`: `http://www.tampagov.net/appl_rss_feeds/rss.asp?feed=police_calls` |
| **Kamloops Scanner (kamscan)** | Kamloops, BC (Canada) | Mastodon scanner relay | `mastodon`: `@kamscan@mastodon.cloud` |

Notes:
- **Baraboo Scanner** is the best fit for the extractor: 11+ year history (moved
  from Twitter), ~4.8K posts, already natural-language chatter with locations
  ("We are NOT the law"). Human-curated ⇒ lower noise than raw CAD.
- **Lancaster** and **Tampa** are official CAD feeds: terse, structured items
  like `MEDICAL EMERGENCY — 100 BLK N QUEEN ST, LANCASTER CITY`. Locations are
  explicit addresses, so geocoding is reliable; Claude extraction handles the
  terse phrasing far better than the rules fallback.
- **Kamloops** adds non-US coverage — good for testing geocode region bias
  (`GEOCODE_REGION_HINT="Kamloops, BC"`).

### Example config (docker-compose radio-worker service)

RSS (mix official CAD + a Mastodon account's RSS):

```yaml
- RADIO_SOURCE=rss
- RSS_FEEDS=https://www.lcwc911.us/live-incident-list,http://www.tampagov.net/appl_rss_feeds/rss.asp?feed=police_calls,https://mastodon.social/@BarabooScanner.rss
- GEOCODE_REGION_HINT=Lancaster County, PA
```

Or a single Mastodon account via the API source:

```yaml
- RADIO_SOURCE=mastodon
- MASTODON_INSTANCE=https://mastodon.social
- MASTODON_ACCOUNT=BarabooScanner@mastodon.social
```

## Tier B — great data, needs a small JSON/CAD adapter

Structured JSON feeds (not RSS). Each would need a ~1-file source adapter
implementing `RadioSource`. Worth it because the data is clean and high-volume.

| Source | Coverage | Notes |
|--------|----------|-------|
| **DataSF — Law Enforcement Dispatched Calls (Real-Time)** | San Francisco, CA | SODA JSON API (resource `gnap-fj3t`), ~10-min cadence, 10-min delay. **Already includes coordinates** — could bypass Nominatim entirely. |
| **Houston Active Incidents** | Houston, TX | Fire/Police/EMS, 5-min updates. |
| **Seattle Fire Real-Time 911** (`sfdlive.com` / seattle.gov) | Seattle, WA | Fire/EMS incidents with address + type. |
| **Montgomery County, PA WebCAD** | Montgomery County, PA | 4-min updates from CAD. |

## Before enabling — important caveats

- **Terms of use / rate limits.** Official CAD sites sometimes restrict
  automated polling. Poll gently (the default `POLL_INTERVAL`), don't hammer,
  and check each site's ToS / `robots.txt`.
- **Privacy & accuracy.** This is *unverified* data and can include sensitive
  calls (medical, mental-health, named individuals). Reports are marked
  `source='radio'` and logged in `radio_transmissions` — consider adding a
  human-review gate before publishing these publicly.
- **Coverage is regional and feeds go dormant.** Pick sources for the area you
  actually care about, and re-check them periodically.
