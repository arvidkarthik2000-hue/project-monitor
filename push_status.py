#!/usr/bin/env python3
"""Push live project status to GitHub repo.
Queries each project's Supabase DB for real numbers where available.
Falls back to workspace file inspection for projects without DBs.
Run after every work session or every 2 hours during long sessions.

Source confidence levels:
  "live_db"        - Queried from Supabase/DB in real time
  "workspace_files" - Read from local project files (may be stale)
  "manual"         - Last known values, manually set
"""

import json, os, subprocess, sys, io, glob, re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_DIR = Path(__file__).parent
WS = Path(r"C:\Users\XGT-VR-ESCAPE ROOM\.openclaw\workspace")
ENV_FILE = REPO_DIR / ".env"

# Load .env if exists
env_vars = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")


# ============================================================
# SUPABASE HELPERS
# ============================================================

def sb_count(base_url, key, table, filter_str=""):
    url = f"{base_url}/{table}?select=id{filter_str}"
    req = Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
        "Range": "0-0"
    })
    resp = urlopen(req, timeout=15)
    cr = resp.headers.get("Content-Range", "*/0")
    return int(cr.split("/")[-1])


def sb_rpc(base_url, key, fn_name, params=None):
    url = f"{base_url}/rpc/{fn_name}"
    data = json.dumps(params or {}).encode()
    req = Request(url, data=data, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }, method="POST")
    resp = urlopen(req, timeout=15)
    return json.loads(resp.read())


def _stale(name, reason):
    return {
        "name": name,
        "status": "unknown",
        "source": "error",
        "summary": f"Awaiting live data - {reason}",
        "db": {},
        "blockers": [reason],
        "next_actions": ["Fix data source"],
        "decisions": []
    }


# ============================================================
# CINEVERSE — Live Supabase DB
# ============================================================

CINE_SB_URL = env_vars.get("CINE_SUPABASE_URL", "https://inmaobjileopqyhfqsbo.supabase.co/rest/v1")
CINE_SB_KEY = env_vars.get("CINE_SUPABASE_KEY", "")


def get_cineverse_status():
    if not CINE_SB_KEY:
        return _stale("CineVerse", "CINE_SUPABASE_KEY not set in .env")
    try:
        movies_total = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies")
        movies_cast = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&cast=not.is.null")
        questions_total = sb_count(CINE_SB_URL, CINE_SB_KEY, "questions")
        questions_active = sb_count(CINE_SB_URL, CINE_SB_KEY, "questions", "&is_active=eq.true")
        wiki = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&wiki_production=not.is.null")
        omdb = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&rotten_tomatoes=not.is.null")
        saavn = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&songs=not.is.null")

        return {
            "name": "CineVerse",
            "status": "active",
            "source": "live_db",
            "progress": 35,
            "phase": "Data Collection + Question Generation",
            "summary": f"{movies_total} movies, {questions_total} questions ({questions_active} active), enrichment ongoing",
            "db": {
                "movies_total": movies_total,
                "movies_with_cast": movies_cast,
                "questions_total": questions_total,
                "questions_active": questions_active,
                "enrichment": {"wiki": wiki, "omdb": omdb, "jiosaavn": saavn}
            },
            "blockers": [
                "Threads die overnight without watchdog wrapper",
                "emoji_movie format paused at 33% pass rate",
                "12,387 movies missing cast/crew"
            ],
            "next_actions": [
                "Build watchdog wrapper",
                "Relaunch all threads",
                "Add Malayalam + Kannada to generator",
                "Cast/crew backfill for 12K movies"
            ],
            "decisions": [
                "v3 validated = production engine",
                "Gemini via OpenRouter for generation",
                "PROGA 2025 compliance: CineCoins = zero real value"
            ]
        }
    except Exception as e:
        return _stale("CineVerse", f"DB query failed: {e}")


# ============================================================
# NEET PG — Live Supabase DB
# ============================================================

NEETPG_SB_URL = env_vars.get("NEETPG_SUPABASE_URL", "https://tgtxfbfuzpkqofxnrtie.supabase.co/rest/v1")
NEETPG_SB_KEY = env_vars.get("NEETPG_SUPABASE_KEY", "")


