"""Persistence: schema setup, dedup, and writing reports + provenance.

Reuses the existing ``reports`` table (same columns and POINTZ WKT pattern as
backend/main.py ``create_report``) and adds a ``radio_transmissions`` table for
dedup and provenance. There is no Alembic in this project, so schema changes are
applied idempotently with CREATE TABLE / ALTER TABLE ... IF NOT EXISTS.
"""
from __future__ import annotations

import json
from typing import Optional, Tuple

import psycopg2

import config
from extract.base import ExtractedReport
from sources.base import Call


def get_connection():
    return psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
    )


def init_schema(conn) -> None:
    """Create the provenance table and add the reports.source column."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS radio_transmissions (
                id SERIAL PRIMARY KEY,
                source VARCHAR(64) NOT NULL,
                external_id VARCHAR(255) UNIQUE NOT NULL,
                talkgroup VARCHAR(128),
                audio_url TEXT,
                transcript TEXT,
                extracted_json JSONB,
                report_id INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        # reports may not exist yet if the backend hasn't started; guard it.
        cur.execute("SELECT to_regclass('public.reports');")
        if cur.fetchone()[0] is not None:
            cur.execute(
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual';"
            )
    conn.commit()


def already_processed(conn, external_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM radio_transmissions WHERE external_id = %s LIMIT 1;",
            (external_id,),
        )
        return cur.fetchone() is not None


def _insert_report(cur, extracted: ExtractedReport, lat: float, lon: float) -> int:
    """Insert into reports using the same WKT pattern as the backend."""
    point_wkt = f"SRID=4326;POINTZ({lon} {lat} 0)"
    cur.execute(
        """
        INSERT INTO reports (
            event_type, event_subtype, personnel_count, vehicle_count,
            confidence_level, is_urgent, granularity, description, location, source
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromEWKT(%s), %s)
        RETURNING id;
        """,
        (
            extracted.event_type,
            extracted.event_subtype,
            extracted.personnel_count,
            extracted.vehicle_count,
            extracted.confidence_level,
            str(extracted.is_urgent),
            "approximate",  # radio-derived locations are geocoded, not precise
            extracted.description,
            point_wkt,
            config.SOURCE_LABEL,
        ),
    )
    return cur.fetchone()[0]


def record(
    conn,
    call: Call,
    transcript: str,
    extracted: ExtractedReport,
    coords: Optional[Tuple[float, float]],
) -> Optional[int]:
    """Persist a transmission and, when placeable, a report. Returns report id."""
    report_id: Optional[int] = None
    with conn.cursor() as cur:
        if extracted.actionable and coords is not None:
            lat, lon = coords
            report_id = _insert_report(cur, extracted, lat, lon)

        cur.execute(
            """
            INSERT INTO radio_transmissions (
                source, external_id, talkgroup, audio_url, transcript,
                extracted_json, report_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (external_id) DO NOTHING;
            """,
            (
                call.source,
                call.external_id,
                call.talkgroup,
                call.audio_url,
                transcript,
                json.dumps(extracted.__dict__),
                report_id,
            ),
        )
    conn.commit()
    return report_id
