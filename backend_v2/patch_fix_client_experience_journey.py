import re
from pathlib import Path

TARGET = Path("templates/admin_sim_client_experience.html")
BACKUP = Path("templates/admin_sim_client_experience.bak_journeyfix")

print("[THE13TH] Fixing journey graph + timeline...")

if not TARGET.exists():
    print("[ERROR] admin_sim_client_experience.html not found.")
    exit(1)

BACKUP.write_text(TARGET.read_text(), encoding="utf-8")
print(f"[BACKUP] Saved → {BACKUP}")

content = TARGET.read_text(encoding="utf-8")

# ---------------------------------------------------------
# 1. Replace wrong journey-chart div with correct canvas ID
# ---------------------------------------------------------
content = re.sub(
    r'<div id="journey-chart"[^>]*>.*?</div>',
    '<canvas id="journeyChart" style="width:100%; height:100%;"></canvas>',
    content,
    flags=re.DOTALL
)

# ---------------------------------------------------------
# 2. Remove unused {% block extra_body %} (base does not support it)
# ---------------------------------------------------------
content = re.sub(
    r'\{% block extra_body %}.*?\{% endblock %}',
    '',
    content,
    flags=re.DOTALL
)

# ---------------------------------------------------------
# 3. Append the working JS (taken from near.html)
# ---------------------------------------------------------
JS_SNIPPET = """
<!-- THE13TH Journey + Timeline Scripts (Injected by patch) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
document.addEventListener("DOMContentLoaded", () => {
    const journeyData = {{ journey_points | default([]) | tojson }};
    const ctx = document.getElementById("journeyChart");

    if (ctx && journeyData.length) {
        new Chart(ctx, {
            type: "line",
            data: {
                labels: journeyData.map(p => p.x),
                datasets: [{
                    label: "Journey intensity",
                    data: journeyData.map(p => p.y),
                    borderWidth: 2,
                    borderColor: "#a855f7",
                    backgroundColor: "rgba(168,85,247,0.2)",
                    tension: 0.35,
                    pointRadius: 3,
                    pointBackgroundColor: "#a855f7",
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false }},
                scales: {
                    x: {
                        ticks: { color: "#9ca3af" },
                        grid: { color: "rgba(148,163,184,0.16)" }
                    },
                    y: {
                        ticks: { color: "#9ca3af" },
                        grid: { color: "rgba(148,163,184,0.16)" }
                    }
                }
            }
        });
    }
});
</script>

<script>
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
"""

content += "\n\n" + JS_SNIPPET

TARGET.write_text(content, encoding="utf-8")
print("[SUCCESS] Journey graph & timeline scripts injected.")