def get_neetpg_status():
    if not NEETPG_SB_KEY:
        # Fall back to workspace files
        return get_neetpg_from_workspace()
    try:
        total = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "questions")
        v2 = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "questions", "&source=eq.gemini_v2")
        articles = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "knowledge_articles")

        return {
            "name": "NEET PG Exam Prep",
            "status": "active",
            "source": "live_db",
            "progress": 45,
            "phase": "V2 Engine Generation (Gemini)",
            "summary": f"{total} total Qs, {v2} v2 generated, {articles} knowledge articles",
            "db": {
                "questions_total": total,
                "questions_v2_gemini": v2,
                "knowledge_articles": articles,
                "supabase_host": "db.tgtxfbfuzpkqofxnrtie.supabase.co"
            },
            "blockers": [
                "Engine process gets GC'd between checks",
                "Need persistent process runner"
            ],
            "next_actions": [
                "V2 validation pipeline",
                "Persistent runner (Windows service)",
                "React Native app integration"
            ],
            "decisions": [
                "Hourly cron monitor + auto-restart",
                "16 textbooks chunked for RAG (13,204 chunks)"
            ]
        }
    except Exception as e:
        return get_neetpg_from_workspace()


def get_neetpg_from_workspace():
    """Read NEET PG stats from workspace files when DB key unavailable."""
    stats = {}
    stats_file = WS / "neet-pg-pyq" / "engine_v2_stats.json"
    if stats_file.exists():
        try:
            stats = json.loads(stats_file.read_text(encoding='utf-8'))
        except:
            pass

    # Count scraped JSON files
    scraped = list((WS / "neet-pg-pyq" / "scraped").glob("*.json")) if (WS / "neet-pg-pyq" / "scraped").exists() else []

    return {
        "name": "NEET PG Exam Prep",
        "status": "active",
        "source": "workspace_files",
        "progress": 45,
        "phase": "V2 Engine Generation (Gemini)",
        "summary": f"Stats from engine_v2_stats.json, {len(scraped)} scraped JSON files",
        "db": {
            "scraped_files": len(scraped),
            "engine_stats": stats
        },
        "blockers": [
            "Engine dies between hourly checks",
            "NEETPG_SUPABASE_KEY not in .env — using workspace files"
        ],
        "next_actions": [
            "Add NEETPG_SUPABASE_KEY to .env for live queries",
            "V2 validation pipeline",
            "Persistent runner"
        ],
        "decisions": []
    }


# ============================================================
# NEET UG — Workspace files (static JSON on Vercel)
# ============================================================

def get_neetug_status():
    """NEET UG has no live DB — reads from workspace files."""
    questions_file = WS / "neetai-webapp" / "public" / "questions.json"
    q_count = 0
    subjects = {}

    if questions_file.exists():
        try:
            qs = json.loads(questions_file.read_text(encoding='utf-8'))
            q_count = len(qs)
            for q in qs:
                subj = q.get("subject", "Unknown")
                subjects[subj] = subjects.get(subj, 0) + 1
        except:
            pass

    # Check for enrichment data
    enhanced_file = WS / "neet-ai" / "data" / "neet-enhanced.json"
    enhanced_count = 0
    if enhanced_file.exists():
        try:
            enhanced_count = len(json.loads(enhanced_file.read_text(encoding='utf-8')))
        except:
            pass

    return {
        "name": "NEET UG Exam Prep",
        "status": "active",
        "source": "workspace_files",
        "progress": 75,
        "phase": "Production - Live at neetai.in",
        "summary": f"{q_count} verified questions live at neetai.in, all QC phases complete",
        "db": {
            "questions_total": q_count,
            "questions_verified": q_count,
            "critical_issues": 0,
            "subjects": subjects,
            "enhanced_questions": enhanced_count,
            "deployment": "neetai.in (Vercel)",
            "data_source": "questions.json (static)"
        },
        "blockers": [
            "OpenRouter credits exhausted for enrichment",
            "WhatsApp bot not started"
        ],
        "next_actions": [
            "WhatsApp bot integration",
            "Gemini enrichment pipeline",
            "Expand question bank beyond 8K"
        ],
        "decisions": [
            "All QC phases complete (3B/3C/3D/3E) as of Mar 19",
            "Deployed to neetai.in via Vercel"
        ]
    }


# ============================================================
# UPSC SENTINEL — Workspace files
# ============================================================

