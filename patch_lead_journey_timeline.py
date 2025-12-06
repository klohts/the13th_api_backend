#!/usr/bin/env python
"""
THE13TH – Lead Journey Timeline Patch

Run once from repo root:

    python patch_lead_journey_timeline.py

What this does:
- Creates/overwrites backend_v2/routers/admin_lead_detail.py
- Creates/overwrites backend_v2/templates/admin_lead_detail.html
- Ensures backend_v2/main.py imports & includes the router

Result:
- New admin route: GET /admin/leads/{lead_id}
- Shows premium THE13TH-styled Lead Journey Timeline driven by IngestionEvent logs
"""

from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("patch_lead_journey_timeline")

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend_v2"
ROUTERS_DIR = BACKEND_DIR / "routers"
TEMPLATES_DIR = BACKEND_DIR / "templates"
MAIN_PATH = BACKEND_DIR / "main.py"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")
    logger.info(f"[OK] Wrote {path.relative_to(REPO_ROOT)}")


def patch_main_imports() -> None:
    if not MAIN_PATH.exists():
        logger.warning("[WARN] backend_v2/main.py not found; skipping main.py patch")
        return

    text = MAIN_PATH.read_text(encoding="utf-8")

    import_line = "import backend_v2.routers.admin_lead_detail as admin_lead_detail_router"
    include_line = "app.include_router(admin_lead_detail_router.router)"

    changed = False

    if import_line not in text:
        # Insert after pilot_admin import if present, else near top.
        marker = "import backend_v2.routers.pilot_admin as pilot_admin_router"
        if marker in text:
            text = text.replace(
                marker,
                marker + "\n" + import_line,
            )
        else:
            # Fall back: insert after first block of imports.
            parts = text.split("\n")
            insert_idx = 0
            for i, line in enumerate(parts):
                if line.startswith("from ") or line.startswith("import "):
                    insert_idx = i + 1
            parts.insert(insert_idx, import_line)
            text = "\n".join(parts)
        changed = True
        logger.info("[OK] Added admin_lead_detail import to main.py")

    if include_line not in text:
        marker = "app.include_router(pilot_admin_router.router)"
        if marker in text:
            text = text.replace(
                marker,
                marker + "\n" + include_line,
            )
        else:
            # Fallback: append near the bottom after app definition.
            text = text.rstrip() + "\n\n" + include_line + "\n"
        changed = True
        logger.info("[OK] Added admin_lead_detail router include to main.py")

    if changed:
        MAIN_PATH.write_text(text, encoding="utf-8")
    else:
        logger.info("[OK] main.py already wired for admin_lead_detail; no changes")


def scaffold_admin_lead_detail_router() -> None:
    path = ROUTERS_DIR / "admin_lead_detail.py"

    content = """
    from __future__ import annotations

    import logging
    from pathlib import Path
    from typing import List, Optional

    from fastapi import APIRouter, Depends, HTTPException, Request, status
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from backend_v2.db import get_db
    from backend_v2.models.lead import Lead
    from backend_v2.models.ingestion_event import IngestionEvent

    logger = logging.getLogger("the13th.backend_v2.routers.admin_lead_detail")

    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    router = APIRouter(tags=["admin-leads"])


    @router.get("/admin/leads/{lead_id}", response_class=HTMLResponse)
    def lead_detail(
        lead_id: int,
        request: Request,
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        \"\"\"Render the lead detail + journey timeline page.

        This view is read-only and uses IngestionEvent as the first version
        of the journey timeline (ingestion + processing).
        \"\"\"
        lead: Optional[Lead] = db.get(Lead, lead_id)
        if lead is None:
            logger.warning("Lead not found for detail view: id=%s", lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

        events_stmt = (
            select(IngestionEvent)
            .where(IngestionEvent.lead_id == lead_id)
            .order_by(IngestionEvent.created_at.asc())
        )
        events: List[IngestionEvent] = (
            db.execute(events_stmt).scalars().all()
        )

        logger.info(
            "Rendering lead detail (id=%s, tenant=%s, events=%s)",
            lead.id,
            getattr(lead, "tenant_key", None),
            len(events),
        )

        return templates.TemplateResponse(
            "admin_lead_detail.html",
            {
                "request": request,
                "lead": lead,
                "events": events,
            },
        )
    """

    write_file(path, content)


