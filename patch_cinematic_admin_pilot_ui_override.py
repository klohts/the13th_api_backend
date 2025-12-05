#!/usr/bin/env python3
"""
Stronger cinematic override for THE13TH Admin Pilot Dashboard.

- Injects a <style> block *at the end of <head>* so it wins cascade.
- Uses very general selectors (body, table, th, td) with !important,
  which only affect this template.
"""

from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "backend_v2" / "templates" / "admin_pilots.html"

STYLE_BLOCK = """
    <!-- Cinematic Admin Pilot UI Override -->
    <style id="pilot-admin-cinematic-override">
      body {
        font-size: 17px !important;
        line-height: 1.6 !important;
        -webkit-font-smoothing: antialiased;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 1rem !important;
      }

      thead {
        background: linear-gradient(
          to right,
          rgba(0, 0, 0, 0.8),
          rgba(20, 5, 30, 0.95)
        ) !important;
      }

      th {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 12px 18px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
      }

      td {
        font-size: 1rem !important;
        padding: 13px 18px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
        vertical-align: middle !important;
      }

      tbody tr:last-child td {
        border-bottom: none !important;
      }

      tbody tr {
        transition: background 160ms ease-out, transform 160ms ease-out;
      }

      tbody tr:hover {
        background: radial-gradient(
          circle at left,
          rgba(255, 144, 64, 0.16),
          transparent 65%
        ) !important;
        transform: translateY(-1px);
      }

      .status-badge {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        border-radius: 999px !important;
        padding: 5px 11px !important;
      }

      .pilots-empty-state,
      .empty-row td {
        font-size: 1rem !important;
        opacity: 0.95 !important;
        text-align: center;
        padding: 22px 18px !important;
      }
    </style>
"""

def apply_patch() -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Avoid double-inserting the override
    if 'id="pilot-admin-cinematic-override"' in html:
        print("Override style already present.")
        return

    if "</head>" in html:
        patched = html.replace("</head>", STYLE_BLOCK + "\n</head>")
    else:
        # Fallback: append at top
        patched = STYLE_BLOCK + "\n" + html

    TEMPLATE_PATH.write_text(patched, encoding="utf-8")
    print("Cinematic override injected into admin_pilots.html")

if __name__ == "__main__":
    apply_patch()
