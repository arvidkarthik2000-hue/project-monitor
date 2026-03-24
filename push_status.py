#!/usr/bin/env python3
"""Push live project status to GitHub repo.
Queries each project's Supabase DB for real numbers.
Run after every work session or every 2 hours during long sessions."""

import json, os, subprocess, sys, io
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO_DIR = Path(__file__).parent
ENV_FILE = REPO_DIR / ".env"

# Load .env if exists
env_vars = {}
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")

# --- SUPABASE HELPERS ---

def sb_count(base_url, key, table, filter_str=""):
    """Count rows in a Supabase table with optional filter."""
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


def sb_get(base_url, key, query):
    """GET from Supabase REST API."""
    url = f"{base_url}/{query}"
    req = Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}"
    })
    resp = urlopen(req, timeout=15)
    return json.loads(resp.read())


# --- CINEVERSE ---

CINE_SB_URL = env_vars.get("CINE_SUPABASE_URL", "https://inmaobjileopqyhfqsbo.supabase.co/rest/v1")
CINE_SB_KEY = env_vars.get("CINE_SUPABASE_KEY", "")


def get_cineverse_status():
    """Query CineVerse Supabase for live numbers."""
    if not CINE_SB_KEY:
        return _stale("CineVerse", "CINE_SUPABASE_KEY not set in .env")
    try:
        movies_total = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies")
        movies_cast = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&cast=not.is.null")
        questions_total = sb_count(CINE_SB_URL, CINE_SB_KEY, "questions")
        questions_active = sb_count(CINE_SB_URL, CINE_SB_KEY, "questions", "&is_active=eq.true")

        # Enrichment counts
        wiki = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&wiki_production=not.is.null")
        omdb = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&rotten_tomatoes=not.is.null")
        saavn = sb_count(CINE_SB_URL, CINE_SB_KEY, "movies", "&songs=not.is.null")

        return {
            "name": "CineVerse",
            "status": "active",
            "progress": 35,
            "phase": "Data Collection + Question Generation",
            "summary": f"{movies_total} movies, {questions_total} total questions, enrichment ongoing",
            "db": {
                "movies_total": movies_total,
                "movies_with_cast": movies_cast,
                "questions_total": questions_total,
                "questions_active": questions_active,
                "enrichment": {
                    "wiki": wiki,
                    "omdb": omdb,
                    "jiosaavn": saavn
                }
            },
            "blockers": [],
            "next_actions": [],
            "decisions": []
        }
    except Exception as e:
        return _stale("CineVerse", f"DB query failed: {e}")


# --- NEET PG ---

NEETPG_SB_URL = env_vars.get("NEETPG_SUPABASE_URL", "https://tgtxfbfuzpkqofxnrtie.supabase.co/rest/v1")
NEETPG_SB_KEY = env_vars.get("NEETPG_SUPABASE_KEY", "")


def get_neetpg_status():
    """Query NEET PG Supabase for live numbers."""
    if not NEETPG_SB_KEY:
        return _stale("NEET PG Exam Prep", "NEETPG_SUPABASE_KEY not set in .env")
    try:
        total = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "questions")
        # Try v2 count
        v2 = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "questions", "&source=eq.gemini_v2")
        articles = sb_count(NEETPG_SB_URL, NEETPG_SB_KEY, "knowledge_articles")

        return {
            "name": "NEET PG Exam Prep",
            "status": "active",
            "progress": 45,
            "phase": "V2 Engine Generation (Gemini)",
            "summary": f"{total} total Qs, {v2} v2 generated, {articles} knowledge articles",
            "db": {
                "questions_total": total,
                "questions_v2_gemini": v2,
                "knowledge_articles": articles
            },
            "blockers": [],
            "next_actions": [],
            "decisions": []
        }
    except Exception as e:
        return _stale("NEET PG Exam Prep", f"DB query failed: {e}")


# --- HELPER ---

def _stale(name, reason):
    """Return a stale status entry when DB can't be queried."""
    return {
        "name": name,
        "status": "unknown",
        "summary": f"Awaiting live data - {reason}",
        "db": {},
        "blockers": [reason],
        "next_actions": ["Configure DB credentials in .env"],
        "decisions": []
    }


# --- STATIC PROJECTS (no live DB yet) ---

def get_static_project(code):
    """Read existing project JSON for projects without live DB queries."""
    path = REPO_DIR / "projects" / f"{code}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return _stale(code, "No project file found")


# --- MAIN ---

def build_status():
    """Build complete status.json from all project DBs."""
    status = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "updated_by": "alfred_push_status",
        "projects": {}
    }

    # Live DB queries
    print("  Querying CineVerse Supabase...")
    status["projects"]["CINE"] = get_cineverse_status()

    print("  Querying NEET PG Supabase...")
    status["projects"]["NEET-PG"] = get_neetpg_status()

    # Static projects (read existing JSON, update timestamp)
    for code in ["NEET-UG", "CHOTU", "QCLAW", "STYLE", "UPSC", "PHOTO"]:
        print(f"  Loading {code} from existing file...")
        status["projects"][code] = get_static_project(code)

    # Alerts
    status["alerts"] = []

    return status


def write_and_push(status, commit_msg=None):
    """Write status files and push to GitHub."""
    os.chdir(REPO_DIR)

    # Write master status
    with open("status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    print("  Wrote status.json")

    # Write per-project files
    os.makedirs("projects", exist_ok=True)
    for code, data in status["projects"].items():
        with open(f"projects/{code}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(status['projects'])} project files")

    # Append to daily log
    os.makedirs("logs", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    with open(f"logs/{today}.jsonl", "a", encoding="utf-8") as f:
        entry = {
            "timestamp": status["last_updated"],
            "summary": {k: v.get("summary", "") for k, v in status["projects"].items()}
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  Appended to logs/{today}.jsonl")

    # Git commit and push
    if not commit_msg:
        commit_msg = f"status update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    subprocess.run(["git", "add", "."], check=True)
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("  Pushed to GitHub successfully.")
    else:
        print("  No changes to push.")


if __name__ == "__main__":
    print("Building project status...")
    status = build_status()
    print("\nProject summaries:")
    for code, proj in status["projects"].items():
        print(f"  {code}: {proj.get('summary', 'N/A')}")
    print()
    write_and_push(status)
    print("\nDone!")
