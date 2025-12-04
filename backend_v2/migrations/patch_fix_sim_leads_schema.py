#!/usr/bin/env python3
"""
Zero Migration Patch:
Normalize sim_leads schema → remove legacy columns:
- name
- price
- score_band
- deal_stage
- last_activity
Keep only modern engine fields:
- full_name, email, status, stage, score, deal_value, timestamps.
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
DB_PATH = Path("data/the13th_allinone.db")

def main():
    logging.info(f"Connecting → {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    logging.info("PRAGMA foreign_keys=off")
    cur.execute("PRAGMA foreign_keys=off;")

    logging.info("Creating new normalized table sim_leads_new")
    cur.execute("""
        CREATE TABLE sim_leads_new (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            score INTEGER NOT NULL,
            deal_value INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );
    """)

    logging.info("Copying compatible columns into sim_leads_new")
    cur.execute("""
        INSERT INTO sim_leads_new (
            id, company_id, full_name, email, status, stage,
            score, deal_value, created_at, updated_at
        )
        SELECT
            id,
            company_id,
            COALESCE(full_name, 'Unknown Lead') AS full_name,
            COALESCE(email, 'unknown@example.com') AS email,
            COALESCE(status, 'new') AS status,
            COALESCE(stage, 'new') AS stage,
            COALESCE(score, 0) AS score,
            COALESCE(deal_value, 0) AS deal_value,
            COALESCE(created_at, CURRENT_TIMESTAMP),
            COALESCE(updated_at, CURRENT_TIMESTAMP)
        FROM sim_leads;
    """)

    logging.info("Dropping old table sim_leads")
    cur.execute("DROP TABLE sim_leads;")

    logging.info("Renaming sim_leads_new → sim_leads")
    cur.execute("ALTER TABLE sim_leads_new RENAME TO sim_leads;")

    logging.info("PRAGMA foreign_keys=on")
    cur.execute("PRAGMA foreign_keys=on;")

    conn.commit()
    conn.close()
    logging.info("Migration completed successfully.")

if __name__ == "__main__":
    main()
