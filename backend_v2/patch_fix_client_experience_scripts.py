import re
from pathlib import Path

TEMPLATE_PATH = Path("templates/admin_sim_client_experience.html")
BACKUP_PATH = Path("templates/admin_sim_client_experience.bak_scriptsfix")

# Read file
orig = TEMPLATE_PATH.read_text(encoding="utf-8")

# Backup
BACKUP_PATH.write_text(orig, encoding="utf-8")
print(f"[BACKUP] Saved to {BACKUP_PATH}")

# 1. Remove any existing <script> blocks AFTER content block but BEFORE endblock
cleaned = re.sub(
    r"{% endblock %}\s*<script[\s\S]*?{% endblock %}",
    "{% endblock %}",
    orig
)

# 2. Extract all <script>...</script> blocks at bottom of the file
script_blocks = re.findall(r"<script[\s\S]*?</script>", orig)

# 3. Build the extra_body block
extra_body_block = (
    "{% block extra_body %}\n"
    '<script src="/static/js/chart.min.js"></script>\n\n'
    + "\n\n".join(script_blocks)
    + "\n{% endblock %}"
)

# 4. Append to end of file, but before final </html>
patched = re.sub(
    r"</body>\s*</html>",
    extra_body_block + "\n</body></html>",
    cleaned
)

# Write patched file
TEMPLATE_PATH.write_text(patched, encoding="utf-8")
print("[OK] admin_sim_client_experience.html patched with working journey graph + timeline.")
