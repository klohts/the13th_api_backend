from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime


def patch_client_experience_template() -> None:
    project_root = Path(__file__).resolve().parents[1]
    template_path = project_root / "templates" / "admin_sim_client_experience.html"

    if not template_path.exists():
        print(f"[ERROR] Template not found: {template_path}", file=sys.stderr)
        return

    html = template_path.read_text(encoding="utf-8")

    marker = "<script>\n/* === THE13TH Replay Engine === */"
    idx = html.find(marker)
    if idx == -1:
        print("[SKIP] Replay engine script block not found; nothing to patch.")
        return

    # Everything up to the first replay script stays exactly as-is
    before = html[:idx]

    # New tail: close the content block, then add scripts via extra_body.
    # Layout markup is *not* touched.
    new_tail = """{% endblock %}

{% block extra_body %}
<script src="/static/js/chart.min.js"></script>

<script>
/* === THE13TH Replay Engine === */
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("replay-button");
  const statusEl = document.getElementById("replay-status");
  const bar = document.getElementById("replay-progress-bar");
  const steps = Array.from(document.querySelectorAll(".timeline-item"));

  if (!btn || !statusEl || !bar || steps.length === 0) return;

  btn.addEventListener("click", () => {
    steps.forEach((s) => s.classList.remove("replay-highlight"));
    statusEl.textContent = "Replaying journey…";
    bar.style.width = "0%";

    const total = steps.length;
    const duration = 5000;
    const interval = duration / total;
    let i = 0;

    const timer = setInterval(() => {
      if (i >= total) {
        clearInterval(timer);
        statusEl.textContent = "Replay complete.";
        bar.style.width = "100%";
        return;
      }

      const step = steps[i];
      if (step) {
        step.classList.add("replay-highlight");
        step.scrollIntoView({ behavior: "smooth", block: "center" });
        bar.style.width = (((i + 1) / total) * 100) + "%";
      }
      i += 1;
    }, interval);
  });
});
</script>

<script>
/* === THE13TH Journey Chart Engine === */
document.addEventListener("DOMContentLoaded", () => {
  const journeyData = {{ journey_points | tojson }};
  const timelineData = {{ timeline_events | tojson }};

  console.log("Journey data inside extra_body >>>", journeyData);
  console.log("Timeline data inside extra_body >>>", timelineData);

  const cj = document.getElementById("journeyChart");
  if (cj && Array.isArray(journeyData) && journeyData.length) {
    new Chart(cj, {
      type: "line",
      data: {
        labels: journeyData.map((p) => p.x),
        datasets: [{
          label: "Journey Intensity",
          data: journeyData.map((p) => p.y),
          borderColor: "#a855f7",
          backgroundColor: "rgba(168,85,247,0.2)",
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#a855f7",
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            ticks: { color: "#e5e7eb" },
            grid: { color: "rgba(255,255,255,0.08)" },
          },
          x: {
            ticks: { color: "#e5e7eb" },
            grid: { color: "rgba(255,255,255,0.06)" },
          },
        },
      },
    });
  }
});
</script>
{% endblock %}
"""

    # Backup once per timestamped file
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = template_path.with_suffix(f".html.bak_client_experience_{ts}")
    backup_path.write_text(html, encoding="utf-8")
    print(f"[BACKUP] {backup_path}")

    template_path.write_text(before + new_tail, encoding="utf-8")
    print("[OK] Patched admin_sim_client_experience.html (journey graph + timeline).")


if __name__ == "__main__":
    patch_client_experience_template()
