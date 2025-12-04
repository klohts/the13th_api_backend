#!/usr/bin/env python3
"""
THE13TH — Option A Migration
Aligns DB sim_companies + sim_leads tables with new ORM.

 - Renames sim_companies.name → company_name
 - Removes no data
 - Adds missing columns (score_band, last_activity)
 - Creates columns only if not present
 - Idempotent (safe to rerun)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "the13th_allinone.db"


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def main():
    print("=== THE13TH • Option A Schema Migration ===")
    print("DB:", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    #
    # ---- 1) MIGRATE sim_companies ----
    #
    print("\n[STEP 1] Checking sim_companies ...")

    if column_exists(cur, "sim_companies", "name"):
        print(" - Renaming column name → company_name")

        # Create new column if missing
        if not column_exists(cur, "sim_companies", "company_name"):
            cur.execute("ALTER TABLE sim_companies ADD COLUMN company_name TEXT;")

        # Copy values
        cur.execute("UPDATE sim_companies SET company_name = name;")

        # Drop old column: SQLite can't drop columns → rebuild table
        print(" - Rebuilding sim_companies table without column 'name' ...")

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sim_companies_new (
                id INTEGER PRIMARY KEY,
                company_name TEXT,
                created_at TEXT
            );

            INSERT INTO sim_companies_new (id, company_name, created_at)
            SELECT id, company_name, created_at
            FROM sim_companies;

            DROP TABLE sim_companies;
            ALTER TABLE sim_companies_new RENAME TO sim_companies;
        """)

    else:
        print(" - OK: schema already uses company_name")

    #
    # ---- 2) MIGRATE sim_leads ----
    #
    print("\n[STEP 2] Checking sim_leads ...")

    if not column_exists(cur, "sim_leads", "score_band"):
        print(" - Adding score_band column")
        cur.execute("ALTER TABLE sim_leads ADD COLUMN score_band TEXT;")

    if not column_exists(cur, "sim_leads", "last_activity"):
        print(" - Adding last_activity column")
        cur.execute("ALTER TABLE sim_leads ADD COLUMN last_activity TEXT;")

    conn.commit()

    #
    # ---- 3) Final Schema Print ----
    #
    print("\n=== FINAL SCHEMA ===")

    print("\nsim_companies:")
    cur.execute("PRAGMA table_info(sim_companies);")
    for row in cur.fetchall():
        print("  ", row)

    print("\nsim_leads:")
    cur.execute("PRAGMA table_info(sim_leads);")
    for row in cur.fetchall():
        print("  ", row)

    conn.close()

    print("\n=== DONE: DB schema aligned with Option A ORM ===")
    print("Restart backend:")
    print("  python -m backend_v2.run_uvicorn")


if __name__ == "__main__":
    main()
