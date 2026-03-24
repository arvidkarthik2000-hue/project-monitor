#!/usr/bin/env python3
"""Full project resync — actual verification, no memory."""
import json, os, sys, io, glob, subprocess
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WS = Path(r"C:\Users\XGT-VR-ESCAPE ROOM\.openclaw\workspace")

# --- CINE SUPABASE ---
CINE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlubWFvYmppbGVvcHF5aGZxc2JvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDIzMTUwNiwiZXhwIjoyMDg5ODA3NTA2fQ.oTS7nn40ZdSMnq7cT33-lE7htIJMeK0Ora5Ly-BwKm4"
CINE_URL = "https://inmaobjileopqyhfqsbo.supabase.co/rest/v1"

def sb_count(url, key, table, filt=""):
    u = f"{url}/{table}?select=id{filt}"
    req = Request(u, headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "count=exact", "Range": "0-0"})
    resp = urlopen(req, timeout=15)
    return int(resp.headers.get("Content-Range", "*/0").split("/")[-1])

def sb_get(url, key, query):
    u = f"{url}/{query}"
    req = Request(u, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    return json.loads(urlopen(req, timeout=15).read())

print("=" * 70)
print("FULL PROJECT RESYNC — ACTUAL VERIFICATION")
print("=" * 70)

# ===================== CINE =====================
print("\n### CINE (CineVerse) ###")
try:
    movies = sb_count(CINE_URL, CINE_KEY, "movies")
    print(f"  Movies total: {movies}")
    
    movies_cast = sb_count(CINE_URL, CINE_KEY, "movies", "&cast=not.is.null")
    print(f"  Movies with cast: {movies_cast}")
    
    movies_imdb = sb_count(CINE_URL, CINE_KEY, "movies", "&imdb_id=not.is.null")
    print(f"  Movies with imdb_id: {movies_imdb}")
    
    q_total = sb_count(CINE_URL, CINE_KEY, "questions")
    print(f"  Questions total: {q_total}")
    
    q_active = sb_count(CINE_URL, CINE_KEY, "questions", "&is_active=eq.true")
    print(f"  Questions active: {q_active}")
    
    # v3 validated
    q_v3 = sb_count(CINE_URL, CINE_KEY, "questions", "&tags=cs.{v3_validated}")
    print(f"  Questions v3_validated: {q_v3}")
    
    # By category (v3)
    print("  Questions v3 by category:")
    cats = sb_get(CINE_URL, CINE_KEY, "questions?select=category&tags=cs.{v3_validated}")
    cat_counts = {}
    for row in cats:
        c = row.get("category", "Unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"    {c}: {n}")
    
    # By industry (v3)
    print("  Questions v3 by industry:")
    inds = sb_get(CINE_URL, CINE_KEY, "questions?select=industry&tags=cs.{v3_validated}")
    ind_counts = {}
    for row in inds:
        i = row.get("industry", "Unknown")
        ind_counts[i] = ind_counts.get(i, 0) + 1
    for i, n in sorted(ind_counts.items(), key=lambda x: -x[1]):
        print(f"    {i}: {n}")
    
    # By industry (all movies)
    print("  Movies by industry:")
    minds = sb_get(CINE_URL, CINE_KEY, "movies?select=industry")
    mind_counts = {}
    for row in minds:
        i = row.get("industry", "Unknown")
        mind_counts[i] = mind_counts.get(i, 0) + 1
    for i, n in sorted(mind_counts.items(), key=lambda x: -x[1]):
        print(f"    {i}: {n}")
    
    # Enrichment
    wiki = sb_count(CINE_URL, CINE_KEY, "movies", "&wiki_production=not.is.null")
    omdb = sb_count(CINE_URL, CINE_KEY, "movies", "&rotten_tomatoes=not.is.null")
    saavn = sb_count(CINE_URL, CINE_KEY, "movies", "&songs=not.is.null")
    print(f"  Enrichment — wiki: {wiki}, omdb: {omdb}, jiosaavn: {saavn}")
    
except Exception as e:
    print(f"  ERROR: {e}")

# Check workspace files
cine_ws = WS / "workspace-cineverse"
if cine_ws.exists():
    watchdog = cine_ws / "watchdog.py"
    print(f"  watchdog.py exists: {watchdog.exists()}")
    style_guide = cine_ws / "QUESTION_STYLE_GUIDE.md"
    if style_guide.exists():
        lines = len(style_guide.read_text(encoding='utf-8', errors='replace').splitlines())
        print(f"  QUESTION_STYLE_GUIDE.md: {lines} lines")
    else:
        print(f"  QUESTION_STYLE_GUIDE.md: DOES NOT EXIST")
else:
    print(f"  workspace-cineverse: DOES NOT EXIST at {cine_ws}")
    # Check alternate paths
    for alt in ["cineverse", "workspace-cine"]:
        p = WS / alt
        if p.exists():
            print(f"  Found alternate: {p}")

print()

# ===================== NEET-UG =====================
print("### NEET-UG ###")
# Check deployment
try:
    req = Request("https://neetai.in", headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=10)
    print(f"  neetai.in: HTTP {resp.status}")
except Exception as e:
    print(f"  neetai.in: FAILED - {e}")

# Questions file
for qpath in [
    WS / "neetai-webapp" / "public" / "questions.json",
    WS / "neet-ai" / "public" / "questions.json",
    WS / "workspace-neet-ug" / "public" / "questions.json",
]:
    if qpath.exists():
        try:
            qs = json.loads(qpath.read_text(encoding='utf-8'))
            print(f"  {qpath.relative_to(WS)}: {len(qs)} questions")
            # Count by subject
            subjs = {}
            for q in qs:
                s = q.get("subject", "Unknown")
                subjs[s] = subjs.get(s, 0) + 1
            for s, n in sorted(subjs.items(), key=lambda x: -x[1]):
                print(f"    {s}: {n}")
            # Count by year
            years = {}
            for q in qs:
                y = q.get("year", "Unknown")
                years[str(y)] = years.get(str(y), 0) + 1
            print(f"  Years present: {sorted(years.keys())}")
            gap_years = [y for y in ["2010", "2011", "2019", "2021"] if y not in years]
            if gap_years:
                print(f"  YEAR GAPS STILL MISSING: {gap_years}")
            else:
                print(f"  Year gaps (2010,2011,2019,2021): ALL FILLED")
        except Exception as e:
            print(f"  Error reading {qpath}: {e}")

# Check auth code for bcrypt
print("  Auth check (bcrypt vs custom hash):")
for root_dir in ["neetai-webapp", "neet-ai", "workspace-neet-ug"]:
    d = WS / root_dir
    if d.exists():
        for f in d.rglob("*auth*"):
            if f.is_file() and f.suffix in ['.js', '.ts', '.jsx', '.tsx', '.py']:
                content = f.read_text(encoding='utf-8', errors='replace')
                if 'bcrypt' in content.lower():
                    print(f"    {f.relative_to(WS)}: USES bcrypt")
                elif 'hash' in content.lower() or 'crypto' in content.lower():
                    print(f"    {f.relative_to(WS)}: uses custom hash/crypto")

# Per-option explanations
print("  Per-option explanation files:")
for d in ["neetai-webapp", "neet-ai", "workspace-neet-ug"]:
    base = WS / d
    if base.exists():
        for pat in ["*explanation*", "*per_option*", "*option_explain*"]:
            found = list(base.rglob(pat))
            if found:
                for f in found[:5]:
                    print(f"    {f.relative_to(WS)}")

# Quarantined chemistry
print("  Quarantined chemistry PYQs:")
for d in ["neetai-webapp", "neet-ai", "workspace-neet-ug"]:
    base = WS / d
    if base.exists():
        for pat in ["*quarantin*", "*reconstruct*"]:
            found = list(base.rglob(pat))
            if found:
                for f in found[:5]:
                    print(f"    {f.relative_to(WS)}")

print()

# ===================== NEET-PG =====================
print("### NEET-PG ###")
pg_ws = WS / "neet-pg-pyq"

# Try Supabase
NEETPG_KEY = os.environ.get("NEETPG_SUPABASE_KEY", "")
neetpg_env = WS / "neet-pg-pyq" / ".env"
if neetpg_env.exists():
    for line in neetpg_env.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith("SUPABASE_SERVICE_KEY=") or line.startswith("SUPABASE_KEY="):
            NEETPG_KEY = line.split("=", 1)[1].strip().strip('"')
            break

if NEETPG_KEY:
    NEETPG_URL = "https://tgtxfbfuzpkqofxnrtie.supabase.co/rest/v1"
    try:
        total = sb_count(NEETPG_URL, NEETPG_KEY, "questions")
        print(f"  Questions total (Supabase): {total}")
    except Exception as e:
        print(f"  Supabase query failed: {e}")
else:
    print(f"  No Supabase key found in .env")

# Check via _check_status.js
if (pg_ws / "_check_status.js").exists():
    print("  Running _check_status.js...")
    # Will be run separately

# Engine stats
stats_file = pg_ws / "engine_v2_stats.json"
if stats_file.exists():
    stats = json.loads(stats_file.read_text(encoding='utf-8'))
    print(f"  engine_v2_stats.json: {json.dumps(stats, indent=2)[:500]}")
else:
    print(f"  engine_v2_stats.json: DOES NOT EXIST")

# Scraped files
scraped = pg_ws / "scraped"
if scraped.exists():
    jsons = list(scraped.glob("*.json"))
    print(f"  Scraped JSON files: {len(jsons)}")
else:
    print(f"  scraped/ directory: DOES NOT EXIST")

# Textbook chunks
print("  Textbook chunks (pgvector): CANNOT VERIFY — no Supabase key for textbook_chunks table")

# Skills
print("  V2 engine skills/features:")
for fname in ["continuous_engine_v2.js", "generate_questions.js", "knowledge_pipeline.js", "rag_tutor.js", "validate_questions.js", "cross_validate.js"]:
    f = pg_ws / fname
    print(f"    {fname}: {'EXISTS' if f.exists() else 'MISSING'}")

print()

# ===================== CHOTU =====================
print("### CHOTU ###")
# Check deployment
try:
    req = Request("https://chotu-ai.in", headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=10)
    print(f"  chotu-ai.in: HTTP {resp.status}")
except Exception as e:
    print(f"  chotu-ai.in: FAILED - {e}")

# Find all chotu directories
chotu_dirs = []
for d in WS.iterdir():
    if d.is_dir() and 'chotu' in d.name.lower():
        chotu_dirs.append(d.name)
print(f"  Chotu directories: {chotu_dirs}")

# Auth check
for d in chotu_dirs:
    base = WS / d
    for f in base.rglob("*"):
        if f.is_file() and f.suffix in ['.js', '.ts', '.jsx', '.tsx'] and f.stat().st_size < 100000:
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                if 'bcrypt' in content.lower():
                    print(f"    {f.relative_to(WS)}: USES bcrypt")
                    break
            except:
                pass

# GupShup
print("  GupShup API key search:")
for d in chotu_dirs:
    base = WS / d
    for pat in [".env", ".env.local", ".env.production"]:
        f = base / pat
        if f.exists():
            content = f.read_text(encoding='utf-8', errors='replace')
            if 'gupshup' in content.lower() or 'GUPSHUP' in content:
                print(f"    Found in {f.relative_to(WS)}")
            else:
                print(f"    {f.relative_to(WS)}: no gupshup key")

# Parent dashboard check
print("  Parent dashboard code check:")
for d in chotu_dirs:
    base = WS / d
    for f in base.rglob("*dashboard*"):
        if f.is_file() and f.suffix in ['.tsx', '.jsx', '.ts', '.js']:
            content = f.read_text(encoding='utf-8', errors='replace')
            if 'mock' in content.lower() or 'hardcoded' in content.lower() or '= [' in content:
                print(f"    {f.relative_to(WS)}: LIKELY MOCK DATA")
            elif 'supabase' in content.lower() or 'fetch' in content.lower():
                print(f"    {f.relative_to(WS)}: uses Supabase/fetch")

# Games
print("  AI Games check:")
for d in chotu_dirs:
    base = WS / d
    for f in base.rglob("*game*"):
        if f.is_file() and f.suffix in ['.tsx', '.jsx', '.ts', '.js']:
            print(f"    {f.relative_to(WS)} ({f.stat().st_size} bytes)")

print()

# ===================== QCLAW =====================
print("### QCLAW (Voltzz) ###")
# Find directories
qclaw_dirs = []
for name in ["trading-agent", "workspace-voltzz", "voltzz"]:
    d = WS / name
    if d.exists():
        qclaw_dirs.append(d)
        print(f"  Directory: {d.name}")

# Kite credentials
print("  Kite Connect credentials search:")
for d in qclaw_dirs:
    for f in d.rglob("*"):
        if f.is_file() and f.name in [".env", ".env.local", "config.json", "config.yaml", "config.yml", "settings.json"]:
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                if 'kite' in content.lower():
                    # Check if populated or placeholder
                    lines = [l for l in content.splitlines() if 'kite' in l.lower()]
                    for l in lines:
                        if 'xxx' in l or 'placeholder' in l.lower() or '=""' in l or "=''" in l or l.strip().endswith('='):
                            print(f"    {f.relative_to(WS)}: PLACEHOLDER")
                        else:
                            print(f"    {f.relative_to(WS)}: POPULATED")
            except:
                pass

# Stock scan results
print("  Stock feasibility scan results:")
for d in qclaw_dirs:
    for pat in ["*scan*", "*ranking*", "*feasibility*", "*trend*"]:
        for f in d.rglob(pat):
            if f.is_file():
                print(f"    {f.relative_to(WS)} ({f.stat().st_size} bytes)")

# Skills
print("  Skills directories:")
for d in qclaw_dirs:
    skills_dir = d / "skills"
    if skills_dir.exists():
        for s in skills_dir.iterdir():
            if s.is_dir():
                skill_md = s / "SKILL.md"
                print(f"    {s.name}: {'HAS SKILL.md' if skill_md.exists() else 'NO SKILL.md'}")

# Paper trading
print("  Paper trading check:")
for d in qclaw_dirs:
    for pat in ["*paper*", "*backtest*", "*simulate*"]:
        for f in d.rglob(pat):
            if f.is_file():
                print(f"    {f.relative_to(WS)} ({f.stat().st_size} bytes)")

print()

# ===================== STYLE =====================
print("### STYLE (StyleGenie) ###")
# Check deployment
try:
    req = Request("https://stylegenie.in", headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=10)
    print(f"  stylegenie.in: HTTP {resp.status}")
except Exception as e:
    print(f"  stylegenie.in: FAILED - {e}")

# Find directories
style_dirs = []
for d in WS.iterdir():
    if d.is_dir() and 'style' in d.name.lower():
        style_dirs.append(d)
        print(f"  Directory: {d.name}")

# Agent files (VANI, DRISHTI, KAVI, MAYA, RASA, UTSAV, SATHI)
agents = ["vani", "drishti", "kavi", "maya", "rasa", "utsav", "sathi"]
print("  Agent status:")
for d in style_dirs:
    for agent in agents:
        found = list(d.rglob(f"*{agent}*"))
        if found:
            print(f"    {agent.upper()}: {len(found)} files in {d.name}")

# Weather API
print("  Weather API (OpenWeatherMap):")
for d in style_dirs:
    for f in d.rglob("*"):
        if f.is_file() and f.suffix in ['.js', '.ts', '.py', '.env'] and f.stat().st_size < 50000:
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                if 'openweather' in content.lower() or 'weather' in content.lower():
                    print(f"    {f.relative_to(WS)}")
            except:
                pass

# GupShup
print("  GupShup API key:")
for d in style_dirs:
    for fname in [".env", ".env.local"]:
        f = d / fname
        if f.exists():
            content = f.read_text(encoding='utf-8', errors='replace')
            if 'gupshup' in content.lower():
                print(f"    Found in {f.relative_to(WS)}")

print()

# ===================== UPSC =====================
print("### UPSC (Sentinel) ###")
upsc_ws = WS / "upsc-sentinel"
if upsc_ws.exists():
    # Daily files
    daily_dir = upsc_ws / "outputs" / "daily"
    if daily_dir.exists():
        day_files = sorted(daily_dir.glob("day_*[!_answers].txt"))
        answer_files = sorted(daily_dir.glob("*_answers.txt"))
        print(f"  Daily question files: {len(day_files)}")
        print(f"  Daily answer files: {len(answer_files)}")
        
        # Check day_01.txt
        day1 = daily_dir / "day_01.txt"
        if day1.exists():
            content = day1.read_text(encoding='utf-8', errors='replace')
            lines = content.splitlines()
            print(f"  day_01.txt: {len(lines)} lines, {len(content)} chars")
            print(f"  day_01.txt first 10 lines:")
            for l in lines[:10]:
                print(f"    {l}")
        else:
            print(f"  day_01.txt: DOES NOT EXIST — CRITICAL for Mar 25 launch!")
    else:
        print(f"  outputs/daily/: DOES NOT EXIST")
    
    # Schedule
    sched = upsc_ws / "outputs" / "daily_schedule.json"
    if sched.exists():
        sdata = json.loads(sched.read_text(encoding='utf-8'))
        print(f"  daily_schedule.json: {len(sdata)} entries")
    else:
        print(f"  daily_schedule.json: DOES NOT EXIST")
    
    # Question files
    data_dir = upsc_ws / "data"
    if data_dir.exists():
        for fname in ["predicted_questions_v1.json", "predicted_questions_v2.json", "predicted_questions_top10.json"]:
            f = data_dir / fname
            if f.exists():
                try:
                    d = json.loads(f.read_text(encoding='utf-8'))
                    if isinstance(d, dict) and "questions" in d:
                        d = d["questions"]
                    print(f"  {fname}: {len(d)} questions")
                except:
                    print(f"  {fname}: EXISTS but failed to parse")
            else:
                print(f"  {fname}: DOES NOT EXIST")
    
    # PIB scraper
    print("  PIB scraper cron: CHECKING...")
    # Can't check crontab on Windows — check for scheduled tasks or script
    pib_files = list(upsc_ws.rglob("*pib*"))
    print(f"  PIB-related files: {[f.name for f in pib_files]}")
    
    # WhatsApp group
    print("  WhatsApp beta group: CANNOT VERIFY from here")
else:
    print(f"  upsc-sentinel: DOES NOT EXIST at {upsc_ws}")

print()

# ===================== PHOTO =====================
print("### PHOTO (PVR Scene Stealer) ###")
pvr = Path(r"C:\pvr")
if pvr.exists():
    server = pvr / "core" / "server.py"
    model = pvr / "models" / "inswapper_128.onnx"
    overlay = list(pvr.rglob("*overlay*"))
    branding = list(pvr.rglob("*brand*"))
    
    print(f"  server.py: {'EXISTS' if server.exists() else 'MISSING'}")
    print(f"  inswapper_128.onnx: {'EXISTS' if model.exists() else 'MISSING'} ({model.stat().st_size // 1024 // 1024}MB)" if model.exists() else "  inswapper_128.onnx: MISSING")
    print(f"  Overlay files: {[f.name for f in overlay]}")
    print(f"  Branding files: {[f.name for f in branding]}")
    
    # Test images
    test_imgs = list(pvr.rglob("*test*"))
    print(f"  Test files: {[f.name for f in test_imgs if f.is_file()][:10]}")
    
    # Check if face swap was actually tested with a real image
    output_dir = pvr / "output"
    outputs = list(output_dir.glob("*")) if output_dir.exists() else []
    print(f"  Output directory files (actual swap results): {[f.name for f in outputs][:10]}")
else:
    print(f"  C:\\pvr: DOES NOT EXIST")

print()

# ===================== LAST MODIFIED DATES =====================
print("### LAST MODIFIED DATES PER PROJECT ###")
project_dirs = {
    "CINE": [WS / "workspace-cineverse"],
    "NEET-UG": [WS / "neetai-webapp", WS / "neet-ai", WS / "workspace-neet-ug"],
    "NEET-PG": [WS / "neet-pg-pyq"],
    "CHOTU": [WS / d for d in os.listdir(WS) if 'chotu' in d.lower() and (WS / d).is_dir()],
    "QCLAW": [WS / "trading-agent", WS / "workspace-voltzz"],
    "STYLE": [WS / d for d in os.listdir(WS) if 'style' in d.lower() and (WS / d).is_dir()],
    "UPSC": [WS / "upsc-sentinel"],
    "PHOTO": [Path(r"C:\pvr")],
}

for code, dirs in project_dirs.items():
    latest = None
    latest_file = None
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.is_file():
                try:
                    mt = f.stat().st_mtime
                    if latest is None or mt > latest:
                        latest = mt
                        latest_file = f
                except:
                    pass
    if latest:
        dt = datetime.fromtimestamp(latest)
        print(f"  {code}: {dt.strftime('%Y-%m-%d %H:%M')} — {latest_file.name}")
    else:
        print(f"  {code}: NO FILES FOUND")

print("\n### DONE ###")
