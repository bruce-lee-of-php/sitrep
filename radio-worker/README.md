# radio-worker

Ingests emergency radio chatter and turns it into map reports for SitRep Map.

```
source → (transcribe) → extract → geocode → reports table → pin on the map
```

**Text sources are the active path for now.** The OpenMHz audio adapter and the
faster-whisper transcription step are included but disabled (see "Enabling audio"
below).

## How it works

1. **Source** (`sources/`) — pluggable, text-only for now:
   - `FileInboxSource` (default) watches an inbox dir for `.txt` files (one
     transmission per file), processes each, and archives it. `TextSource`
     (in-memory) backs the tests and `inject.py`.
   - `MastodonSource` polls a **public Mastodon account's posts** — a good free
     scanner-feed source, no auth or API key needed. It resolves the account,
     polls `/api/v1/accounts/:id/statuses` with a `since_id` cursor, and strips
     each post's HTML to plain text. (Twitter/X is intentionally not supported —
     its API is paywalled since 2023.)
2. **Extract** (`extract/`) — pluggable. `ClaudeExtractor` (default when
   `ANTHROPIC_API_KEY` is set) returns structured JSON; `RulesExtractor` is the
   keyword/regex fallback with no key. Output `event_type` is constrained to the
   frontend's icon set (`Police / Military / Checkpoint / Protest / Arrest /
   Other`).
3. **Geocode** (`geocode.py`) — forward-geocodes the extracted place text via
   Nominatim (throttled to the ~1 req/s usage policy). `GEOCODE_REGION_HINT` /
   `NOMINATIM_VIEWBOX` bias bare street names to the right area.
4. **Store** (`store.py`) — inserts a row into the existing `reports` table
   (marked `source='radio'`) and a `radio_transmissions` row for dedup and
   provenance. A transmission with no actionable incident or no geocodable
   location is still recorded, but no pin is created.

## Run it

The service is wired into `docker-compose.yaml`. Drop a transmission in and watch:

```bash
docker-compose up --build radio-worker
cp radio-worker/samples/protest.txt radio-worker/inbox/     # one transmission
```

A pin should appear at `http://localhost:8085`.

### Using a Mastodon feed

Point the worker at any public Mastodon account that posts scanner chatter
(no API key needed). In `docker-compose.yaml`, set on the `radio-worker` service:

```yaml
- RADIO_SOURCE=mastodon
- MASTODON_INSTANCE=https://mastodon.social
- MASTODON_ACCOUNT=someScanner@mastodon.social
```

On first poll it primes its cursor and skips the backlog, then ingests new posts
as they appear. Accounts are regional and some go dormant — pick one that
actually covers your area.

### One-shot injection (no inbox, no audio)

```bash
docker-compose run --rm radio-worker python inject.py \
  "Units respond, checkpoint set up on Broadway near the bridge, 3 vehicles, code 3"
```

## Configuration (env)

| Var | Default | Purpose |
|-----|---------|---------|
| `RADIO_SOURCE` | `text` | `text`, `mastodon`, or `openmhz` (needs audio deps) |
| `TEXT_INBOX_DIR` | `/data/inbox` | Watched inbox for `.txt` transmissions |
| `TEXT_ARCHIVE_DIR` | `/data/processed` | Where processed files are moved |
| `MASTODON_INSTANCE` | _(unset)_ | e.g. `https://mastodon.social` (for `mastodon` source) |
| `MASTODON_ACCOUNT` | _(unset)_ | e.g. `someScanner@host` or a numeric id |
| `MASTODON_EXCLUDE_REPLIES` | `true` | Skip reply posts |
| `POLL_INTERVAL` | `30` | Seconds between polls |
| `ANTHROPIC_API_KEY` | _(unset)_ | Set to use Claude extraction; unset ⇒ rules |
| `CLAUDE_MODEL` | `claude-sonnet-5` | Model for the Claude extractor |
| `GEOCODE_REGION_HINT` | _(unset)_ | e.g. `Portland, Oregon` — biases geocoding |
| `NOMINATIM_VIEWBOX` | _(unset)_ | `minLon,maxLat,maxLon,minLat` bias box |

## Tests

```bash
cd radio-worker && python -m pytest tests/ -q
```

## Enabling audio (OpenMHz) later

1. Uncomment `faster-whisper` in `requirements.txt`.
2. Add `ffmpeg` install to the `Dockerfile` (see the comment there).
3. Set `RADIO_SOURCE=openmhz`, `OPENMHZ_SYSTEM=<short name from openmhz.com>`,
   and optionally `OPENMHZ_FILTER_TYPE` / `OPENMHZ_FILTER_CODE`.

The pipeline is unchanged — audio calls simply get a transcript from
faster-whisper before extraction.