def scaffold_admin_lead_detail_template() -> None:
    path = TEMPLATES_DIR / "admin_lead_detail.html"

    content = """
    {# THE13TH – Lead Detail & Journey Timeline #}
    {% extends "admin_base.html" %}

    {% block title %}Lead Journey · THE13TH{% endblock %}

    {% block content %}
    <div class="min-h-screen bg-[radial-gradient(circle_at_top_left,#4b0082,#0a0014_60%)] text-slate-100 py-10 px-4 sm:px-8 lg:px-12">
        <div class="max-w-6xl mx-auto space-y-8">

            <!-- Breadcrumb / Header -->
            <div class="flex items-center justify-between gap-4">
                <div>
                    <p class="text-xs font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                        Lead Journey
                    </p>
                    <h1 class="mt-2 text-3xl sm:text-4xl font-bold text-[#FCE6C8]">
                        {{ lead.full_name or "Unknown Lead" }}
                    </h1>
                    <p class="mt-1 text-sm text-slate-300">
                        {{ lead.email or "No email on record" }} · {{ lead.phone or "No phone" }}
                    </p>
                </div>
                <div class="text-right">
                    <p class="text-xs font-semibold tracking-[0.2em] uppercase text-purple-200/80">
                        Tenant
                    </p>
                    <p class="mt-1 text-sm text-slate-200">
                        {{ lead.tenant_key or "unassigned" }}
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                        Lead ID · {{ lead.id }}
                    </p>
                </div>
            </div>

            <!-- Top summary cards -->
            <div class="grid gap-4 md:grid-cols-3">
                <div class="rounded-3xl border border-purple-500/40 bg-[#120017]/70 backdrop-blur-xl px-5 py-4 shadow-[0_18px_45px_rgba(0,0,0,0.65)]">
                    <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                        Source
                    </p>
                    <p class="mt-2 text-lg font-semibold text-[#FAD9B9]">
                        {{ lead.source or "Unknown source" }}
                    </p>
                    <p class="mt-1 text-xs text-slate-300">
                        External ID: {{ lead.external_id or "—" }}
                    </p>
                </div>

                <div class="rounded-3xl border border-purple-500/40 bg-[#120017]/70 backdrop-blur-xl px-5 py-4 shadow-[0_18px_45px_rgba(0,0,0,0.65)]">
                    <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                        Assignment
                    </p>
                    <p class="mt-2 text-lg font-semibold text-[#FAD9B9]">
                        {{ lead.assigned_agent or "Not yet assigned" }}
                    </p>
                    <p class="mt-1 text-xs text-slate-300">
                        Created · {{ lead.created_at or "—" }}
                    </p>
                </div>

                <div class="rounded-3xl border border-purple-500/40 bg-[#120017]/70 backdrop-blur-xl px-5 py-4 shadow-[0_18px_45px_rgba(0,0,0,0.65)] flex flex-col justify-between">
                    <div>
                        <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                            Journey Events
                        </p>
                        <p class="mt-2 text-3xl font-bold text-emerald-400">
                            {{ events|length }}
                        </p>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-2">
                        <span class="inline-flex items-center rounded-full bg-emerald-500/20 px-3 py-1 text-[0.7rem] font-semibold text-emerald-300">
                            ● Ingestion
                        </span>
                        <span class="inline-flex items-center rounded-full bg-pink-500/20 px-3 py-1 text-[0.7rem] font-semibold text-pink-300">
                            ● Automation
                        </span>
                        <span class="inline-flex items-center rounded-full bg-orange-500/20 px-3 py-1 text-[0.7rem] font-semibold text-orange-300">
                            ● Agent
                        </span>
                    </div>
                </div>
            </div>

            <div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)]">
                <!-- Journey Timeline -->
                <section class="rounded-3xl border border-purple-500/40 bg-[#120017]/80 backdrop-blur-xl p-6 shadow-[0_22px_55px_rgba(0,0,0,0.75)]">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                                Journey Timeline
                            </p>
                            <h2 class="mt-1 text-xl font-semibold text-[#FCE6C8]">
                                Every touch, from ingestion to automation
                            </h2>
                        </div>
                        <span class="inline-flex items-center rounded-full bg-purple-500/20 px-3 py-1 text-[0.7rem] font-semibold text-purple-100">
                            {{ events|length }} events logged
                        </span>
                    </div>

                    {% if events %}
                        <ol class="mt-6 space-y-4">
                            {% for ev in events %}
                                <li class="relative flex gap-4">
                                    <!-- timeline rail -->
                                    <div class="flex flex-col items-center">
                                        <div class="mt-1 h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_0_4px_rgba(16,185,129,0.25)]"></div>
                                        {% if not loop.last %}
                                            <div class="mt-1 h-full w-px bg-slate-700/70"></div>
                                        {% endif %}
                                    </div>

                                    <!-- card -->
                                    <div class="flex-1 rounded-2xl border border-purple-600/40 bg-[#16002a]/70 px-4 py-3 shadow-[0_14px_35px_rgba(0,0,0,0.7)]">
                                        <div class="flex flex-wrap items-center justify-between gap-2">
                                            <div class="flex items-center gap-2">
                                                <span class="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-emerald-300">
                                                    {{ ev.channel|default("webhook") }}
                                                </span>
                                                <span class="rounded-full bg-slate-800/80 px-2.5 py-0.5 text-[0.65rem] font-medium uppercase tracking-[0.16em] text-slate-300">
                                                    {{ ev.status|upper }}
                                                </span>
                                            </div>
                                            <p class="text-[0.7rem] text-slate-400">
                                                {{ ev.created_at }}
                                            </p>
                                        </div>

                                        <p class="mt-2 text-sm font-semibold text-slate-50">
                                            {{ ev.source or "Ingestion" }}
                                        </p>
                                        <p class="mt-1 text-xs leading-relaxed text-slate-300">
                                            {{ ev.message or "No message recorded for this event." }}
                                        </p>

                                        {% if ev.raw_payload %}
                                            <details class="mt-2 group">
                                                <summary class="cursor-pointer text-[0.7rem] font-semibold text-purple-200 hover:text-purple-100">
                                                    Raw payload
                                                </summary>
                                                <pre class="mt-1 max-h-52 overflow-auto rounded-xl bg-black/50 p-3 text-[0.7rem] text-slate-200">
{{ ev.raw_payload | tojson(indent=2) }}
                                                </pre>
                                            </details>
                                        {% endif %}
                                    </div>
                                </li>
                            {% endfor %}
                        </ol>
                    {% else %}
                        <div class="mt-6 rounded-2xl border border-dashed border-slate-600/70 bg-black/20 p-6 text-sm text-slate-300">
                            No journey events have been logged for this lead yet.
                            Once ingestion and automation run, they will appear here in
                            chronological order.
                        </div>
                    {% endif %}
                </section>

                <!-- Raw lead snapshot -->
                <aside class="space-y-4">
                    <div class="rounded-3xl border border-purple-500/40 bg-[#120017]/80 backdrop-blur-xl p-5 shadow-[0_22px_55px_rgba(0,0,0,0.8)]">
                        <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                            Lead Snapshot
                        </p>
                        <dl class="mt-3 space-y-2 text-xs text-slate-200">
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">Name</dt>
                                <dd class="text-right">{{ lead.full_name or "—" }}</dd>
                            </div>
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">Email</dt>
                                <dd class="text-right">{{ lead.email or "—" }}</dd>
                            </div>
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">Phone</dt>
                                <dd class="text-right">{{ lead.phone or "—" }}</dd>
                            </div>
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">Source</dt>
                                <dd class="text-right">{{ lead.source or "—" }}</dd>
                            </div>
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">External ID</dt>
                                <dd class="text-right">{{ lead.external_id or "—" }}</dd>
                            </div>
                            <div class="flex justify-between gap-3">
                                <dt class="text-slate-400">Created</dt>
                                <dd class="text-right">{{ lead.created_at or "—" }}</dd>
                            </div>
                        </dl>
                    </div>

                    <div class="rounded-3xl border border-purple-500/40 bg-[#120017]/80 backdrop-blur-xl p-5 shadow-[0_22px_55px_rgba(0,0,0,0.8)]">
                        <p class="text-[0.7rem] font-semibold tracking-[0.25em] uppercase text-purple-200/80">
                            Raw Lead Payload
                        </p>
                        {% if lead.raw_payload %}
                            <pre class="mt-3 max-h-80 overflow-auto rounded-2xl bg-black/50 p-3 text-[0.7rem] leading-relaxed text-slate-200">
{{ lead.raw_payload | tojson(indent=2) }}
                            </pre>
                        {% else %}
                            <p class="mt-3 text-xs text-slate-300">
                                This lead has no raw_payload stored yet.
                            </p>
                        {% endif %}
                    </div>
                </aside>
            </div>
        </div>
    </div>
    {% endblock %}
    """

    write_file(path, content)


def main() -> None:
    logger.info("=== THE13TH – Lead Journey Timeline Patch ===")
    scaffold_admin_lead_detail_router()
    scaffold_admin_lead_detail_template()
    patch_main_imports()
    logger.info("=== Done. Deploy / restart backend_v2 and visit /admin/leads/{id} ===")


if __name__ == "__main__":
    main()
