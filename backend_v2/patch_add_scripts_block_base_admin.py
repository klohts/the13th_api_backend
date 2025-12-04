import re
import shutil
from pathlib import Path

BASE = Path("backend_v2") / ".." / "templates" / "base_admin.html"
BASE = BASE.resolve()

backup = BASE.with_suffix(".bak_scripts_patch")
shutil.copy2(BASE, backup)
print(f"[BACKUP] {backup}")

content = BASE.read_text()

# Check if block already exists
if "{% block scripts %}" in content:
    print("[SKIP] scripts block already exists.")
    exit(0)

# Insert before closing </html>
patched = re.sub(
    r"</html>",
    """
    {% block scripts %}
    {% endblock %}
</html>
""",
    content,
    count=1,
    flags=re.IGNORECASE | re.DOTALL,
)

BASE.write_text(patched)
print("[OK] scripts block injected.")
