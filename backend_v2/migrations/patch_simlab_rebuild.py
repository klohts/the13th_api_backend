"""
patch_simlab_rebuild.py
-----------------------------------------
Rebuilds the Simulation Lab database inside:
    /home/hp/AIAutomationProjects/saas_demo/the13th/data/the13th_allinone.db

This script:
  - Drops all sim_* tables
  - Recreates them with correct schema
  - Seeds 5 simulation companies
  - Seeds ≈250 leads per company
  - Seeds score bands & deal stages
  - Seeds agent activity baseline
  - Fully restores Simulation Lab Overview functionality

Safe to run multiple times.

Run with:
  python backend_v2/migrations/patch_simlab_rebuild.py
"""

import logging
import random
from datetime import datetime, timedelta

from sqlalchemy import text
from backend_v2.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("patch_simlab_rebuild")


# ---------------------------------------------------------
#  CONFIG
# ---------------------------------------------------------
SIM_COMPANIES = [
    "Horizon Estates",
    "Prime Realty Group",
    "MetroKey Properties",
    "Summit Home Advisors",
    "BlueOak Living",
]

LEADS_PER_COMPANY = 250

SCORE_BANDS = ["Low", "Medium", "High", "Elite"]
DEAL_STAGES = ["New", "Nurturing", "Won", "Lost"]
AGENTS = ["Agent A", "Agent B", "Agent C"]


# ---------------------------------------------------------
#  RANDOM GENERATORS
# ---------------------------------------------------------
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer",
    "Michael", "Linda", "William", "Elizabeth", "David", "Barbara",
    "Joseph", "Susan", "Christopher", "Jessica", "Daniel", "Sarah",
    "Paul", "Karen"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
    "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez",
    "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin"
]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_price():
    return random.randint(150_000, 1_500_000)


def random_scoreband():
    return random.choices(SCORE_BANDS, weights=[0.4, 0.3, 0.2, 0.1])[0]


def random_dealstage():
    return random.choices(DEAL_STAGES, weights=[0.60, 0.30, 0.07, 0.03])[0]


def random_date():
    days_ago = random.randint(0, 60)
    return datetime.utcnow() - timedelta(days=days_ago)


# ---------------------------------------------------------
#  MAIN DATABASE OPERATION
# ---------------------------------------------------------
def run():
    db = SessionLocal()
    logger.info("Connected to Simulation Lab DB.")

    # --------------------------------------------
    # 1. DROP existing sim tables if they exist
    # --------------------------------------------
    logger.info("Dropping existing sim_* tables (if any).")

    drop_sql = [
        "DROP TABLE IF EXISTS sim_leads;",
        "DROP TABLE IF EXISTS sim_bursts;",
        "DROP TABLE IF EXISTS sim_companies;",
        "DROP TABLE IF EXISTS sim_agent_activity;",
    ]
    for stmt in drop_sql:
        db.execute(text(stmt))

    db.commit()
    logger.info("All sim_* tables dropped.")

    # --------------------------------------------
    # 2. CREATE TABLES
    # --------------------------------------------
    logger.info("Creating Simulation Lab tables...")

    db.execute(text("""
        CREATE TABLE sim_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    db.execute(text("""
        CREATE TABLE sim_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER,
            score_band TEXT,
            deal_stage TEXT,
            last_activity TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES sim_companies(id)
        );
    """))

    db.execute(text("""
        CREATE TABLE sim_bursts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            burst_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES sim_companies(id)
        );
    """))

    db.execute(text("""
        CREATE TABLE sim_agent_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            actions INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    db.commit()
    logger.info("Simulation Lab tables created.")

    # --------------------------------------------
    # 3. SEED COMPANIES
    # --------------------------------------------
    logger.info("Seeding companies...")

    for name in SIM_COMPANIES:
        db.execute(
            text("INSERT INTO sim_companies (company_name) VALUES (:n)"),
            {"n": name}
        )
    db.commit()

    company_rows = db.execute(text("SELECT id, company_name FROM sim_companies")).fetchall()
    logger.info(f"Seeded {len(company_rows)} companies.")

    # --------------------------------------------
    # 4. SEED LEADS (250 per company)
    # --------------------------------------------
    logger.info("Seeding leads (this may take a few seconds)...")

    for company in company_rows:
        cid = company.id
        for _ in range(LEADS_PER_COMPANY):
            db.execute(text("""
                INSERT INTO sim_leads
                (company_id, name, price, score_band, deal_stage, last_activity)
                VALUES
                (:cid, :name, :price, :sb, :ds, :la)
            """), {
                "cid": cid,
                "name": random_name(),
                "price": random_price(),
                "sb": random_scoreband(),
                "ds": random_dealstage(),
                "la": random_date(),
            })

    db.commit()
    logger.info("Leads seeded successfully.")

    # --------------------------------------------
    # 5. SEED AGENT ACTIVITY
    # --------------------------------------------
    logger.info("Seeding agent activity...")
    for agent in AGENTS:
        db.execute(text("""
            INSERT INTO sim_agent_activity
            (agent_name, actions)
            VALUES (:a, :act)
        """), {
            "a": agent,
            "act": random.randint(10, 100)
        })
    db.commit()

    logger.info("Agent activity seeded.")

    # --------------------------------------------
    # 6. Confirm completion
    # --------------------------------------------
    logger.info("Simulation Lab rebuild complete.")
    logger.info("You may now restart backend_v2.")


if __name__ == "__main__":
    run()
