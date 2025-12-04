from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime


def patch():
    root = Path(__file__).resolve().parents[1]
    tpl = root / "templates" / "admin_sim_client_experience.html"

    if not tpl.exists():
        print(f"[ERROR] Missing file: {tpl}")
        return

    original = tpl.read_text(encoding="utf-8")

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = tpl.with_suffix(f".html.bak_fix_extra_body_{ts}")
    backup.write_text(original, encoding="utf-8")
    print(f"[BACKUP] {backup}")

    html = original

    # ---------------------------------------------------------
    # 1. REMOVE ALL EXISTING extra_body BLOCKS
    # ---------------------------------------------------------
    html = re.sub(
        r"{% block extra_body %}.*?{% endblock %}",
        "",
        html,
        flags=re.DOTALL,
    )

    # ---------------------------------------------------------
    # 2. REMOVE any leftover bottom </script> blocks if they stray
    #    (we re-add them properly)
    # ---------------------------------------------------------
    html = re.sub(
        r"<script>\/\* === THE13TH Journey Chart Engine ===[\s\S]*?</script>",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<script>\/\* === THE13TH Replay Engine ===[\s\S]*?</script>",
        "",
        html,
        flags=re.DOTALL,
    )

    # ---------------------------------------------------------
    # 3. Append OUR SINGLE CLEAN extra_body
    # ---------------------------------------------------------
    extra = """
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
    steps.forEach(s => s.classList.remove("replay-highlight"));
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

  const cj = document.getElementById("journeyChart");
  if (!cj || !Array.isArray(journeyData) || journeyData.length === 0) return;

  new Chart(cj, {
    type: "line",
    data: {
      labels: journeyData.map(p => p.x),
      datasets: [{
        label: "Journey Intensity",
        data: journeyData.map(p => p.y),
        borderColor: "#a855f7",
        backgroundColor: "rgba(168,85,247,0.2)",
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: "#a855f7",
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: { color: "#e5e7eb" },
          grid: { color: "rgba(255,255,255,0.08)" }
        },
        x: {
          ticks: { color: "#e5e7eb" },
          grid: { color: "rgba(255,255,255,0.06)" }
        }
      }
    }
  });
});
</script>
{% endblock %}
"""

    updated = html.rstrip() + "\n\n" + extra

    tpl.write_text(updated, encoding="utf-8")
    print("[OK] FIXED | All extra_body conflicts removed + one clean block added")


if __name__ == "__main__":
    patch()

