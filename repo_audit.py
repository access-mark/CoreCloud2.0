#!/usr/bin/env python3
import os, re, json, sys
from collections import defaultdict

ROOT = os.getcwd()
IMG_DIR = os.path.join(ROOT, "assets", "images")
CSS_PATH = os.path.join(ROOT, "assets", "css", "styles.css")

# --- Config you can tweak ---
REQUIRED_NAV_ITEMS = [
    ("Consulting", ["consulting.html","dynamic-imprinting.html"]),
    ("Cloud Suite", ["cloud.html","finops.html","application-development.html","data-ai.html","hosted-private-cloud.html"]),
    ("Curated Talent", ["talent.html","talent-relaunch.html","global-talent.html"]),
    ("Security", ["cloud-security.html","hosting-security.html"]),
]
EXPECTED_CSS_QUERY = r"assets/css/styles\.css\?v=15"
SECURITY_PAGES = {"cloud-security.html","hosting-security.html"}
SECURITY_BANNER = "assets/images/security-bannerimage.png"
RECOMMENDED_PRELOADS = [
    "assets/images/corecloud-logo.png",
    SECURITY_BANNER,
]

html_files = [p for p in os.listdir(ROOT) if p.endswith(".html")]
issues = defaultdict(list)

def add_issue(file, msg):
    issues[file].append(msg)

def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return f.read()
    except Exception as e:
        return ""

def exists_rel(rel):
    return os.path.exists(os.path.join(ROOT, rel.replace("/", os.sep)))

# --- Collect CSS class names defined ---
css = read(CSS_PATH)
defined_classes = set(re.findall(r"\.([A-Za-z0-9_-]+)\s*[{:,\.#\s>]", css)) if css else set()

# Simple selector list (classes only)
# Remove pseudo/compound leftovers
defined_classes = {c for c in defined_classes if not any(x in c for x in (":","(",")"))}

# Scan each HTML file
all_used_classes = set()
all_ids = []
id_seen = defaultdict(list)

for hf in html_files:
    src = read(os.path.join(ROOT, hf))
    if not src:
        add_issue(hf, "File unreadable or empty.")
        continue

    # 1) CSS link version
    css_links = re.findall(r'<link[^>]+href="([^"]+styles\.css[^"]*)"', src, re.I)
    if not css_links:
        add_issue(hf, "Missing stylesheet link to assets/css/styles.css.")
    else:
        if not any(re.search(EXPECTED_CSS_QUERY, href) for href in css_links):
            add_issue(hf, f"Stylesheet version mismatch. Expected '?v=15' → found: {css_links}")

    # 2) Header/nav presence (desktop + mobile)
    if 'class="site-header"' not in src or 'class="main-nav"' not in src:
        add_issue(hf, "Header/Main nav missing or altered.")
    if 'class="mobile-drawer"' not in src or 'id="nav-toggle"' not in src:
        add_issue(hf, "Mobile drawer missing or toggle checkbox not present.")

    # 3) Security menu present with both links
    if "Security</button>" in src:
        for link in ("cloud-security.html","hosting-security.html"):
            if link not in src:
                add_issue(hf, f"Security submenu missing link: {link}")
    # 4) Hero frame + centered intro/classes
    if 'class="hero-frame"' not in src or 'class="hero-media"' not in src:
        add_issue(hf, "Hero frame/media structure missing.")
    if 'class="hero-intro"' not in src or 'class="hero-title"' not in src:
        add_issue(hf, "Centered hero intro/title missing.")

    # 5) Banner image path exists
    hero_imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', src, re.I)
    hero_imgs = [u for u in hero_imgs if "banner" in u or "security" in u or "footer-bannerimage1" in u]
    for u in hero_imgs:
        rel = u.split("?")[0]
        if rel.startswith(("http://","https://","//")):
            continue
        if not exists_rel(rel):
            add_issue(hf, f"Hero/banner image not found on disk: {u}")

    # 6) Preload recommended assets
    for preload in RECOMMENDED_PRELOADS:
        if preload in SECURITY_BANNER and hf not in SECURITY_PAGES:
            continue
        if preload not in src:
            add_issue(hf, f"Recommended <link rel='preload'> missing: {preload}")

    # 7) Active-link highlighter script present
    if "aria-current" not in src or "document.querySelectorAll('.main-nav" not in src:
        add_issue(hf, "Active-link script missing (desktop/mobile underline).")

    # 8) Right rail TOC on security pages
    if hf in SECURITY_PAGES:
        if 'class="layout-rail"' not in src or 'class="toc"' not in src:
            add_issue(hf, "Right rail TOC layout missing on security page.")

    # 9) Body class policy (security pages use .security-page)
    if hf in SECURITY_PAGES and 'class="security-page' not in src and "class='security-page" not in src:
        add_issue(hf, "Body missing 'security-page' class.")

    # 10) Collect classes used
    used_classes = re.findall(r'class\s*=\s*"([^"]+)"', src)
    for block in used_classes:
        for c in re.split(r"\s+", block.strip()):
            if c: all_used_classes.add(c)

    # 11) Duplicate IDs
    ids = re.findall(r'id\s*=\s*"([^"]+)"', src)
    for i in ids:
        id_seen[i].append(hf)
    all_ids.extend([(hf, i) for i in ids])

# 12) Class comparison: used-but-undefined, defined-but-unused
used_but_undefined = sorted([c for c in all_used_classes if c not in defined_classes and not c.startswith(("fa-","icon-"))])
defined_but_unused = sorted([c for c in defined_classes if c not in all_used_classes])

# 13) Duplicate IDs across files
dupe_ids = {i: files for i, files in id_seen.items() if len(files) > 1}

# 14) Broken local <img> across all pages (general)
missing_assets = []
img_refs = set()
for hf in html_files:
    src = read(os.path.join(ROOT, hf))
    for u in re.findall(r'<img[^>]+src="([^"]+)"', src, re.I):
        rel = u.split("?")[0]
        if rel.startswith(("http://","https://","//")): continue
        img_refs.add((hf, rel))
for hf, rel in img_refs:
    if not exists_rel(rel):
        missing_assets.append((hf, rel))

# ---- Report ----
print("\n=== CoreCloud Repo Consistency Audit ===\n")

for hf in sorted(html_files):
    if issues[hf]:
        print(f"[{hf}]")
        for msg in issues[hf]:
            print(f"  - {msg}")
        print("")

print("— Classes used but NOT defined in CSS —")
if used_but_undefined:
    for c in used_but_undefined: print("  ", c)
else:
    print("  None")

print("\n— Classes defined in CSS but NOT used anywhere — (top 60)")
for c in defined_but_unused[:60]:
    print("  ", c)
if len(defined_but_unused) > 60:
    print(f"  ... +{len(defined_but_unused)-60} more")

print("\n— Duplicate IDs across files —")
if dupe_ids:
    for i, files in dupe_ids.items():
        print(f"  #{i} → {files}")
else:
    print("  None")

print("\n— Missing image assets referenced by HTML —")
if missing_assets:
    for hf, rel in missing_assets:
        print(f"  {hf}: {rel}")
else:
    print("  None")

# Exit code for CI
err_count = sum(len(v) for v in issues.values()) + len(missing_assets)
sys.exit(1 if err_count else 0)
