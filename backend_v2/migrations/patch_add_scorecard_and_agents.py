import logging
from sqlalchemy import text
from backend_v2.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def run():
    db = SessionLocal()

    # ------------------------------
    # Add score_band column
    # ------------------------------
    try:
        db.execute(text("""
            ALTER TABLE sim_leads
            ADD COLUMN score_band TEXT DEFAULT 'Low'
        """))
        logger.info("Added column sim_leads.score_band")
    except Exception as e:
        logger.info(f"score_band exists or cannot be added: {e}")

    # ------------------------------
    # Create sim_agent_activity table
    # ------------------------------
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS sim_agent_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                actions INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        logger.info("sim_agent_activity table created or already exists")
    except Exception as e:
        logger.error(f"Error creating sim_agent_activity: {e}")

    db.commit()
    db.close()
    logger.info("Migration complete.")

if __name__ == "__main__":
    run()
