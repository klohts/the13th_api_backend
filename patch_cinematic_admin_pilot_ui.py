#!/usr/bin/env python3
"""
Cinematic upgrade for THE13TH Admin Pilot Dashboard UI.

- Larger, more readable typography
- Cinematic card + table styling
- Softer shadows and row hover treatment
- Keeps existing color scheme / theme

Safely injects a <style> block into backend_v2/templates/admin_pilots.html.
"""

from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "backend_v2" / "templates" / "admin_pilots.html"

STYLE_BLOCK = """
    <!-- Cinematic Admin Pilot UI Patch -->
    <style>
      body {
        font-size: 17px;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
      }

      /* Outer shell */
      .admin-pilot-shell {
        max-width: 1200px;
        margin: 0 auto;
        padding: 48px 32px 80px;
      }

      .admin-pilot-header {
        margin-bottom: 32px;
      }

      .admin-pilot-header h1 {
        font-size: 1.8rem;
        letter-spacing: 0.04em;
      }

      .admin-pilot-header p {
        margin-top: 8px;
        font-size: 0.98rem;
        opacity: 0.85;
      }

      /* Legend + tags */
      .pilot-legend {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
        font-size: 0.9rem;
        opacity: 0.9;
      }

      .legend-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 500;
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.06);
      }

      .legend-pill-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
      }

      /* Main card */
      .pilot-table-card {
        border-radius: 22px;
        border: 1px solid rgba(255, 144, 64, 0.16);
        background: radial-gradient(circle at top left,
                    rgba(255, 144, 64, 0.09),
                    rgba(5, 0, 10, 0.96));
        box-shadow:
          0 26px 60px rgba(0, 0, 0, 0.85),
          0 0 0 1px rgba(255, 255, 255, 0.02);
        overflow: hidden;
      }

      /* Table layout */
      .pilot-table {
        width: 100%;
        border-collapse: collapse;
      }

      .pilot-table thead {
        background: linear-gradient(
          to right,
          rgba(0, 0, 0, 0.75),
          rgba(20, 5, 30, 0.9)
        );
      }

      .pilot-table th {
        font-size: 0.95rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 12px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        white-space: nowrap;
      }

      .pilot-table td {
        font-size: 1rem;
        padding: 13px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        vertical-align: middle;
      }

      .pilot-table tbody tr:last-child td {
        border-bottom: none;
      }

      .pilot-table tbody tr {
        transition: background 160ms ease-out, transform 160ms ease-out;
      }

      .pilot-table tbody tr:hover {
        background: radial-gradient(
          circle at left,
          rgba(255, 144, 64, 0.18),
          transparent 65%
        );
        transform: translateY(-1px);
      }

      /* Empty state row */
      .pilot-table .empty-row td {
        text-align: center;
        font-size: 1rem;
        padding: 22px 18px;
        opacity: 0.92;
      }

      /* Status + action badges */
      .status-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 96px;
        padding: 5px 11px;
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.09);
        background: linear-gradient(
          to bottom right,
          rgba(0, 0, 0, 0.85),
          rgba(20, 5, 30, 0.95)
        );
        box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7);
      }

      .status-badge--requested {
        border-color: rgba(255, 199, 94, 0.85);
        box-shadow: 0 0 12px rgba(255, 199, 94, 0.35);
      }

      .status-badge--approval-sent {
        border-color: rgba(120, 219, 255, 0.85);
        box-shadow: 0 0 12px rgba(120, 219, 255, 0.35);
      }

      .status-badge--active {
        border-color: rgba(72, 240, 164, 0.95);
        box-shadow: 0 0 16px rgba(72, 240, 164, 0.45);
      }

      .primary-action-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 7px 16px;
        border-radius: 999px;
        border: none;
        font-size: 0.92rem;
        font-weight: 500;
        cursor: pointer;
        background: radial-gradient(circle at top left,
                   rgba(255, 144, 64, 0.28),
                   rgba(255, 92, 0, 0.85));
        box-shadow:
          0 12px 28px rgba(0, 0, 0, 0.9),
          0 0 0 1px rgba(255, 255, 255, 0.08);
        transition:
          transform 130ms ease-out,
          box-shadow 130ms ease-out,
          background 130ms ease-out,
          opacity 130ms ease-out;
      }

      .primary-action-btn:hover {
        transform: translateY(-1px);
        box-shadow:
          0 16px 42px rgba(0, 0, 0, 0.95),
          0 0 0 1px rgba(255, 255, 255, 0.16);
        opacity: 0.98;
      }

      .primary-action-btn:active {
        transform: translateY(0);
        box-shadow:
          0 6px 20px rgba(0, 0, 0, 0.9),
          0 0 0 1px rgba(255, 255, 255, 0.12);
      }

      /* Refresh + timestamp */
      .pilot-toolbar {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
        margin-bottom: 18px;
        font-size: 0.88rem;
        opacity: 0.9;
      }

      .refresh-pill {
        padding: 5px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(0, 0, 0, 0.55);
        cursor: pointer;
        font-size: 0.86rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background 120ms ease-out, border-color 120ms ease-out;
      }

      .refresh-pill:hover {
        background: rgba(255, 144, 64, 0.28);
        border-color: rgba(255, 144, 64, 0.9);
      }

      .refresh-dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: rgba(144, 255, 190, 0.9);
      }
    </style>
"""

def apply_patch() -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    if "<!-- Cinematic Admin Pilot UI Patch -->" in html:
        print("Cinematic patch already applied.")
        return

    if "<head>" in html:
        patched = html.replace("<head>", "<head>\n" + STYLE_BLOCK)
    else:
        # fallback: prepend at top
        patched = STYLE_BLOCK + "\n" + html

    TEMPLATE_PATH.write_text(patched, encoding="utf-8")
    print("Cinematic Admin Pilot UI patch applied.")

if __name__ == "__main__":
    apply_patch()