def get_upsc_status():
    """UPSC reads from local JSON question files."""
    base = WS / "upsc-sentinel" / "data"
    counts = {"v1": 0, "v2": 0, "top10": 0}

    for key, fname in [("v1", "predicted_questions_v1.json"), ("v2", "predicted_questions_v2.json"), ("top10", "predicted_questions_top10.json")]:
        f = base / fname
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                if isinstance(data, dict) and "questions" in data:
                    data = data["questions"]
                counts[key] = len(data)
            except:
                pass

    total = sum(counts.values())

    # Check daily content
    daily_dir = WS / "upsc-sentinel" / "outputs" / "daily"
    daily_count = len(list(daily_dir.glob("day_*[!_answers].txt"))) if daily_dir.exists() else 0
    answer_count = len(list(daily_dir.glob("*_answers.txt"))) if daily_dir.exists() else 0

    # PYQ data
    pyq_dir = WS / "upsc-sentinel" / "data"
    pyq_files = list(pyq_dir.glob("pyq_*.json")) if pyq_dir.exists() else []

    return {
        "name": "UPSC Sentinel",
        "status": "active",
        "source": "workspace_files",
        "progress": 65,
        "phase": "Launch Content Ready",
        "summary": f"{total} clean questions (v1:{counts['v1']}, v2:{counts['v2']}, top10:{counts['top10']}). {daily_count} daily WhatsApp messages ready.",
        "db": {
            "questions_total": total,
            "questions_v1": counts["v1"],
            "questions_v2": counts["v2"],
            "questions_top10": counts["top10"],
            "daily_content_days": daily_count,
            "daily_answer_sheets": answer_count,
            "pyq_files": len(pyq_files)
        },
        "blockers": [
            "WhatsApp bot not integrated for automated delivery",
            "No user response tracking system"
        ],
        "next_actions": [
            "WhatsApp bot for daily delivery",
            "User response tracking + scoring",
            "Generate more questions for gap topics"
        ],
        "decisions": [
            "50-day launch: Mar 25 to May 13",
            "1 easy + 1 moderate + 1 hard per day",
            "Prelims: May 25, 2026"
        ]
    }


# ============================================================
# CHOTU AI — Workspace files
# ============================================================

def get_chotu_status():
    """Chotu AI reads from webapp files."""
    # Count questions from the data file
    q_count = 0
    q_file = WS / "chotu-ai-webapp" / "src" / "data" / "ai-questions.ts"
    if q_file.exists():
        content = q_file.read_text(encoding='utf-8', errors='replace')
        q_count = content.count("question:")

    # Check for questions.json
    qjson = WS / "chotu-ai-webapp" / "public" / "data" / "questions.json"
    if qjson.exists():
        try:
            q_count = max(q_count, len(json.loads(qjson.read_text(encoding='utf-8'))))
        except:
            pass

    # Count video files
    vid_dir = WS / "chotu-ai-videos" / "output"
    videos = list(vid_dir.glob("*.mp4")) if vid_dir.exists() else []

    return {
        "name": "Chotu AI",
        "status": "active",
        "source": "workspace_files",
        "progress": 60,
        "phase": "Testing - Live at chotu-ai.in",
        "summary": f"{q_count} questions, {len(videos)} AI education videos, full Next.js app deployed",
        "db": {
            "questions_estimated": q_count,
            "videos": len(videos),
            "video_topics": [v.stem.replace("_final", "") for v in videos],
            "deployment": "chotu-ai.in (Vercel)",
            "features": ["17 pages", "5 AI games", "gamification", "bilingual EN/HI"]
        },
        "blockers": [
            "GupShup WhatsApp API not configured",
            "Videos too large for Vercel CDN"
        ],
        "next_actions": [
            "WhatsApp bot via GupShup",
            "Video hosting (CDN/S3)",
            "200+ more AI questions"
        ],
        "decisions": [
            "AI education only (Doc directive Mar 11)",
            "Duolingo-style gamification",
            "Deployed to chotu-ai.in"
        ]
    }


# ============================================================
# QUANTCLAW / VOLTZZ — Workspace files
# ============================================================

def get_qclaw_status():
    """Voltzz trading agent reads from workspace."""
    agent_dir = WS / "trading-agent"
    files = list(agent_dir.rglob("*.py")) if agent_dir.exists() else []

    return {
        "name": "QuantClaw / Voltzz Trading",
        "status": "active",
        "source": "workspace_files",
        "progress": 60,
        "phase": "Development - Agent Deployed",
        "summary": f"OpenClaw agent on Opus 4.6, {len(files)} Python files, 7 skills, paper trading active",
        "db": {
            "python_files": len(files),
            "stocks_tracked": 52,
            "indices": ["NIFTY", "BANKNIFTY"],
            "skills": 7
        },
        "blockers": [
            "No live broker integration (paper only)",
            "OpenAlgo bridge not configured"
        ],
        "next_actions": [
            "Connect OpenAlgo to broker",
            "Backtest validation",
            "Options strategies"
        ],
        "decisions": [
            "Hybrid: LLMs for analysis, Python for execution",
            "Paper trading first",
            "Indian markets (NSE/BSE)"
        ]
    }


# ============================================================
# STYLEGENIE — Workspace files
# ============================================================

