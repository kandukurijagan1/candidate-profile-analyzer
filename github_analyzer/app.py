import os, time
from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
GITHUB = "https://api.github.com"

# ===== Load token safely =====
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"
else:
    print("⚠️ WARNING: GITHUB_TOKEN not set. You may hit rate limits.")

# ===== Simple in-memory cache =====
CACHE = {}
CACHE_TTL_SECONDS = 600  # 10 minutes

# ===== Limit deep analysis to avoid rate limits =====
MAX_REPOS_TO_SCAN = 3  # 🔴 Change to 5 or 10 if you want deeper analysis

def fetch_json(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        try:
            data = r.json()
        except Exception:
            return r.status_code, None
        return r.status_code, data
    except requests.exceptions.RequestException:
        return None, None

def hr_evaluate(username: str):
    now = time.time()
    if username in CACHE and now - CACHE[username]["time"] < CACHE_TTL_SECONDS:
        return CACHE[username]["data"], None

    # ---- Validate user ----
    status, user = fetch_json(f"{GITHUB}/users/{username}")
    if status == 404:
        return None, "GitHub profile not found."
    if status == 403:
        return None, "GitHub API rate limit reached. Please try again later."
    if status != 200 or not isinstance(user, dict):
        return None, "GitHub API error while fetching profile."

    # ---- Fetch repos ----
    status, repos = fetch_json(
        f"{GITHUB}/users/{username}/repos",
        params={"per_page": 50, "sort": "updated"}
    )
    if status == 403:
        return None, "GitHub API rate limit reached. Please try again later."
    if status != 200 or not isinstance(repos, list):
        return None, "Unable to fetch repositories."

    total = len(repos)
    readmes = 0
    stars = 0
    langs = set()
    complete = 0
    recent_commits = 0
    since = (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"

    for r in repos[:MAX_REPOS_TO_SCAN]:
        if not isinstance(r, dict):
            continue

        stars += int(r.get("stargazers_count", 0) or 0)
        if r.get("language"):
            langs.add(r["language"])
        if r.get("description") and r.get("license"):
            complete += 1

        name = r.get("name")
        if not name:
            continue

        rm_status, _ = fetch_json(f"{GITHUB}/repos/{username}/{name}/readme")
        if rm_status == 200:
            readmes += 1

        c_status, commits = fetch_json(
            f"{GITHUB}/repos/{username}/{name}/commits",
            params={"since": since}
        )
        if c_status == 200 and isinstance(commits, list):
            recent_commits += len(commits)

    # ---- Scoring ----
    scanned = max(1, min(total, MAX_REPOS_TO_SCAN))
    doc = int((readmes / scanned) * 100)
    activity = min(100, int((recent_commits / max(1, scanned * 4)) * 100))
    org = int((complete / scanned) * 100)
    tech = min(100, len(langs) * 20)
    impact = min(100, int((stars / 10) * 100))

    final_100 = int(0.30 * doc + 0.20 * activity + 0.20 * org + 0.15 * tech + 0.15 * impact)
    rating = max(1, min(10, round(final_100 / 10, 1)))

    if rating >= 8:
        verdict, verdict_color = "Strong Fit", "green"
    elif rating >= 5:
        verdict, verdict_color = "Potential (Needs Improvement)", "yellow"
    else:
        verdict, verdict_color = "Not Recruiter-Ready Yet", "red"

    positives, concerns, actions = [], [], []

    if doc >= 70:
        positives.append("Clear documentation makes projects easy to evaluate.")
    else:
        concerns.append("Many repositories lack README or setup instructions.")
        actions.append("Add README with setup steps, screenshots, and demo links.")

    if activity >= 60:
        positives.append("Consistent recent activity shows active learning.")
    else:
        concerns.append("Low recent commit activity.")
        actions.append("Make small weekly commits.")

    if tech >= 60:
        positives.append("Good technical breadth across technologies.")
    else:
        actions.append("Add a project in a new technology stack.")

    if impact >= 40:
        positives.append("Some impact signals (stars/forks) indicate relevance.")
    else:
        concerns.append("Low visibility/impact signals.")
        actions.append("Add demo links & project stories.")

    defaults = ["Pin your top 2 repositories.", "Add topics to repositories."]
    actions = actions[:3] if len(actions) >= 3 else actions + defaults[:max(0, 3 - len(actions))]

    result = {
        "repos": total,
        "readmes": readmes,
        "stars": stars,
        "languages": ", ".join(sorted(langs)) or "N/A",
        "rating": rating,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "subs": {
            "Documentation": doc,
            "Activity": activity,
            "Organization": org,
            "Tech Depth": tech,
            "Impact": impact
        },
        "positives": positives or ["Profile basics look fine."],
        "concerns": concerns or ["No critical red flags found."],
        "actions": actions
    }

    CACHE[username] = {"time": time.time(), "data": result}
    return result, None

@app.route("/", methods=["GET", "POST"])
def home():
    data, err = None, None
    if request.method == "POST":
        url = request.form.get("url", "").strip().rstrip("/")
        username = url.split("/")[-1]
        data, err = hr_evaluate(username)
    return render_template("index.html", data=data, err=err)

if __name__ == "__main__":
    app.run(debug=True)
