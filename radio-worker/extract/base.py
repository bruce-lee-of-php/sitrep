"""Extractor interface and shared types.

``event_type`` is constrained to the set the frontend has marker icons for
(``frontend/index.html``); anything else renders as the gray default pin, so we
normalise onto this enum here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import config

# Must match the icon keys in frontend/index.html (createReportIcon / reportIcons).
EVENT_TYPES = ["Police", "Military", "Checkpoint", "Protest", "Arrest", "Other"]
CONFIDENCE_LEVELS = ["Low", "Medium", "High"]


@dataclass
class ExtractedReport:
    """Structured fields pulled from a transcript.

    ``actionable`` is False when the transcript carries no reportable incident
    (chatter, tests, static) — the worker then stores provenance but creates no
    map pin. ``location_text`` is what gets forward-geocoded.
    """

    actionable: bool
    event_type: str = "Other"
    event_subtype: Optional[str] = None
    personnel_count: Optional[str] = None
    vehicle_count: Optional[str] = None
    confidence_level: str = "Low"
    is_urgent: bool = False
    description: Optional[str] = None
    location_text: Optional[str] = None

    def normalized(self) -> "ExtractedReport":
        """Clamp fields to allowed values so downstream/DB stays consistent."""
        if self.event_type not in EVENT_TYPES:
            self.event_type = "Other"
        if self.confidence_level not in CONFIDENCE_LEVELS:
            self.confidence_level = "Low"
        return self


class Extractor(ABC):
    name = "base"

    @abstractmethod
    def extract(self, transcript: str) -> ExtractedReport:
        raise NotImplementedError


def get_extractor() -> Extractor:
    """Select an extractor per config.

    ``RADIO_EXTRACTOR`` forces a choice; otherwise ("auto") Claude is used when
    an API key is present and the rules extractor is the fallback.
    """
    choice = config.EXTRACTOR
    if choice == "rules":
        from .rules import RulesExtractor

        return RulesExtractor()
    if choice == "claude":
        from .claude import ClaudeExtractor

        return ClaudeExtractor()

    # auto
    if config.ANTHROPIC_API_KEY:
        from .claude import ClaudeExtractor

        return ClaudeExtractor()
    from .rules import RulesExtractor

    print(
        "[extract] no ANTHROPIC_API_KEY set — using rules extractor fallback",
        flush=True,
    )
    return RulesExtractor()
