
from backend_v2.database import engine
from backend_v2.models.sim_activity_log import Base

def run():
    print("[MIGRATION] Creating sim_activity_log table…")
    Base.metadata.create_all(bind=engine)
    print("[DONE] sim_activity_log table created.")

if __name__ == "__main__":
    run()
