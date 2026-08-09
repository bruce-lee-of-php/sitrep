"""Shared per-call processing pipeline.

Given a Call, run: (transcribe if needed) -> extract -> geocode -> store.
Kept separate from the loop so the injection helper and tests can reuse it.
"""
from __future__ import annotations

import config
import geocode as geocode_mod
import store
from extract.base import Extractor
from sources.base import Call


def process_call(conn, call: Call, extractor: Extractor) -> None:
    if store.already_processed(conn, call.external_id):
        return

    # 1. Transcript: text sources bring their own; audio sources transcribe.
    transcript = (call.transcript or "").strip()
    if not transcript and call.audio_url:
        # Lazy import so the text-only build never needs faster-whisper.
        import transcribe

        transcript = transcribe.transcribe_url(call.audio_url)

    if not transcript or len(transcript) < config.MIN_TRANSCRIPT_CHARS:
        # Nothing usable — still record provenance so we don't re-fetch it.
        from extract.base import ExtractedReport

        store.record(conn, call, transcript, ExtractedReport(actionable=False), None)
        print(f"[pipeline] {call.external_id}: empty/short transcript, skipped", flush=True)
        return

    # 2. Extract structured fields.
    extracted = extractor.extract(transcript)

    # 3. Geocode when actionable and a location was found.
    coords = None
    if extracted.actionable and extracted.location_text:
        coords = geocode_mod.geocode(extracted.location_text)
        if coords is None:
            print(
                f"[pipeline] {call.external_id}: could not geocode "
                f"{extracted.location_text!r}, storing without pin",
                flush=True,
            )

    # 4. Persist (report only when actionable + geocoded).
    report_id = store.record(conn, call, transcript, extracted, coords)
    if report_id:
        lat, lon = coords
        print(
            f"[pipeline] {call.external_id}: report #{report_id} "
            f"[{extracted.event_type}] @ {extracted.location_text!r} "
            f"({lat:.5f},{lon:.5f})",
            flush=True,
        )
    else:
        print(
            f"[pipeline] {call.external_id}: recorded transmission, no pin "
            f"(actionable={extracted.actionable})",
            flush=True,
        )
