from pathlib import Path
import json
import re

root = Path(".")
index = root / "frontend" / "index.html"
seed = root / "data" / "trips" / "current_2026-09_2027-08.json"

text = index.read_text(encoding="utf-8")
baseline = json.loads(seed.read_text(encoding="utf-8"))

# If an earlier v3.3 overlay was tried locally, remove those includes.
text = text.replace('<link rel="stylesheet" href="/tracker-v3.3.css">\n', "")
text = text.replace('<script src="/tracker-v3.3.js"></script>\n', "")

# Explicitly include assets in index.html so a static Netlify deployment gets
# the same UI as the Railway-served root page.
for asset in ["/hal-v2.css", "/tracker-v3.4.css"]:
    if asset not in text:
        text = text.replace("</head>", f'<link rel="stylesheet" href="{asset}">\n</head>')

for asset in ["/hal-v2.js", "/tracker-v3.4.js"]:
    if asset not in text:
        text = text.replace("</body>", f'<script src="{asset}"></script>\n</body>')

# Replace the inline current-year array with a literal zero-trip baseline.
lines = ["        const employees = ["]
for employee in baseline["employees"]:
    name = json.dumps(employee["name"], ensure_ascii=False)
    email = json.dumps(employee.get("email", ""), ensure_ascii=False)
    lines.append(f"            {{ name: {name}, email: {email}, trips: [] }},")
lines.append("        ];")
replacement = "\n".join(lines)

pattern = r"const employees = \[.*?\n\s*\];\n\n\s*const MAX_DAYS"
new_text, count = re.subn(
    pattern,
    replacement + "\n\n        const MAX_DAYS",
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("Could not find the inline employees array to reset.")
text = new_text

# Prevent old counters flashing before live sync completes.
repls = {
    r'(<p class="stat-value" id="totalEmployees">).*?(</p>)': r'\g<1>0\2',
    r'(<p class="stat-value" id="totalDays">).*?(</p>)': r'\g<1>0\2',
    r'(<p class="stat-value" id="daysRemaining">).*?(</p>)': r'\g<1>250\2',
    r'(<p class="stat-value" id="avgDays">).*?(</p>)': r'\g<1>0.0\2',
}
for pattern, replacement in repls.items():
    text, n = re.subn(pattern, replacement, text, count=1)
    if n != 1:
        raise SystemExit(f"Could not patch expected stat element: {pattern}")

index.write_text(text, encoding="utf-8")
print("frontend/index.html reset to 0 / 0 / 250 and linked to HAL/tracker v3.4 assets.")
