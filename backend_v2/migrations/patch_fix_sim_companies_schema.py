#!/usr/bin/env python3
"""
patch_fix_sim_companies_schema.py

Brings sim_companies table to the expected schema:

Expected final columns:
- id (PK)
- name (TEXT)
- company_name (TEXT, legacy)
- segment (TEXT)
- region (TEXT)
- target_volume (INTEGER)
- created_at (TIMESTAMP)

Safe, idempotent migration.
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("patch_fix_sim_companies_schema")

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "the13th_allinone.db"


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def run():
    logger.info(f"Connecting to DB → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ----------------------------------
    # 1) Ensure "name" column exists
    # ----------------------------------
    if not column_exists(cursor, "sim_companies", "name"):
        logger.info("Adding column: name (TEXT)")
        cursor.execute("ALTER TABLE sim_companies ADD COLUMN name TEXT;")

        # Copy company_name into name if exists
        if column_exists(cursor, "sim_companies", "company_name"):
            logger.info("Copying company_name → name")
            cursor.execute("UPDATE sim_companies SET name = company_name;")
        else:
            logger.warning("company_name column not found; name left NULL")

    else:
        logger.info("Column 'name' already exists")

    # ----------------------------------
    # 2) Ensure "segment" column exists
    # ----------------------------------
    if not column_exists(cursor, "sim_companies", "segment"):
        logger.info("Adding column: segment (TEXT)")
        cursor.execute("ALTER TABLE sim_companies ADD COLUMN segment TEXT;")
        logger.info("Populating default: segment='General'")
        cursor.execute("UPDATE sim_companies SET segment='General';")
    else:
        logger.info("Column 'segment' already exists")

    # ----------------------------------
    # 3) Ensure "region" column exists
    # ----------------------------------
    if not column_exists(cursor, "sim_companies", "region"):
        logger.info("Adding column: region (TEXT)")
        cursor.execute("ALTER TABLE sim_companies ADD COLUMN region TEXT;")
        logger.info("Populating default: region='US'")
        cursor.execute("UPDATE sim_companies SET region='US';")
    else:
        logger.info("Column 'region' already exists")

    # ----------------------------------
    # 4) Ensure "target_volume" column exists
    # ----------------------------------
    if not column_exists(cursor, "sim_companies", "target_volume"):
        logger.info("Adding column: target_volume (INTEGER)")
        cursor.execute("ALTER TABLE sim_companies ADD COLUMN target_volume INTEGER;")
        logger.info("Populating default: target_volume=250")
        cursor.execute("UPDATE sim_companies SET target_volume=250;")
    else:
        logger.info("Column 'target_volume' already exists")

    conn.commit()
    conn.close()
    logger.info("Migration completed successfully.")


if __name__ == "__main__":
    run()
