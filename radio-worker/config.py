"""Environment-driven configuration for the radio-worker module.

All settings come from environment variables so the worker can be configured
entirely from docker-compose without code changes.
"""
import os


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# --- Database (reused from the backend / docker-compose) ---
DB_NAME = os.getenv("POSTGRES_DB", "sitrep_db")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# --- Source ---
# Which source adapter to use:
#   "text"     — watched inbox of .txt files (default, active)
#   "mastodon" — poll a public Mastodon account's posts (active, text-only)
#   "openmhz"  — scaffolded for later (needs faster-whisper + ffmpeg)
SOURCE = os.getenv("RADIO_SOURCE", "text").strip().lower()

# Text source: a watched inbox of .txt files, one transmission per file. Drop a
# file in, it gets processed and moved to the archive dir. Mount these as a
# volume in docker-compose to feed chatter in.
TEXT_INBOX_DIR = os.getenv("TEXT_INBOX_DIR", "/data/inbox")
TEXT_ARCHIVE_DIR = os.getenv("TEXT_ARCHIVE_DIR", "/data/processed")

# Mastodon source: poll a public account (no auth needed for public posts).
# INSTANCE e.g. "https://mastodon.social"; ACCOUNT e.g. "someScanner@host" or a
# numeric account id.
MASTODON_INSTANCE = os.getenv("MASTODON_INSTANCE", "").strip()
MASTODON_ACCOUNT = os.getenv("MASTODON_ACCOUNT", "").strip()
MASTODON_EXCLUDE_REPLIES = _get_bool("MASTODON_EXCLUDE_REPLIES", True)

# OpenMHz system short name (e.g. "kcers1b"). Browse https://openmhz.com to find
# a system that carries traffic for your area. Required for the openmhz source.
OPENMHZ_SYSTEM = os.getenv("OPENMHZ_SYSTEM", "").strip()
# "group" or "talkgroup". Determines how filter-code is interpreted.
OPENMHZ_FILTER_TYPE = os.getenv("OPENMHZ_FILTER_TYPE", "group").strip()
# Group id, or comma-separated talkgroup ids. Empty = no filter (all calls).
OPENMHZ_FILTER_CODE = os.getenv("OPENMHZ_FILTER_CODE", "").strip()
OPENMHZ_BASE_URL = os.getenv("OPENMHZ_BASE_URL", "https://api.openmhz.com").rstrip("/")

# --- Poll loop ---
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
# Ignore very short transmissions (seconds) — usually noise / key-ups.
MIN_CALL_LENGTH = float(os.getenv("MIN_CALL_LENGTH", "1.0"))

# --- Transcription (faster-whisper) ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
# Transcripts shorter than this many characters are treated as empty/noise.
MIN_TRANSCRIPT_CHARS = int(os.getenv("MIN_TRANSCRIPT_CHARS", "8"))

# --- Extraction ---
# Absent ANTHROPIC_API_KEY => the rules extractor is used automatically.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
# Force a specific extractor regardless of key presence: "claude" | "rules" | "auto".
EXTRACTOR = os.getenv("RADIO_EXTRACTOR", "auto").strip().lower()

# --- Geocoding (Nominatim) ---
NOMINATIM_URL = os.getenv(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "SitRepApp/1.0")
# Optional bias to disambiguate bare street names, format: "left,top,right,bottom"
# (min-lon,max-lat,max-lon,min-lat) per Nominatim viewbox convention.
NOMINATIM_VIEWBOX = os.getenv("NOMINATIM_VIEWBOX", "").strip()
# If set, restrict results strictly to the viewbox.
NOMINATIM_BOUNDED = _get_bool("NOMINATIM_BOUNDED", False)
# Optional free-text region appended to queries (e.g. "Portland, Oregon") to
# help geocode bare intersections/streets.
GEOCODE_REGION_HINT = os.getenv("GEOCODE_REGION_HINT", "").strip()
# Minimum seconds between Nominatim requests (usage policy: max ~1/s).
NOMINATIM_MIN_INTERVAL = float(os.getenv("NOMINATIM_MIN_INTERVAL", "1.1"))

SOURCE_LABEL = os.getenv("RADIO_SOURCE_LABEL", "radio")
