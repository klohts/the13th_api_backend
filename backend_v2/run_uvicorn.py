import os
import uvicorn
from backend_v2.logging_config import configure_logging


def main() -> None:
    """
    Render-ready Uvicorn launcher.
    - Reads PORT from env (Render sets this automatically).
    - Defaults to 5000 for local dev.
    - Logging configured before Uvicorn starts.
    - No reload=True (Render does not support autoreload).
    """

    # Must run before uvicorn.run() so workers inherit logging.
    configure_logging()

    port = int(os.environ.get("PORT", 5000))

    uvicorn.run(
        "backend_v2.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,         # <-- REQUIRED for Render deployment
        log_config=None,      # <-- Ensures your logging_config is used
        use_colors=False,
    )


if __name__ == "__main__":
    main()
