#!/usr/bin/env python3
"""
patch_make_sim_bursts_company_nullable.py

Makes column company_id in sim_bursts nullable.
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("patch_make_sim_bursts_company_nullable")

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "the13th_allinone.db"


def run():
    logger.info(f"Opening DB → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    logger.info("Renaming table sim_bursts → sim_bursts_old")
    cursor.execute("ALTER TABLE sim_bursts RENAME TO sim_bursts_old;")

    logger.info("Creating new sim_bursts with company_id nullable")
    cursor.execute("""
        CREATE TABLE sim_bursts (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NULL,
            burst_number INTEGER,
            run_at TIMESTAMP,
            leads_created INTEGER,
            events_generated INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    logger.info("Copying data from old table → new table")
    cursor.execute("""
        INSERT INTO sim_bursts (
            id,
            company_id,
            burst_number,
            created_at
        )
        SELECT
            id,
            company_id,
            burst_number,
            created_at
        FROM sim_bursts_old;
    """)

    logger.info("Dropping old table")
    cursor.execute("DROP TABLE sim_bursts_old;")

    conn.commit()
    conn.close()
    logger.info("Migration completed: company_id is now nullable.")


if __name__ == "__main__":
    run()
