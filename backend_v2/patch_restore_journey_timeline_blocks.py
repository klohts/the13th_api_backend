from pathlib import Path
import re

TEMPLATE = Path("templates/admin_sim_client_experience.html")
BACKUP = Path("templates/admin_sim_client_experience.bak_restore_blocks")

html = TEMPLATE.read_text(encoding="utf-8")
BACKUP.write_text(html, encoding="utf-8")
print(f"[BACKUP] Saved → {BACKUP}")

# ----- 1. Insert the correct JOURNEY GRAPH section (from near.html) -----
journey_block = """
<section class="card" style="padding:18px 18px 16px;">
  <div class="cj-section-title">Journey graph</div>
  <div class="cj-section-subtitle">
    Each dot is a touchpoint: replies, nudges, questions, and key decision moments.
  </div>

  <div class="journey-chart-shell">
    <canvas id="journeyChart" style="width:100%; height:100%; display:block;"></canvas>
    <div class="journey-chart-placeholder">
      {% if journey_points %}
        The journey curve is rendering above. Every point reflects a touchpoint this lead experienced.
      {% else %}
        Waiting for simulation data. Run a persona above to see the journey curve and key decision points.
      {% endif %}
    </div>
  </div>

  <div class="stage-pills">
    {% for stage_label in journey_stage_labels or [] %}
      <span class="stage-pill">{{ stage_label }}</span>
    {% endfor %}
    {% if not journey_stage_labels %}
      <span class="stage-pill">New inquiry</span>
      <span class="stage-pill">Qualified</span>
      <span class="stage-pill">Active search</span>
      <span class="stage-pill">Offer / Negotiation</span>
      <span class="stage-pill">Won / Closed</span>
    {% endif %}
  </div>
</section>
"""

html = re.sub(
    r"<section class=\"card\"[^>]*>\s*<div class=\"cj-section-title\">Journey graph[\s\S]*?</section>",
    journey_block,
    html,
    flags=re.MULTILINE
)

# ----- 2. Insert the working TIMELINE section (from near.html) -----
timeline_block = """
<section class="card" style="padding:18px 18px 16px;">
  <div class="cj-section-title">Conversation timeline</div>
  <div class="cj-section-subtitle">
    A readable timeline of the back-and-forth between your assistant and the client.
  </div>

  <button id="replay-button" class="btn-subtle" style="margin-bottom:10px;">Replay this journey</button>
  <div id="replay-status" class="fade-late" style="margin-bottom:6px;">Ready to replay this simulated journey.</div>
  <div class="replay-progress">
    <div id="replay-progress-bar" class="replay-bar"></div>
  </div>

  <div class="timeline fade-late">
    {% if timeline_events %}
      {% for ev in timeline_events %}
        <article class="timeline-item">
          <div class="fade-late timeline-label">{{ ev.label }}</div>
          <div class="fade-late timeline-headline">{{ ev.headline }}</div>
          <div class="fade-late timeline-meta">{{ ev.meta }}</div>
        </article>
      {% endfor %}
    {% else %}
      <article class="timeline-item">
        <div class="fade-late timeline-label">No conversation yet</div>
        <div class="fade-late timeline-headline">Run the simulation above to populate the timeline.</div>
        <div class="fade-late timeline-meta">
          You’ll see every touchpoint, including generated replies.
        </div>
      </article>
    {% endif %}
  </div>
</section>
"""

html = re.sub(
    r"<section class=\"card\"[^>]*>\s*<div class=\"cj-section-title\">Conversation timeline[\s\S]*?</section>",
    timeline_block,
    html,
    flags=re.MULTILINE
)

# ----- SAVE -----
TEMPLATE.write_text(html, encoding="utf-8")
print("[OK] Restored working Journey Graph + Timeline blocks.")
