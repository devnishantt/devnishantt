#!/usr/bin/env python3
"""An HTTP-style API whose transport is GitHub Issues.

Open an issue titled like `GET /projects/ledgerline` on this repository. The `profile-api`
workflow runs this script, which answers in a comment formatted as an HTTP response,
closes the issue, appends the call to data/access-log.json and redraws
assets/access-log.svg so the README shows the request.

The issue title is untrusted input. It is read from the event payload file (never
interpolated into a shell), matched against a fixed route table and echoed only inside
code fences. Nothing in it is executed.

Standard library only. Runs inside GitHub Actions with GITHUB_TOKEN, GITHUB_REPOSITORY and
GITHUB_EVENT_PATH set.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_profile as bp  # noqa: E402

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "BREW")
REASONS = {200: "OK", 201: "Created", 400: "Bad Request", 403: "Forbidden", 404: "Not Found",
           405: "Method Not Allowed", 418: "I'm a teapot"}
MAX_LOG = 60


# ---------------------------------------------------------------- GitHub REST

def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"bearer {token}", "Accept": "application/vnd.github+json",
                 "User-Agent": "profile-api", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


# ---------------------------------------------------------------- routes

def project_by_name(name: str) -> dict | None:
    key = name.lower()
    for p in bp.PROJECTS:
        if key in (p["slug"], p["repo"].lower(), p["name"].lower()):
            return p
    return None


def project_json(p: dict, ci: dict | None = None) -> dict:
    out = {"name": p["name"], "repo": f"https://github.com/{USER}/{p['repo']}", "summary": p["tag"],
           "what": p["desc"], "hard_part": p["hard"],
           "stack": [bp.ICONS[s]["title"] for s in p["stack"]]}
    if ci is not None:
        out["ci"] = ci_json(ci)
    return out


def ci_json(run: dict | None) -> dict:
    if run is None:
        return {"status": "no CI"}
    return {"status": bp.ci_look(run)[1], "workflow": run["name"], "commit": run["sha"],
            "duration_s": run["seconds"], "finished": run["date"], "url": run["url"]}


def route(method: str, path: str, token: str) -> tuple[int, dict]:
    path = "/" + path.strip().strip("/")
    path = re.sub(r"/{2,}", "/", path)
    parts = [x for x in path.split("/") if x]

    if method == "BREW" or (method == "POST" and path in ("/coffee", "/tea")):
        return 418, {"error": "I'm a teapot", "detail": "This server refuses to brew coffee. "
                     "It does ship backends though: try GET /projects."}
    if method == "OPTIONS":
        return 200, {"allow": ["GET", "OPTIONS"], "routes": ROUTES}
    if method in ("DELETE", "PUT", "PATCH"):
        return 403, {"error": "Forbidden", "detail": "This profile is append-only, like a good audit log."}
    if method == "POST":
        return 405, {"error": "Method Not Allowed", "allow": ["GET", "OPTIONS"],
                     "hint": "Want to reach me? Star a repo or open a real issue on one."}
    if method == "HEAD":
        return 200, {}

    if path == "/":
        return 200, {"service": f"{USER}-profile-api", "transport": "GitHub Issues",
                     "version": "1.0.0", "routes": ROUTES}
    if path in ("/about", "/whoami"):
        return 200, {"name": "Nishant", "handle": f"@{USER}", "role": "Backend engineer",
                     "languages": ["TypeScript", "JavaScript", "Python"],
                     "focus": ["correctness under concurrency", "money and ledgers",
                               "auditability", "CI on every repository"],
                     "github": f"https://github.com/{USER}"}
    if path == "/projects":
        return 200, {"count": len(bp.PROJECTS),
                     "projects": [{"name": p["name"], "path": f"/projects/{p['slug']}", "summary": p["tag"]}
                                  for p in bp.PROJECTS]}
    if len(parts) == 2 and parts[0] == "projects":
        p = project_by_name(parts[1])
        if p is None:
            return 404, {"error": "Not Found", "detail": f"No project called {parts[1]!r}.",
                         "try": [f"/projects/{q['slug']}" for q in bp.PROJECTS]}
        return 200, project_json(p, bp.fetch_ci(token, USER, p["repo"]))
    if path == "/ci":
        runs = {p["slug"]: bp.fetch_ci(token, USER, p["repo"]) for p in bp.PROJECTS}
        green = sum(1 for r in runs.values() if r and r["conclusion"] == "success")
        return 200, {"green": green, "total": sum(1 for r in runs.values() if r),
                     "pipelines": {p["name"]: ci_json(runs[p["slug"]]) for p in bp.PROJECTS}}
    if path == "/stack":
        return 200, {"tools": [bp.ICONS[s]["title"] for s in bp.STACK]}
    if path in ("/now", "/stats"):
        prof = bp.fetch_profile(token, USER)
        return 200, {"contributions_7d": sum(c for _, c in prof["days"][-7:]),
                     "contributions_past_year": prof["contributions"],
                     "streak_days": bp.streak(prof["days"]),
                     "public_repositories": len(prof["repos"])}
    if path == "/teapot":
        return 418, {"error": "I'm a teapot", "detail": "Short and stout."}
    return 404, {"error": "Not Found", "detail": f"No route for GET {path}.", "routes": ROUTES}


ROUTES = ["GET /", "GET /about", "GET /projects", "GET /projects/{name}", "GET /ci",
          "GET /stack", "GET /now", "OPTIONS /", "BREW /coffee"]


def parse(title: str) -> tuple[str, str] | None:
    m = re.match(r"^\s*([A-Za-z]{3,7})\s+(/[\x21-\x7e]{0,120})\s*$", title or "")
    if not m or m.group(1).upper() not in METHODS:
        return None
    return m.group(1).upper(), m.group(2)


# ---------------------------------------------------------------- response

def render(status: int, payload: dict, method: str, path: str, rtt: int, n: int) -> str:
    reason = REASONS.get(status, "")
    head = [f"HTTP/1.1 {status} {reason}", "content-type: application/json; charset=utf-8",
            f"x-request-id: req_{n:05d}", "x-served-by: github-actions",
            f"x-response-time: {bp.fmt_rtt(rtt)}"]
    body = "" if method == "HEAD" else json.dumps(payload, indent=2, ensure_ascii=False)
    safe = f"{method} {path}".replace("`", "'")
    parts = [f"```http\n{safe} HTTP/1.1\nhost: github.com/{USER}\n```",
             "```http\n" + "\n".join(head) + "\n```"]
    if body:
        parts.append(f"```json\n{body}\n```")
    parts.append(f"<sub>Served by <a href=\"https://github.com/{REPO}/blob/main/scripts/profile_api.py\">"
                 f"<code>scripts/profile_api.py</code></a> in GitHub Actions. This request now appears in the "
                 f"access log on the <a href=\"https://github.com/{USER}\">profile</a>. "
                 f"Try another: <code>GET /projects</code>, <code>GET /ci</code>, <code>BREW /coffee</code>.</sub>")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- access log

def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def record(entry: dict) -> None:
    """Append to the log and push. Re-reads from origin on every attempt, so concurrent runs never conflict."""
    for attempt in range(6):
        git("fetch", "--quiet", "origin", "main")
        git("reset", "--quiet", "--hard", "origin/main")
        log = bp.load_log()
        log["served"] += 1
        log["entries"] = (log["entries"] + [entry])[-MAX_LOG:]
        bp.LOG_FILE.parent.mkdir(exist_ok=True)
        bp.LOG_FILE.write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
        (bp.ASSETS / "access-log.svg").write_text(bp.build_access_log(log, USER), encoding="utf-8")
        git("add", str(bp.LOG_FILE), str(bp.ASSETS / "access-log.svg"))
        git("commit", "--quiet", "-m", f"chore(api): {entry['method']} {entry['path']} -> {entry['status']}")
        if subprocess.run(["git", "push", "--quiet", "origin", "HEAD:main"]).returncode == 0:
            return
        time.sleep(2 + attempt * 2)
    raise SystemExit("could not push the access log after several attempts")


# ---------------------------------------------------------------- main

USER = os.environ.get("PROFILE_USER", "devnishantt")
REPO = os.environ.get("GITHUB_REPOSITORY", f"{USER}/{USER}")


def main() -> int:
    token = os.environ["GITHUB_TOKEN"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    issue = event["issue"]
    caller = issue["user"]["login"]
    parsed = parse(issue["title"])
    if parsed is None:
        method, path = "GET", "/?"
        status, payload = 400, {"error": "Bad Request",
                                "detail": "Title must look like an HTTP request line, e.g. GET /projects.",
                                "routes": ROUTES}
    else:
        method, path = parsed
        try:
            status, payload = route(method, path, token)
        except Exception as exc:  # a failing lookup is still answered
            print(f"route error: {exc}", file=sys.stderr)
            status, payload = 200, {"note": "Upstream lookup failed; try again shortly."}

    created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    rtt = max(1, int((datetime.now(timezone.utc) - created).total_seconds()))
    n = bp.load_log()["served"] + 1
    num = issue["number"]
    api("POST", f"/repos/{REPO}/issues/{num}/comments", token,
        {"body": render(status, payload, method, path, rtt, n)})
    api("PATCH", f"/repos/{REPO}/issues/{num}", token,
        {"state": "closed", "state_reason": "completed" if status < 400 or status == 418 else "not_planned"})

    record({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "user": caller,
            "method": method, "path": path[:60], "status": status, "rtt": rtt})
    print(f"{caller}: {method} {path} -> {status} in {rtt}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
