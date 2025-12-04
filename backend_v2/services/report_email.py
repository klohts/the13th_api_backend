from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

logger = logging.getLogger("the13th.report.email")


def send_weekly_report_email(
    subject: str,
    body_html: str,
    attachment_path: Optional[str] = None,
) -> None:
    """
    Send Weekly Intelligence Report to the admin-only recipient.

    Required env vars (Option A):
      - THE13TH_REPORT_SENDER
      - THE13TH_REPORT_RECIPIENT
      - THE13TH_SMTP_HOST
      - THE13TH_SMTP_PORT
      - THE13TH_EMAIL_USER
      - THE13TH_EMAIL_PASS
    """
    sender = os.getenv("THE13TH_REPORT_SENDER")
    recipient = os.getenv("THE13TH_REPORT_RECIPIENT")
    smtp_host = os.getenv("THE13TH_SMTP_HOST")
    smtp_port = int(os.getenv("THE13TH_SMTP_PORT", "587"))
    smtp_user = os.getenv("THE13TH_EMAIL_USER")
    smtp_pass = os.getenv("THE13TH_EMAIL_PASS")

    if not sender or not recipient or not smtp_host or not smtp_user or not smtp_pass:
        logger.warning(
            "Weekly report email skipped; missing SMTP configuration or recipient."
        )
        return

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content("Your weekly intelligence report is attached.")
    msg.add_alternative(body_html, subtype="html")

    if attachment_path:
        path_obj = Path(attachment_path)
        if path_obj.is_file():
            with path_obj.open("rb") as f:
                data = f.read()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="pdf",
                filename=path_obj.name,
            )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Weekly intelligence report email sent to %s", recipient)
    except Exception as exc:
        logger.error("Failed to send weekly report email: %s", exc, exc_info=True)
