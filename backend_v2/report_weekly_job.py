from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend_v2.database import DATA_DIR, SessionLocal
from backend_v2.services.report_email import send_weekly_report_email
from backend_v2.services.report_service import (
    REPORTS_DIR,
    generate_weekly_intelligence_report,
    render_weekly_report_html,
    save_report_log,
)

logger = logging.getLogger("the13th.report.job")


def _generate_pdf_if_possible(html: str, filename: str) -> Optional[str]:
    """
    Attempt to generate a PDF via WeasyPrint.
    Falls back to saving HTML if WeasyPrint is unavailable.
    """
    try:
        from weasyprint import HTML  # type: ignore

        output_path = REPORTS_DIR / filename
        HTML(string=html).write_pdf(str(output_path))
        logger.info("Weekly report PDF generated at %s", output_path)
        return str(output_path)
    except ImportError:
        logger.warning(
            "WeasyPrint is not installed; saving HTML-only weekly report instead."
        )
        output_path = REPORTS_DIR / (filename.replace(".pdf", ".html"))
        output_path.write_text(html, encoding="utf-8")
        logger.info("Weekly report HTML saved at %s", output_path)
        return str(output_path)
    except Exception as exc:
        logger.error("Failed to generate weekly report PDF: %s", exc, exc_info=True)
        return None


def run_weekly_report(no_email: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        report = generate_weekly_intelligence_report(db)
        html = render_weekly_report_html(report)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"weekly_intel_{ts}.pdf"

        attachment_path = _generate_pdf_if_possible(html, pdf_filename)
        report_id = save_report_log(db, report, attachment_path)

        logger.info("Weekly intelligence report stored with id=%s", report_id)

        if not no_email:
            send_weekly_report_email(
                subject="THE13TH Weekly Intelligence Report",
                body_html=html,
                attachment_path=attachment_path,
            )

    except Exception as exc:
        logger.error("Weekly report job failed: %s", exc, exc_info=True)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run THE13TH Weekly Intelligence Report job."
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Generate and log report only; do not send email.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    run_weekly_report(no_email=args.no_email)


if __name__ == "__main__":
    main()
