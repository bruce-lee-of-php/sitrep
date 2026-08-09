"""Claude-based extractor (default when ANTHROPIC_API_KEY is set).

Sends the transcript to Claude and asks for a strict JSON object matching the
report schema. Falls back to a non-actionable result on any error so a bad API
call never crashes the worker.
"""
from __future__ import annotations

import json
from typing import Optional

import config
from .base import CONFIDENCE_LEVELS, EVENT_TYPES, ExtractedReport, Extractor

_SYSTEM_PROMPT = (
    "You extract structured incident data from short, noisy emergency-radio "
    "transcripts. Transcripts may be garbled or contain no real incident. "
    "Return ONLY a single JSON object, no prose."
)

_INSTRUCTIONS = f"""Extract the following fields from the radio transmission.

Return JSON with exactly these keys:
- "actionable": boolean. false if the transmission has no reportable incident
  (idle chatter, radio checks, static, unintelligible).
- "event_type": one of {EVENT_TYPES}.
- "event_subtype": short string or null (e.g. "traffic stop", "crowd forming").
- "personnel_count": string number or null (people/officers/subjects mentioned).
- "vehicle_count": string number or null.
- "confidence_level": one of {CONFIDENCE_LEVELS} — your confidence the incident
  and location are real and correctly extracted.
- "is_urgent": boolean (shots fired, officer down, code 3, priority, etc.).
- "location_text": the place to map (intersection, street, address, landmark),
  or null if none is stated. Do NOT invent a location.
- "description": one-sentence plain-language summary of the transmission.

Transmission:
\"\"\"{{transcript}}\"\"\"
"""


class ClaudeExtractor(Extractor):
    name = "claude"

    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ClaudeExtractor requires ANTHROPIC_API_KEY.")
        # Imported lazily so the package imports without the SDK installed.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._model = config.CLAUDE_MODEL

    def _parse_json(self, text: str) -> Optional[dict]:
        text = text.strip()
        # Tolerate code fences or leading/trailing prose.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    def extract(self, transcript: str) -> ExtractedReport:
        text = (transcript or "").strip()
        if not text:
            return ExtractedReport(actionable=False)

        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": _INSTRUCTIONS.format(transcript=text)}
                ],
            )
            raw = "".join(
                block.text for block in msg.content if getattr(block, "type", None) == "text"
            )
        except Exception as exc:  # noqa: BLE001 — never let extraction crash the loop
            print(f"[extract:claude] API error, skipping report: {exc}", flush=True)
            return ExtractedReport(actionable=False, description=text)

        data = self._parse_json(raw)
        if not data:
            print(f"[extract:claude] could not parse JSON: {raw!r}", flush=True)
            return ExtractedReport(actionable=False, description=text)

        report = ExtractedReport(
            actionable=bool(data.get("actionable")),
            event_type=str(data.get("event_type") or "Other"),
            event_subtype=data.get("event_subtype"),
            personnel_count=_as_opt_str(data.get("personnel_count")),
            vehicle_count=_as_opt_str(data.get("vehicle_count")),
            confidence_level=str(data.get("confidence_level") or "Low"),
            is_urgent=bool(data.get("is_urgent")),
            description=data.get("description") or text,
            location_text=data.get("location_text"),
        )
        # A report with no location cannot be placed on the map.
        if not report.location_text:
            report.actionable = False
        return report.normalized()


def _as_opt_str(val) -> Optional[str]:
    if val is None:
        return None
    return str(val)
