from __future__ import annotations

import logging
from typing import Optional

try:
    from weasyprint import HTML  # type: ignore
except Exception:  # pragma: no cover
    HTML = None  # type: ignore

logger = logging.getLogger("the13th.report_pdf")


class PdfRenderingUnavailable(RuntimeError):
    """Raised when WeasyPrint (or PDF rendering) is not available."""


def generate_pdf_from_html(html: str, title: Optional[str] = None) -> bytes:
    """
    Convert an HTML string into a PDF byte stream using WeasyPrint.

    Raises PdfRenderingUnavailable if WeasyPrint is not installed or fails.
    """
    if HTML is None:
        logger.error(
            "WeasyPrint is not installed. Install with: pip install weasyprint"
        )
        raise PdfRenderingUnavailable(
            "PDF rendering is not available. Install 'weasyprint' to enable it."
        )

    try:
        doc = HTML(string=html, base_url=".")
        pdf_bytes: bytes = doc.write_pdf()
        return pdf_bytes
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to generate PDF from HTML: %r", exc)
        raise PdfRenderingUnavailable(
            f"PDF rendering failed: {exc!r}"
        ) from exc
