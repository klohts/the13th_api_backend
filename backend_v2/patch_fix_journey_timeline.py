import re
from pathlib import Path

TEMPLATE = Path("templates/admin_sim_client_experience.html")
BACKUP = Path("templates/admin_sim_client_experience.bak_journey_timeline_fix")

# -----------------------------------------------------
# Load file
# -----------------------------------------------------
html = TEMPLATE.read_text(encoding="utf-8")

# Backup original
BACKUP.write_text(html, encoding="utf-8")
print(f"[BACKUP] Saved original to {BACKUP}")


# -----------------------------------------------------
# 1. Remove ANY existing extra_body block (to avoid double definitions)
# -----------------------------------------------------
cleaned = re.sub(
    r"{% block extra_body %}[\s\S]*?{% endblock %}",
    "",
    html
)


# -----------------------------------------------------
# 2. Build WORKING extra_body block (based on near.html)
# -----------------------------------------------------
extra_body = """
{% block extra_body %}
<!-- Chart.js (CDN) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
document.addEventListener("DOMContentLoaded", () => {
  /* =====================
     JOURNEY + TIMELINE
     ===================== */

  const journeyData = {{ journey_points | default([], true) | tojson }};
  const timelineData = {{ timeline_events | default([], true) | tojson }};

  console.log("JourneyData →", journeyData);
  console.log("TimelineData →", timelineData);

  /* =====================
     JOURNEY GRAPH
     ===================== */
  const canvas = document.getElementById("journeyChart");
  if (canvas && journeyData.length) {
    new Chart(canvas, {
      type: "line",
      data: {
        labels: journeyData.map(p => p.x),
        datasets: [{
          label: "Journey Intensity",
          data: journeyData.map(p => p.y),
          borderColor: "#a855f7",
          backgroundColor: "rgba(168,85,247,0.20)",
          borderWidth: 2,
          tension: 0.32,
          pointRadius: 3,
          pointBackgroundColor: "#a855f7"
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
  }

  /* =====================
     REPLAY ENGINE
     ===================== */
  const btn = document.getElementById("replay-button");
  const statusEl = document.getElementById("replay-status");
  const bar = document.getElementById("replay-progress-bar");
  const steps = Array.from(document.querySelectorAll(".timeline-item"));

  if (btn && statusEl && bar && steps.length) {
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
  }
});
</script>

{% endblock %}
""".strip()


# -----------------------------------------------------
# 3. Append extra_body before </body>
# -----------------------------------------------------
patched = re.sub(
    r"</body>",
    extra_body + "\n\n</body>",
    cleaned,
    flags=re.IGNORECASE
)

# -----------------------------------------------------
# 4. Save file
# -----------------------------------------------------
TEMPLATE.write_text(patched, encoding="utf-8")
print("[OK] Patched admin_sim_client_experience.html with working journey graph + timeline wiring.")
