#!/usr/bin/env python3
"""
patch_fix_sim_bursts_schema.py

Brings sim_bursts table to expected ORM schema:

Expected ORM columns:
- id
- run_at
- leads_created
- events_generated
- notes

Current DB columns:
- id
- company_id
- burst_number
- created_at

This migration:
- Adds missing ORM columns with safe defaults
- Maps created_at → run_at
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("patch_fix_sim_bursts_schema")

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "the13th_allinone.db"


def column_exists(cursor, table: str, col: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return col in [row[1] for row in cursor.fetchall()]


def run():
    logger.info(f"Connecting to DB → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ==========================================================
    # run_at
    # ==========================================================
    if not column_exists(cursor, "sim_bursts", "run_at"):
        logger.info("Adding run_at (TIMESTAMP)")
        cursor.execute("ALTER TABLE sim_bursts ADD COLUMN run_at TIMESTAMP;")
        logger.info("Mapping created_at → run_at")
        cursor.execute("UPDATE sim_bursts SET run_at = created_at;")

    # ==========================================================
    # leads_created
    # ==========================================================
    if not column_exists(cursor, "sim_bursts", "leads_created"):
        logger.info("Adding leads_created (INTEGER)")
        cursor.execute("ALTER TABLE sim_bursts ADD COLUMN leads_created INTEGER;")
        cursor.execute("UPDATE sim_bursts SET leads_created = 0;")

    # ==========================================================
    # events_generated
    # ==========================================================
    if not column_exists(cursor, "sim_bursts", "events_generated"):
        logger.info("Adding events_generated (INTEGER)")
        cursor.execute("ALTER TABLE sim_bursts ADD COLUMN events_generated INTEGER;")
        cursor.execute("UPDATE sim_bursts SET events_generated = 0;")

    # ==========================================================
    # notes
    # ==========================================================
    if not column_exists(cursor, "sim_bursts", "notes"):
        logger.info("Adding notes (TEXT)")
        cursor.execute("ALTER TABLE sim_bursts ADD COLUMN notes TEXT;")
        cursor.execute("UPDATE sim_bursts SET notes = '';")

    conn.commit()
    conn.close()
    logger.info("sim_bursts migration completed successfully.")


if __name__ == "__main__":
    run()
