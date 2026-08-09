"""Base types for radio source adapters.

A ``RadioSource`` yields ``Call`` objects. Each source is responsible for its
own polling cursor so the worker loop stays source-agnostic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Call:
    """A single radio transmission to be processed.

    ``audio_url`` may be ``None`` when the call already carries a transcript
    (e.g. the text source), in which case transcription is skipped.
    """

    external_id: str          # stable, source-unique id (used for dedup)
    source: str               # adapter name, e.g. "openmhz" / "text"
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    talkgroup: Optional[str] = None
    timestamp: Optional[str] = None   # ISO8601 string if available
    length: Optional[float] = None    # seconds
    extra: dict = field(default_factory=dict)


class RadioSource(ABC):
    """Interface every source adapter implements."""

    name: str = "base"

    @abstractmethod
    def fetch_new_calls(self) -> List[Call]:
        """Return calls not seen since the last invocation.

        Implementations advance their own cursor. Returning an empty list is
        normal (no new traffic).
        """
        raise NotImplementedError