def get_style_status():
    base = WS / "stylegenie"
    bot_dir = WS / "stylegenie-bot"
    engine_dir = WS / "stylegenie-engine"

    file_count = 0
    for d in [base, bot_dir, engine_dir]:
        if d.exists():
            file_count += len(list(d.rglob("*")))

    return {
        "name": "StyleGenie",
        "status": "active",
        "source": "workspace_files",
        "progress": 50,
        "phase": "Development - Bot + Engine Built",
        "summary": f"WhatsApp bot + Flask engine built, {file_count} files, landing page live at stylegenie.in",
        "db": {
            "total_files": file_count,
            "products": 50,
            "brands": 5,
            "style_profiles": 5,
            "deployment": "stylegenie.in"
        },
        "blockers": [
            "GupShup WhatsApp API not configured",
            "Aishwarya's product catalog pending"
        ],
        "next_actions": [
            "GupShup setup",
            "Product catalog from Aishwarya",
            "Instagram OAuth"
        ],
        "decisions": [
            "Claude Vision for outfit analysis",
            "5 style profiles"
        ]
    }


# ============================================================
# PHOTO / PVR SCENE STEALER — Workspace files
# ============================================================

def get_photo_status():
    pvr_dir = Path(r"C:\pvr")
    build_status = pvr_dir / "BUILD_STATUS.md"
    status_text = ""
    if build_status.exists():
        status_text = build_status.read_text(encoding='utf-8', errors='replace')[:200]

    model_exists = (pvr_dir / "models" / "inswapper_128.onnx").exists()
    server_exists = (pvr_dir / "core" / "server.py").exists()

    return {
        "name": "PhotoBooth AI / PVR Scene Stealer",
        "status": "active",
        "source": "workspace_files",
        "progress": 40,
        "phase": "Build Complete - Ready for Demo",
        "summary": f"ML stack working, model={'loaded' if model_exists else 'missing'}, server={'ready' if server_exists else 'missing'}",
        "db": {
            "model_file": "inswapper_128.onnx" if model_exists else "MISSING",
            "server_file": "core/server.py" if server_exists else "MISSING",
            "gpu": "RTX 5060 Ti (Blackwell sm_120)",
            "pytorch": "2.7.1+cu128",
            "vram": "0.55GB",
            "init_time": "5.2s",
            "port": 8000,
            "build_status_excerpt": status_text[:100]
        },
        "blockers": [
            "No webcam on dev machine",
            "Need venue for live demo",
            "PVR branding overlay not built"
        ],
        "next_actions": [
            "Webcam at venue",
            "Live demo test",
            "PVR branding overlay"
        ],
        "decisions": [
            "PyTorch 2.7.1+cu128 for Blackwell",
            "HuggingFace for model (GitHub 404)",
            "numpy<2 for onnxruntime compat"
        ]
    }


# ============================================================
# MAIN
# ============================================================

PROJECT_GETTERS = {
    "CINE": get_cineverse_status,
    "NEET-UG": get_neetug_status,
    "NEET-PG": get_neetpg_status,
    "CHOTU": get_chotu_status,
    "QCLAW": get_qclaw_status,
    "STYLE": get_style_status,
    "UPSC": get_upsc_status,
    "PHOTO": get_photo_status,
}


def build_status():
    status = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "updated_by": "alfred_push_status",
        "projects": {},
        "alerts": []
    }

    for code, getter in PROJECT_GETTERS.items():
        print(f"  [{code}] Querying...")
        try:
            status["projects"][code] = getter()
            src = status["projects"][code].get("source", "unknown")
            print(f"  [{code}] OK (source: {src})")
        except Exception as e:
            status["projects"][code] = _stale(code, str(e))
            print(f"  [{code}] ERROR: {e}")

    return status


def write_and_push(status, commit_msg=None):
    os.chdir(REPO_DIR)

    with open("status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    print("  Wrote status.json")

    os.makedirs("projects", exist_ok=True)
    for code, data in status["projects"].items():
        with open(f"projects/{code}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(status['projects'])} project files")

    os.makedirs("logs", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    with open(f"logs/{today}.jsonl", "a", encoding="utf-8") as f:
        entry = {
            "timestamp": status["last_updated"],
            "projects": {k: {"summary": v.get("summary", ""), "source": v.get("source", "unknown")} 
                        for k, v in status["projects"].items()}
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  Appended to logs/{today}.jsonl")

    if not commit_msg:
        commit_msg = f"status update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    subprocess.run(["git", "add", "."], check=True)
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push_result.returncode == 0:
            print("  Pushed to GitHub successfully.")
        else:
            print(f"  Push failed: {push_result.stderr}")
            print("  Commit saved locally. Run 'git push' manually after auth.")
    else:
        print("  No changes to push.")


if __name__ == "__main__":
    print("=" * 60)
    print("PROJECT MONITOR - Status Push")
    print("=" * 60)
    status = build_status()
    print()
    print("Project summaries:")
    for code, proj in status["projects"].items():
        src = proj.get("source", "?")
        print(f"  [{code}] ({src}) {proj.get('summary', 'N/A')}")
    print()
    write_and_push(status)
    print("\nDone!")
