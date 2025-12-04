from __future__ import annotations

import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.services.report_viewer_service import (
    list_reports,
    get_report_detail,
)
from backend_v2.services.report_pdf import (
    generate_pdf_from_html,
    PdfRenderingUnavailable,
)

logger = logging.getLogger("the13th.admin_reports.router")

router = APIRouter(prefix="/admin/reports", tags=["Admin Reports"])


@router.get("/", response_class=HTMLResponse)
def admin_reports_index(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Admin view: list of simulation reports from SimReportLog.
    """
    reports = list_reports(db)
    context = {
        "request": request,
        "admin": admin,
        "reports": reports,
    }
    return render_template("admin_report_list.html", context)


@router.get("/{report_id}", response_class=HTMLResponse)
def admin_report_detail(
    report_id: int,
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Admin view: single report detail.
    """
    report = get_report_detail(db, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    context = {
        "request": request,
        "admin": admin,
        "report": report,
    }
    return render_template("admin_report_detail.html", context)


@router.get("/{report_id}/pdf")
def admin_report_pdf(
    report_id: int,
    download: bool = Query(
        False,
        description="If true, force download. If false, render inline.",
    ),
    request: Request = None,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Return a PDF rendition of the report.

    - If `download=true`, Content-Disposition: attachment
    - Else, Content-Disposition: inline
    """
    report = get_report_detail(db, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    html_body = report.get("html_body") or ""
    if not html_body:
        # Fallback: embed raw JSON in a simple HTML shell
        raw_meta = report.get("raw_meta_json", "")
        html_body = (
            "<html><body>"
            "<h1>Report has no dedicated HTML body.</h1>"
            "<pre style='font-size: 11px; white-space: pre-wrap;'>"
            + (raw_meta or "")
            + "</pre>"
            "</body></html>"
        )

    title = report.get("title") or f"report-{report_id}"

    try:
        pdf_bytes = generate_pdf_from_html(html_body, title=title)
    except PdfRenderingUnavailable as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    filename = f"{title.replace(' ', '-').lower()}-{report_id}.pdf"
    disposition = "attachment" if download else "inline"

    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"'
    }

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=headers,
    )
