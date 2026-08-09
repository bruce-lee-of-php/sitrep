"""Text source adapters — the active source while we are text-only.

``TextSource`` yields calls from an in-memory list (tests / one-shot injection).
``FileInboxSource`` watches a directory for ``.txt`` files (one transmission per
file), processes each, and moves it to an archive dir. Transcripts are already
set, so the transcription step is skipped entirely.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import time
from typing import Iterable, List

from sources.base import Call, RadioSource


def _stable_id(text: str) -> str:
    return "text-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class TextSource(RadioSource):
    name = "text"

    def __init__(self, transcripts: Iterable[str]):
        # Snapshot once; this source is drained on the first fetch.
        self._pending: List[Call] = [
            Call(
                external_id=_stable_id(t),
                source=self.name,
                transcript=t,
            )
            for t in transcripts
        ]

    def fetch_new_calls(self) -> List[Call]:
        pending, self._pending = self._pending, []
        return pending


class FileInboxSource(RadioSource):
    """Watch a directory for .txt files; each file is one transmission.

    Files are moved to ``archive_dir`` after being read so they are not
    reprocessed. Dedup on content hash still guards against re-drops.
    """

    name = "text"

    def __init__(self, inbox_dir: str, archive_dir: str):
        self.inbox_dir = inbox_dir
        self.archive_dir = archive_dir
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

    def fetch_new_calls(self) -> List[Call]:
        calls: List[Call] = []
        try:
            names = sorted(os.listdir(self.inbox_dir))
        except FileNotFoundError:
            return calls

        for name in names:
            if not name.lower().endswith(".txt"):
                continue
            path = os.path.join(self.inbox_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read().strip()
            except OSError as exc:
                print(f"[text] could not read {path}: {exc}", flush=True)
                continue

            if text:
                calls.append(
                    Call(
                        external_id=_stable_id(text + name),
                        source=self.name,
                        transcript=text,
                        extra={"filename": name},
                    )
                )

            # Move out of the inbox regardless, so it isn't re-scanned.
            dest = os.path.join(self.archive_dir, f"{int(time.time())}_{name}")
            try:
                shutil.move(path, dest)
            except OSError as exc:
                print(f"[text] could not archive {path}: {exc}", flush=True)

        return calls
