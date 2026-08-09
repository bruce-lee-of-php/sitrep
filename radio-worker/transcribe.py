"""Speech-to-text using self-hosted faster-whisper.

The model is loaded lazily on first use so that importing this module (e.g. in
unit tests or the text-injection path) never pulls in the heavy dependency.
"""
from __future__ import annotations

import io
from typing import Optional

import httpx

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        # Imported lazily: heavy dependency, only needed for real audio.
        from faster_whisper import WhisperModel

        print(
            f"[transcribe] loading faster-whisper model="
            f"{config.WHISPER_MODEL} device={config.WHISPER_DEVICE} "
            f"compute={config.WHISPER_COMPUTE_TYPE}",
            flush=True,
        )
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _model


def download_audio(url: str) -> Optional[bytes]:
    try:
        resp = httpx.get(url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError as exc:
        print(f"[transcribe] audio download failed for {url}: {exc}", flush=True)
        return None


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe raw audio bytes (m4a/wav/etc.) to text.

    faster-whisper reads the stream via PyAV/ffmpeg, so any container ffmpeg
    supports works without pre-conversion.
    """
    model = _get_model()
    segments, _info = model.transcribe(io.BytesIO(audio_bytes), beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text


def transcribe_url(url: str) -> str:
    audio = download_audio(url)
    if not audio:
        return ""
    return transcribe_audio(audio)


def is_meaningful(transcript: str) -> bool:
    return bool(transcript) and len(transcript.strip()) >= config.MIN_TRANSCRIPT_CHARS
