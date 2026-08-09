"""Rules/keyword extractor — the no-API-key fallback.

Deliberately conservative: it maps obvious keywords to an event type, pulls a
rough location phrase (intersections, "at/near <place>", block addresses) and
flags urgency. It will miss a lot of real chatter — that is expected; Claude is
the recommended path when a key is available.
"""
from __future__ import annotations

import re
from typing import Optional

from .base import ExtractedReport, Extractor

# Keyword -> event type. First match wins (order matters: specific before broad).
_EVENT_KEYWORDS = [
    ("Checkpoint", ["checkpoint", "road block", "roadblock", "barricade", "cordon"]),
    ("Protest", ["protest", "demonstration", "crowd", "march", "rally", "gathering"]),
    ("Arrest", ["arrest", "in custody", "detain", "detained", "cuffed", "apprehend"]),
    ("Military", ["national guard", "military", "troops", "convoy", "armored", "humvee"]),
    ("Police", ["officer", "units respond", "pd ", "police", "patrol", "dispatch",
                "suspect", "pursuit", "traffic stop", "backup", "10-4", "code 3"]),
]

_URGENT_KEYWORDS = [
    "urgent", "emergency", "shots fired", "shots-fired", "officer down",
    "code 3", "code three", "priority", "immediate", "mayday", "man down",
    "10-33", "active", "asap",
]

# Location patterns, tried in order.
_LOCATION_PATTERNS = [
    # intersections: "5th and Main", "Main & 3rd"
    re.compile(r"\b([A-Z0-9][\w.]*(?:\s+\w+)?\s+(?:and|&|/)\s+[A-Z0-9][\w.]*(?:\s+\w+)?)\b"),
    # "at/near/on <Proper Place>"
    re.compile(r"\b(?:at|near|on|by)\s+((?:the\s+)?[A-Z0-9][\w.'-]*(?:\s+[A-Z0-9][\w.'-]*){0,3})"),
    # block addresses: "1200 block of Elm Street"
    re.compile(r"\b(\d{1,5}\s+block\s+of\s+[A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,2})", re.IGNORECASE),
]

_COUNT_PEOPLE = re.compile(r"\b(\d{1,4})\s+(?:people|persons?|protesters?|subjects?|individuals?)\b", re.IGNORECASE)
_COUNT_VEHICLES = re.compile(r"\b(\d{1,3})\s+(?:vehicles?|cars?|trucks?|units?)\b", re.IGNORECASE)


class RulesExtractor(Extractor):
    name = "rules"

    def _event_type(self, text: str) -> Optional[str]:
        low = text.lower()
        for event_type, keywords in _EVENT_KEYWORDS:
            if any(k in low for k in keywords):
                return event_type
        return None

    def _location(self, text: str) -> Optional[str]:
        for pat in _LOCATION_PATTERNS:
            m = pat.search(text)
            if m:
                return m.group(1).strip()
        return None

    def extract(self, transcript: str) -> ExtractedReport:
        text = (transcript or "").strip()
        if not text:
            return ExtractedReport(actionable=False)

        event_type = self._event_type(text)
        location = self._location(text)
        low = text.lower()
        is_urgent = any(k in low for k in _URGENT_KEYWORDS)

        people = _COUNT_PEOPLE.search(text)
        vehicles = _COUNT_VEHICLES.search(text)

        # Actionable only if we recognised an event AND have somewhere to place it.
        actionable = bool(event_type and location)

        report = ExtractedReport(
            actionable=actionable,
            event_type=event_type or "Other",
            personnel_count=people.group(1) if people else None,
            vehicle_count=vehicles.group(1) if vehicles else None,
            confidence_level="Low",  # rules extraction is inherently low-confidence
            is_urgent=is_urgent,
            description=text,
            location_text=location,
        )
        return report.normalized()
