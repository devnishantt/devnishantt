#!/usr/bin/env python3
"""Generate the profile README graphics from live GitHub data.

Writes, all self-contained (images embedded, no third-party services):
  assets/hero.svg       animated terminal intro with live repository and CI numbers
  assets/pipeline.svg   live CI board: the latest main-branch run of every featured project
  assets/card-*.svg     project cards with a live CI status light
  assets/stack.svg      tools I use, plus the language split of my own repositories
  assets/heartbeat.svg  daily contributions drawn as an ECG trace
  assets/access-log.svg the latest requests made to the issue-driven profile API (scripts/profile_api.py)
  assets/divider.svg    animated section divider
  assets/h-*.svg        typed section headings
  assets/principles.svg how I build, rendered as a passing test run
  assets/trace.svg      written by scripts/profile_api.py: a waterfall trace of the latest API request
  assets/footer.svg     animated sign-off

Standard library only. Usage: GITHUB_TOKEN=... python scripts/build_profile.py [--user LOGIN]
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import os
import random
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = json.loads((ROOT / "scripts" / "icons.json").read_text())

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
VIOLET, CYAN, GREEN, GREY, RED, AMBER = "#a371f7", "#39d0d8", "#3fb950", "#8b949e", "#f85149", "#d29922"

STACK = ["typescript", "javascript", "nodedotjs", "python", "express", "fastify", "hono", "bun",
         "react", "zod", "prisma", "postgresql", "redis", "cloudflare", "duckdb", "pydantic",
         "vitest", "pytest", "docker", "githubactions", "mysql", "mongodb", "git", "github"]

# Featured projects, newest work first. `steps` mirrors each repository's CI workflow.
PROJECTS = [
    {"slug": "ledgerline", "hard": 'Integer minor-unit money, ambiguous matches left unresolved instead of guessed, a separate reviewer credential for approvals and a hash-linked audit chain that detects a missing tail.', "repo": "ledgerline", "name": "Ledgerline", "lang": "typescript",
     "tag": "Financial reconciliation workspace",
     "desc": "Matches bank statements against ledger records with exact minor-unit money, a separate "
             "reviewer credential for approvals and a hash-linked audit trail.",
     "stack": ["react", "hono", "cloudflare", "zod"],
     "steps": ["install", "typecheck", "test", "build", "audit"]},
    {"slug": "aftermark", "hard": 'An incident closes only after two non-creator principals approve the current SHA-256 evidence manifest; new evidence makes old approvals stale, and every write claims the next revision.', "repo": "aftermark", "name": "Aftermark", "lang": "typescript",
     "tag": "Evidence-driven incident response API",
     "desc": "Incidents close only when two independent people approve the exact evidence manifest. "
             "Hash-linked history and revision-claimed writes.",
     "stack": ["fastify", "bun", "zod", "cloudflare"],
     "steps": ["install", "typecheck", "test", "build", "docker"]},
    {"slug": "pactrail", "hard": 'A conservative OpenAPI diff: anything it cannot prove safe is flagged for review and blocks CI. Backed by 639 tests, most of them schema boundary cases.', "repo": "Pactrail", "name": "Pactrail", "lang": "typescript",
     "tag": "API contract checks and OpenAPI diffing",
     "desc": "Library and CLI that validates payloads against OpenAPI schemas, flags breaking changes "
             "between versions and runs deterministic response fixtures.",
     "stack": ["typescript", "nodedotjs", "zod", "vitest"],
     "steps": ["install", "typecheck", "test", "smoke", "pack"]},
    {"slug": "tracebench", "hard": "Drift checks that report 'incomparable' instead of quietly saying 'stable', with bounded ingestion, exact decimal bounds and fingerprinted offline reports.", "repo": "tracebench", "name": "Tracebench", "lang": "python",
     "tag": "Local-first dataset contracts and drift",
     "desc": "Checks CSV, JSONL and Parquet files against explicit contracts, profiles them and writes "
             "reproducible drift reports in JSON, Markdown and HTML.",
     "stack": ["python", "duckdb", "pydantic", "pytest"],
     "steps": ["install", "lint", "mypy", "test", "build"]},
    {"slug": "bank", "hard": 'A double-entry ledger you can check against balances, transfers that lock rows in a fixed order so they cannot deadlock, and Idempotency-Key retries that never double-charge.', "repo": "bank-management-system", "name": "bank-management-system", "lang": "typescript",
     "tag": "Banking REST API",
     "desc": "Double-entry ledger, row-locked transfers that cannot deadlock, Idempotency-Key retries "
             "and rotating refresh tokens.",
     "stack": ["express", "prisma", "postgresql", "docker"],
     "steps": ["install", "typecheck", "test", "build"]},
    {"slug": "hospital", "hard": 'Access and refresh token rotation, a Redis-backed token blacklist, rate limiting, uploads and email in a layered Express service.', "repo": "Hospital-Management", "name": "Hospital-Management", "lang": "typescript",
     "tag": "Hospital management API",
     "desc": "JWT access and refresh tokens with rotation, a Redis-backed token blacklist, rate "
             "limiting, file uploads and email.",
     "stack": ["express", "prisma", "postgresql", "redis"],
     "steps": ["install", "generate", "typecheck", "build", "audit"]},
]

PROFILE_QUERY = """
query($login: String!) { user(login: $login) {
  createdAt
  contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } }
  repositories(ownerAffiliations: OWNER, isFork: false, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
    nodes { name isPrivate languages(first: 10) { edges { size node { name color } } } }
  }
} }"""


# ---------------------------------------------------------------- data

def request(url: str, token: str, data: bytes | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"bearer {token}", "User-Agent": "profile-builder",
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def gql(token: str, query: str, variables: dict) -> dict:
    payload = request("https://api.github.com/graphql", token,
                      json.dumps({"query": query, "variables": variables}).encode())
    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def fetch_profile(token: str, user: str) -> dict:
    u = gql(token, PROFILE_QUERY, {"login": user})["user"]
    # The profile repository itself is not a project; private repositories are not advertised.
    repos = [r for r in u["repositories"]["nodes"] if r["name"].lower() != user.lower() and not r["isPrivate"]]
    langs: dict[str, list] = {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            entry = langs.setdefault(e["node"]["name"], [0, e["node"]["color"] or GREY])
            entry[0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])
    return {"since": u["createdAt"][:4], "repos": [r["name"] for r in repos],
            "contributions": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
            "days": [(d["date"], d["contributionCount"])
                     for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]],
            "languages": [(name, size / total, color) for name, (size, color) in top if size / total >= 0.005]}


def fetch_ci(token: str, user: str, repo: str) -> dict | None:
    """Latest completed main-branch workflow run, or None when the repository has no CI."""
    url = (f"https://api.github.com/repos/{user}/{repo}/actions/runs"
           f"?branch=main&status=completed&per_page=1&exclude_pull_requests=true")
    try:
        runs = request(url, token).get("workflow_runs") or []
    except Exception as exc:
        print(f"warning: CI lookup for {repo}: {exc}", file=sys.stderr)
        return None
    if not runs:
        return None
    r = runs[0]
    start = datetime.fromisoformat((r.get("run_started_at") or r["created_at"]).replace("Z", "+00:00"))
    end = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
    return {"conclusion": r["conclusion"] or "unknown", "name": r["name"], "sha": r["head_sha"][:7],
            "seconds": max(0, int((end - start).total_seconds())), "date": end.strftime("%b %d"),
            "url": r["html_url"]}


def fetch_image(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-builder"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return data_uri(resp.read())
    except Exception as exc:  # an avatar we cannot fetch falls back to a monogram
        print(f"warning: {url}: {exc}", file=sys.stderr)
        return None


def data_uri(raw: bytes) -> str:
    mime = ("image/png" if raw[:4] == b"\x89PNG" else "image/gif" if raw[:3] == b"GIF"
            else "image/webp" if raw[:4] == b"RIFF" else "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def ci_look(ci: dict | None) -> tuple[str, str]:
    if ci is None:
        return GREY, "no CI"
    return {"success": (GREEN, "passing"), "failure": (RED, "failing"),
            "cancelled": (GREY, "cancelled")}.get(ci["conclusion"], (AMBER, ci["conclusion"]))


# ---------------------------------------------------------------- helpers

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def human(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def kt(*times: float) -> str:
    """keyTimes string, clamped and non-decreasing."""
    out, last = [], 0.0
    for t in times:
        last = max(last, min(1.0, max(0.0, t)))
        out.append(f"{last:.4f}")
    return ";".join(out)


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + ([line] if line else [])


def icon(slug: str, x: float, y: float, size: float, cls: str = "") -> str:
    ic = ICONS[slug]
    scale = size / 24
    lum = luminance(ic["hex"])
    klass = f' class="{cls}{" dk" if lum < 0.25 else ""}"'
    return (f'<path{klass} fill="#{ic["hex"]}" transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})" '
            f'd="{ic["path"]}"/>')


def luminance(hex_: str) -> float:
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def svg_open(w: int, h: int, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">')


def starfield(w: int, h: int, count: int, seed: int) -> str:
    rnd = random.Random(seed)
    out = []
    for i in range(count):
        x, y, r = rnd.uniform(4, w - 4), rnd.uniform(4, h - 4), rnd.choice([0.5, 0.7, 0.9, 1.2])
        o = rnd.uniform(0.25, 0.8)
        tw = ""
        if i % 3 == 0:
            d = rnd.uniform(2.5, 6.0)
            tw = (f'<animate attributeName="opacity" values="{o:.2f};0.05;{o:.2f}" dur="{d:.1f}s" '
                  f'begin="-{rnd.uniform(0, d):.1f}s" repeatCount="indefinite"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#c9d1d9" opacity="{o:.2f}">{tw}</circle>')
    return "".join(out)


# ---------------------------------------------------------------- hero

def build_hero(prof: dict, ci: dict, user: str, avatar: str | None) -> str:
    W, H, fs, lh, x0, y0 = 960, 320, 14, 26, 314, 100
    cw = fs * 0.62
    featured = [p["repo"] for p in PROJECTS]
    listing = ""
    for name in featured:
        candidate = f"{listing}  {name}".strip()
        if len(candidate) > 62:
            listing += "  …"
            break
        listing = candidate
    with_ci = [p for p in PROJECTS if ci.get(p["slug"])]
    green = sum(ci[p["slug"]]["conclusion"] == "success" for p in with_ci)
    lines = [
        ("cmd", "whoami"),
        ("out", [("Nishant", "name"), (" · backend engineer · TypeScript, Node.js & Python", "txt")]),
        ("cmd", "ls ~/projects --featured"),
        ("out", [(listing, "cy")]),
        ("cmd", "gh run list --branch main"),
        ("out", [("● ", "op" if green == len(with_ci) else "yl"),
                 (f"{green}/{len(with_ci)} pipelines green   ", "txt"), ("● ", "mg"),
                 (f"{len(prof['repos'])} public repositories", "txt")]),
    ]
    t, timing = 0.6, []
    for kind, content in lines:
        if kind == "cmd":
            end = t + len(content) * 0.05
            timing.append((t, end))
            t = end + 0.35
        else:
            timing.append((t, t))
            t += 0.5
    final, T = t, t + 0.6

    defs, body = [], []
    for i, ((kind, content), (a, b)) in enumerate(zip(lines, timing)):
        y = y0 + i * lh
        if kind == "cmd":
            w = (len(content) + 2) * cw + 6
            k = kt(0, a / T, b / T, 1)
            defs.append(f'<clipPath id="c{i}"><rect x="{x0}" y="{y - 17}" width="{w:.1f}" height="24">'
                        f'<animate attributeName="width" values="0;0;{w:.1f};{w:.1f}" keyTimes="{k}" dur="{T:.2f}s" '
                        f'fill="freeze"/></rect></clipPath>')
            body.append(f'<text xml:space="preserve" class="m" x="{x0}" y="{y}" clip-path="url(#c{i})"><tspan class="pr">$ </tspan>'
                        f'<tspan class="cmd">{esc(content)}</tspan></text>')
            cx0, cx1 = x0 + 2 * cw, x0 + w - 4
            body.append(f'<rect class="cur" x="{cx0:.1f}" y="{y - 13}" width="8" height="16" opacity="0">'
                        f'<animate attributeName="x" values="{cx0:.1f};{cx0:.1f};{cx1:.1f};{cx1:.1f}" keyTimes="{k}" '
                        f'dur="{T:.2f}s" fill="freeze"/>'
                        f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
                        f'keyTimes="{kt(0, a / T, a / T, (b + 0.3) / T, (b + 0.3) / T, 1)}" dur="{T:.2f}s" fill="freeze"/>'
                        f'</rect>')
        else:
            spans = "".join(f'<tspan class="{c}">{esc(s)}</tspan>' for s, c in content)
            body.append(f'<text xml:space="preserve" class="m" x="{x0}" y="{y}">{spans}'
                        f'<animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt(0, a / T, a / T + 0.01, 1)}" '
                        f'dur="{T:.2f}s" fill="freeze"/></text>')
    yf = y0 + len(lines) * lh
    body.append(f'<text xml:space="preserve" class="m" x="{x0}" y="{yf}"><tspan class="pr">$ </tspan>'
                f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt(0, final / T, final / T)}" '
                f'dur="{T:.2f}s" fill="freeze"/></text>')
    body.append(f'<rect class="cur" x="{x0 + 2 * cw:.1f}" y="{yf - 13}" width="8" height="16">'
                f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt(0, final / T, final / T)}" '
                f'dur="{T:.2f}s" fill="freeze"/>'
                f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" '
                f'begin="{final:.2f}s" repeatCount="indefinite"/></rect>')

    acx, acy, ar = 160, 146, 88
    face = (f'<image href="{avatar}" x="{acx - ar}" y="{acy - ar}" width="{2 * ar}" height="{2 * ar}" '
            f'clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>' if avatar else
            f'<text x="{acx}" y="{acy + 22}" text-anchor="middle" class="mono-big">N</text>')
    return f"""{svg_open(W, H, f"Terminal intro for {user}: backend engineer. {green} of {len(with_ci)} featured CI pipelines are green.")}
<style>
  .m{{font:{fs}px {MONO};white-space:pre}} .pr{{fill:{VIOLET};font-weight:700}} .cmd{{fill:#e6edf3}}
  .txt{{fill:#c9d1d9}} .name{{fill:{CYAN};font-weight:700}} .mg{{fill:{VIOLET}}} .op{{fill:{GREEN}}}
  .cy{{fill:{CYAN}}} .yl{{fill:{AMBER}}} .cur{{fill:{CYAN}}} .dim{{fill:#6e7681;font:12px {MONO}}}
  .handle{{fill:#c9d1d9;font:600 14px {MONO}}} .mono-big{{fill:#e6edf3;font:700 64px {SANS}}}
  .scan{{animation:scan 7s linear infinite}} @keyframes scan{{from{{transform:translateY(-40px)}}to{{transform:translateY({H}px)}}}}
</style>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#150b2e"/></linearGradient>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="scanline" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".07"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".55"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#ffffff" opacity=".06"/></pattern>
  <clipPath id="av"><circle cx="{acx}" cy="{acy}" r="{ar}"/></clipPath>
  <clipPath id="term"><rect x="290" y="30" width="644" height="260" rx="14"/></clipPath>
  {''.join(defs)}
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<rect width="{W}" height="{H}" rx="20" fill="url(#dots)"/>
{starfield(W, H, 40, 3)}
<circle cx="{acx}" cy="{acy}" r="128" fill="url(#glow)"><animate attributeName="r" values="118;134;118" dur="5s" repeatCount="indefinite"/></circle>
{face}
<circle cx="{acx}" cy="{acy}" r="{ar + 9}" fill="none" stroke="url(#ring)" stroke-width="3" stroke-linecap="round" stroke-dasharray="70 26 14 26">
  <animateTransform attributeName="transform" type="rotate" from="0 {acx} {acy}" to="360 {acx} {acy}" dur="16s" repeatCount="indefinite"/></circle>
<circle cx="{acx}" cy="{acy}" r="{ar + 18}" fill="none" stroke="{CYAN}" stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 7">
  <animateTransform attributeName="transform" type="rotate" from="360 {acx} {acy}" to="0 {acx} {acy}" dur="40s" repeatCount="indefinite"/></circle>
<circle cx="{acx + 62}" cy="{acy + 64}" r="9" fill="{GREEN}" stroke="#0b1020" stroke-width="4"/>
<circle cx="{acx + 62}" cy="{acy + 64}" r="9" fill="none" stroke="{GREEN}" stroke-width="2">
  <animate attributeName="r" values="9;20" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0" dur="2s" repeatCount="indefinite"/></circle>
<text x="{acx}" y="278" text-anchor="middle" class="handle">@{esc(user)}</text>
<rect x="290" y="30" width="644" height="260" rx="14" fill="#0d1117" fill-opacity=".9" stroke="#30363d"/>
<g clip-path="url(#term)"><rect class="scan" x="290" y="0" width="644" height="40" fill="url(#scanline)"/></g>
<circle cx="312" cy="52" r="6" fill="#ff5f57"/><circle cx="332" cy="52" r="6" fill="#febc2e"/><circle cx="352" cy="52" r="6" fill="#28c840"/>
<text x="612" y="56" text-anchor="middle" class="dim">{esc(user)}@github: ~</text>
<line x1="290" y1="70" x2="934" y2="70" stroke="#21262d"/>
{''.join(body)}
</svg>
"""


# ---------------------------------------------------------------- pipeline

def build_pipeline(ci: dict) -> str:
    rows = [p for p in PROJECTS if p["steps"] and ci.get(p["slug"])]
    W, top, rh = 960, 92, 64
    H = top + len(rows) * rh + 34
    x_name, x_steps0, x_steps1 = 40, 300, 650
    cycle = 6.0
    body = []
    for i, p in enumerate(rows):
        run = ci[p["slug"]]
        col, label = ci_look(run)
        y = top + i * rh + 20
        steps = p["steps"]
        n = len(steps)
        xs = [x_steps0 + j * (x_steps1 - x_steps0) / max(n - 1, 1) for j in range(n)]
        offset = i * 0.45
        lang = ICONS[p["lang"]]
        body.append(f'<g class="row" style="animation-delay:{0.15 + i * 0.12:.2f}s">')
        body.append(f'<rect x="20" y="{y - 26}" width="{W - 40}" height="{rh - 10}" rx="12" class="lane"/>')
        body.append(f'<circle cx="{x_name + 6}" cy="{y - 4}" r="5" fill="#{lang["hex"]}"/>')
        body.append(f'<text x="{x_name + 20}" y="{y}" class="nm">{esc(p["name"])}</text>')
        body.append(f'<text x="{x_name + 20}" y="{y + 17}" class="meta">{esc(run["name"])} · {run["sha"]}</text>')
        body.append(f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" class="rail"/>')
        # A light travels along the pipeline, then every node flashes in turn.
        body.append(f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="{col}" stroke-width="2.5" '
                    f'stroke-linecap="round" stroke-dasharray="{xs[-1] - xs[0]:.1f}" stroke-dashoffset="{xs[-1] - xs[0]:.1f}">'
                    f'<animate attributeName="stroke-dashoffset" values="{xs[-1] - xs[0]:.1f};0;0;{xs[-1] - xs[0]:.1f}" '
                    f'keyTimes="0;.55;.9;1" dur="{cycle}s" begin="{offset:.2f}s" repeatCount="indefinite"/></line>')
        body.append(f'<circle r="4" fill="#ffffff" opacity="0"><animateMotion dur="{cycle}s" begin="{offset:.2f}s" '
                    f'repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.55;1" calcMode="linear" '
                    f'path="M{xs[0]},{y} L{xs[-1]},{y}"/><animate attributeName="opacity" values="0;1;1;0;0" '
                    f'keyTimes="0;.05;.5;.56;1" dur="{cycle}s" begin="{offset:.2f}s" repeatCount="indefinite"/></circle>')
        for j, (x, step) in enumerate(zip(xs, steps)):
            hit = 0.55 * j / max(n - 1, 1)
            body.append(f'<circle cx="{x:.1f}" cy="{y}" r="8" class="node"/>'
                        f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{col}" opacity=".35">'
                        f'<animate attributeName="opacity" values=".35;.35;1;1;.35" keyTimes="{kt(0, hit, hit + 0.01, 0.9, 1)}" '
                        f'dur="{cycle}s" begin="{offset:.2f}s" repeatCount="indefinite"/></circle>'
                        f'<text x="{x:.1f}" y="{y + 24}" class="st" text-anchor="middle">{esc(step)}</text>')
        dur = f"{run['seconds'] // 60}m {run['seconds'] % 60:02d}s" if run["seconds"] >= 60 else f"{run['seconds']}s"
        pw = 90
        px = W - 40 - pw
        body.append(f'<rect x="{px}" y="{y - 14}" width="{pw}" height="24" rx="12" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".7"/>'
                    f'<circle cx="{px + 15}" cy="{y - 2}" r="4" fill="{col}"><animate attributeName="opacity" values="1;.3;1" dur="2s" repeatCount="indefinite"/></circle>'
                    f'<text x="{px + 26}" y="{y + 2.5}" class="pill" fill="{col}">{label}</text>'
                    f'<text x="{px - 14}" y="{y + 2.5}" class="meta" text-anchor="end">{dur} · {run["date"]}</text>')
        body.append('</g>')
    return f"""{svg_open(W, H, "Live CI board: the latest main-branch GitHub Actions run of each featured project")}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:14px {MONO}}}
  .nm{{fill:#e6edf3;font:600 14px {SANS}}} .meta{{fill:#6e7681;font:11.5px {MONO}}}
  .st{{fill:#8b949e;font:11px {MONO}}} .pill{{font:600 11.5px {SANS}}}
  .lane{{fill:#161b22;fill-opacity:.55;stroke:#21262d}} .rail{{stroke:#30363d;stroke-width:2.5;stroke-linecap:round}}
  .node{{fill:#0d1117;stroke:#30363d;stroke-width:2}}
  .row{{animation:in .5s ease-out both}} @keyframes in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
</style>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
<text x="34" y="46" class="h"><tspan fill="{VIOLET}">❯</tspan> gh run list --branch main --limit 1 <tspan class="c"># every featured repo, refreshed daily</tspan></text>
<line x1="20" y1="64" x2="{W - 20}" y2="64" stroke="#21262d"/>
{''.join(body)}
</svg>
"""


# ---------------------------------------------------------------- stack

def build_stack(prof: dict) -> str:
    W = 960
    cols, tw, th, gap, x0, y0 = 8, 106, 84, 10, 20, 20
    tiles = []
    for i, slug in enumerate(STACK):
        r, c = divmod(i, cols)
        x, y = x0 + c * (tw + gap), y0 + r * (th + gap)
        tiles.append(f'<g class="tile" style="animation-delay:{i * 0.05:.2f}s">'
                     f'<rect class="tb" x="{x}" y="{y}" width="{tw}" height="{th}" rx="14"/>'
                     f'{icon(slug, x + tw / 2 - 15, y + 15, 30)}'
                     f'<text class="tl" x="{x + tw / 2}" y="{y + 68}" text-anchor="middle">{esc(ICONS[slug]["title"])}</text></g>')
    rows_h = math.ceil(len(STACK) / cols) * (th + gap)
    by = y0 + rows_h + 30
    segs, legend, acc = [], [], 0.0
    bw = W - 2 * x0
    for name, frac, color in prof["languages"]:
        w = bw * frac
        segs.append(f'<rect x="{x0 + acc:.1f}" y="{by}" width="{max(w - 2, 1):.1f}" height="12" fill="{color}"/>')
        acc += w
    lx = x0
    for name, frac, color in prof["languages"]:
        label = f"{name} {frac * 100:.1f}%"
        legend.append(f'<circle cx="{lx + 5}" cy="{by + 37}" r="5" fill="{color}"/>'
                      f'<text class="tl" x="{lx + 15}" y="{by + 41}">{esc(label)}</text>')
        lx += 30 + len(label) * 7.2
    H = by + 62
    return f"""{svg_open(W, H, "Tools I use and the language split of my repositories")}
<style>
  .tb{{fill:#161b22;stroke:#30363d}} .tl{{fill:#9198a1;font:12px {SANS}}} .cap{{fill:#c9d1d9;font:600 13px {SANS}}} .dk{{fill:#e6edf3}}
  .tile{{animation:pop .5s cubic-bezier(.2,.8,.2,1.2) both}}
  @keyframes pop{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
  .bar{{animation:grow 1.2s .6s ease-out both;transform-box:fill-box;transform-origin:left}}
  @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
</style>
<defs><clipPath id="bar"><rect x="{x0}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath></defs>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
{''.join(tiles)}
<text class="cap" x="{x0}" y="{by - 10}">Languages in my own repositories, by bytes</text>
<g clip-path="url(#bar)"><g class="bar">{''.join(segs)}</g></g>
{''.join(legend)}
</svg>
"""



# ---------------------------------------------------------------- cards

def build_card(p: dict, run: dict | None) -> str:
    W, H = 460, 196
    col, label = ci_look(run)
    lines = wrap(p["desc"], 62)[:3]
    desc = "".join(f'<text class="d" x="24" y="{96 + i * 19}">{esc(l)}</text>' for i, l in enumerate(lines))
    chips, x = [], 24
    for slug in p["stack"]:
        title = ICONS[slug]["title"]
        w = 30 + len(title) * 6.6
        chips.append(f'<rect class="chip" x="{x:.1f}" y="156" width="{w:.1f}" height="24" rx="12"/>'
                     f'{icon(slug, x + 8, 162, 12)}<text class="cl" x="{x + 25:.1f}" y="172">{esc(title)}</text>')
        x += w + 6
    lw = 22 + len(f"CI {label}") * 6.4
    pulse = (f'<circle cx="{W - 24 - lw + 11}" cy="38" r="4" fill="none" stroke="{col}">'
             f'<animate attributeName="r" values="4;10" dur="2s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values=".9;0" dur="2s" repeatCount="indefinite"/></circle>'
             if run and run["conclusion"] == "success" else "")
    badge = (f'<rect x="{W - 24 - lw:.1f}" y="26" width="{lw:.1f}" height="24" rx="12" fill="{col}" fill-opacity=".12" '
             f'stroke="{col}" stroke-opacity=".6"/>{pulse}<circle cx="{W - 24 - lw + 11:.1f}" cy="38" r="4" fill="{col}"/>'
             f'<text class="ci" x="{W - 24 - lw + 20:.1f}" y="42" fill="{col}">CI {label}</text>' if run else "")
    status = f" CI {label}." if run else ""
    return f"""{svg_open(W, H, f"{p['name']}: {p['tag']}. {p['desc']}{status}")}
<style>
  .bg{{fill:#0d1117;stroke:#30363d}} .n{{fill:#e6edf3;font:700 17px {SANS}}} .t{{fill:{CYAN};font:600 12.5px {SANS}}}
  .d{{fill:#9198a1;font:13px {SANS}}} .chip{{fill:#161b22;stroke:#30363d}} .cl{{fill:#9198a1;font:11.5px {SANS}}}
  .ar{{fill:#6e7681}} .dk{{fill:#e6edf3}} .ci{{font:600 11px {SANS}}}
  .shine{{animation:sh 5s ease-in-out infinite}} @keyframes sh{{0%,60%{{transform:translateX(-200px)}}100%{{transform:translateX({W + 200}px)}}}}
</style>
<defs>
  <linearGradient id="acc" x1="0" x2="1">
    <stop offset="0" stop-color="{VIOLET}"><animate attributeName="stop-color" values="{VIOLET};{CYAN};{VIOLET}" dur="6s" repeatCount="indefinite"/></stop>
    <stop offset="1" stop-color="{CYAN}"><animate attributeName="stop-color" values="{CYAN};{VIOLET};{CYAN}" dur="6s" repeatCount="indefinite"/></stop>
  </linearGradient>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <clipPath id="cc"><rect width="{W}" height="{H}" rx="14"/></clipPath>
</defs>
<rect class="bg" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/>
<g clip-path="url(#cc)"><rect x="0" y="0" width="{W}" height="4" fill="url(#acc)"/>
<rect class="shine" x="0" y="0" width="140" height="{H}" fill="url(#gl)" transform="skewX(-20)"/></g>
<path class="ar" transform="translate(24,26) scale(1.1)" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>
<text class="n" x="50" y="41">{esc(trunc(p['name'], 26))}</text>
<text class="t" x="24" y="68">{esc(p['tag'])}</text>
{badge}
{desc}
{''.join(chips)}
</svg>
"""


# ---------------------------------------------------------------- heartbeat

def streak(days: list[tuple[str, int]]) -> int:
    run, seq = 0, list(days)
    if seq and seq[-1][1] == 0:  # today may simply not have started yet
        seq = seq[:-1]
    for _, c in reversed(seq):
        if c == 0:
            break
        run += 1
    return run


def build_heartbeat(prof: dict) -> str:
    days = prof["days"][-28:] or [("", 0)]
    W, H = 960, 240
    gx0, gx1, base = 34, 640, 138
    seg = (gx1 - gx0) / len(days)
    peak = max(math.sqrt(c) for _, c in days) or 1
    d = f"M{gx0},{base}"
    for i, (_, c) in enumerate(days):
        x = gx0 + i * seg
        if c == 0:
            d += f" L{x + seg:.1f},{base}"
            continue
        a = 14 + 72 * math.sqrt(c) / peak
        d += (f" L{x + seg * .14:.1f},{base} Q{x + seg * .22:.1f},{base - 5} {x + seg * .3:.1f},{base}"
              f" L{x + seg * .4:.1f},{base + 6} L{x + seg * .5:.1f},{base - a:.1f} L{x + seg * .6:.1f},{base + a * .3:.1f}"
              f" L{x + seg * .68:.1f},{base} Q{x + seg * .8:.1f},{base - 9} {x + seg * .92:.1f},{base} L{x + seg:.1f},{base}")
    week = sum(c for _, c in prof["days"][-7:])
    best = max(prof["days"], key=lambda dc: dc[1]) if prof["days"] else ("", 0)
    best_label = datetime.fromisoformat(best[0]).strftime("%b %d") if best[0] else "-"
    first = datetime.fromisoformat(days[0][0]).strftime("%b %d") if days[0][0] else ""
    sweep, gw = 7, gx1 - gx0
    stats = [("streak", f"{streak(prof['days'])} days"), ("past year", f"{prof['contributions']:,}"),
             ("busiest day", f"{best[1]} · {best_label}")]
    rows = "".join(f'<text x="700" y="{150 + i * 26}" class="k">{k}</text>'
                   f'<text x="926" y="{150 + i * 26}" class="v" text-anchor="end">{esc(v)}</text>'
                   for i, (k, v) in enumerate(stats))
    return f"""{svg_open(W, H, f"Contribution heartbeat: {week} contributions in the last 7 days, {prof['contributions']} in the past year")}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:14px {MONO}}} .ax{{fill:#4b6b57;font:11px {MONO}}}
  .big{{fill:{GREEN};font:700 54px {MONO}}} .unit{{fill:#7ee2a8;font:600 12px {MONO};letter-spacing:1px}}
  .k{{fill:#6e7681;font:12.5px {MONO}}} .v{{fill:#c9d1d9;font:600 12.5px {MONO}}}
</style>
<defs>
  <pattern id="grid" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M12 0H0V12" fill="none" stroke="{GREEN}" stroke-opacity=".07"/></pattern>
  <pattern id="grid5" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0H0V60" fill="none" stroke="{GREEN}" stroke-opacity=".12"/></pattern>
  <filter id="glow" x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <linearGradient id="head" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset="1" stop-color="{GREEN}" stop-opacity=".35"/></linearGradient>
  <clipPath id="sweep"><rect x="{gx0}" y="30" width="0" height="180">
    <animate attributeName="width" values="0;{gw}" dur="{sweep}s" repeatCount="indefinite"/></rect></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="#06110b"/>
<rect x="{gx0 - 14}" y="62" width="{gw + 28}" height="150" fill="url(#grid)"/>
<rect x="{gx0 - 14}" y="62" width="{gw + 28}" height="150" fill="url(#grid5)"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#1d3b29"/>
<text x="34" y="42" class="h"><tspan fill="{GREEN}">❯</tspan> watch --interval 1d contributions <tspan class="c"># last 4 weeks, one beat per day</tspan></text>
<path d="{d}" fill="none" stroke="{GREEN}" stroke-opacity=".18" stroke-width="1.6" stroke-linejoin="round"/>
<path d="{d}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-linejoin="round" clip-path="url(#sweep)" filter="url(#glow)"/>
<rect x="{gx0 - 40}" y="62" width="40" height="150" fill="url(#head)">
  <animate attributeName="x" values="{gx0 - 40};{gx1 - 40}" dur="{sweep}s" repeatCount="indefinite"/></rect>
<text x="{gx0}" y="228" class="ax">{first}</text><text x="{gx1}" y="228" class="ax" text-anchor="end">today</text>
<line x1="676" y1="62" x2="676" y2="212" stroke="#1d3b29"/>
<circle cx="706" cy="73" r="5" fill="{GREEN}"/>
<circle cx="706" cy="73" r="5" fill="none" stroke="{GREEN}" stroke-width="1.5"><animate attributeName="r" values="5;13" dur="1.2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0" dur="1.2s" repeatCount="indefinite"/></circle>
<text x="722" y="78" class="unit">LIVE · CONTRIBUTIONS · 7D</text>
<text x="700" y="124" class="big">{week}</text>
{rows}
</svg>
"""


# ---------------------------------------------------------------- access log

LOG_FILE = ROOT / "data" / "access-log.json"


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"served": 0, "entries": []}


def fmt_rtt(seconds: int) -> str:
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"


def status_color(code: int) -> str:
    return VIOLET if code == 418 else GREEN if code < 300 else AMBER if code < 500 else RED


def build_access_log(log: dict, user: str) -> str:
    rows = log["entries"][-8:][::-1]
    W, top, rh = 960, 96, 32
    H = top + max(len(rows), 2) * rh + 58
    body = []
    if not rows:
        body.append(f'<text x="40" y="{top + 20}" class="row0">no requests yet. Be the first: open an issue titled '
                    f'<tspan fill="{CYAN}">GET /</tspan></text>')
    for i, e in enumerate(rows):
        y = top + i * rh + 16
        col = status_color(e["status"])
        ts = datetime.fromisoformat(e["at"].replace("Z", "+00:00")).strftime("%d/%b %H:%M")
        anim = (f' style="animation:in .7s ease-out both"' if i == 0 else "")
        hl = (f'<rect x="20" y="{y - 21}" width="{W - 40}" height="{rh - 2}" rx="8" fill="{CYAN}" fill-opacity=".07">'
              f'<animate attributeName="fill-opacity" values=".16;.04;.16" dur="3s" repeatCount="indefinite"/></rect>' if i == 0 else "")
        body.append(
            f'<g{anim}>{hl}'
            f'<text x="40" y="{y}" class="r ts">{ts}</text>'
            f'<text x="186" y="{y}" class="r" fill="{CYAN}">@{esc(trunc(e["user"], 16))}</text>'
            f'<text x="330" y="{y}" class="r"><tspan fill="{VIOLET}" font-weight="700">{esc(e["method"])}</tspan> '
            f'<tspan fill="#e6edf3">{esc(trunc(e["path"], 34))}</tspan></text>'
            f'<rect x="{W - 190}" y="{y - 15}" width="46" height="21" rx="10" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".7"/>'
            f'<text x="{W - 167}" y="{y}" class="st" fill="{col}" text-anchor="middle">{e["status"]}</text>'
            f'<text x="{W - 40}" y="{y}" class="ms" text-anchor="end">{fmt_rtt(e["rtt"])}</text></g>')
    yb = top + max(len(rows), 2) * rh + 16
    return f"""{svg_open(W, H, f"Access log of the issue-driven profile API: {log['served']} requests served")}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:14px {MONO}}} .r{{font:13px {MONO}}}
  .ts{{fill:#6e7681}} .st{{font:700 11.5px {MONO}}} .ms{{fill:#8b949e;font:12px {MONO}}} .row0{{fill:#8b949e;font:13px {MONO}}}
  .cnt{{fill:{GREEN};font:600 12px {MONO}}} .hd{{fill:#6e7681;font:600 10.5px {MONO};letter-spacing:1px}}
  @keyframes in{{from{{opacity:0;transform:translateY(-10px)}}to{{opacity:1;transform:none}}}}
  .blink{{animation:b 1.1s steps(1) infinite}} @keyframes b{{50%{{opacity:0}}}}
</style>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
<text x="34" y="44" class="h"><tspan fill="{VIOLET}">❯</tspan> tail -f /var/log/{esc(user)}/access.log</text>
<circle cx="{W - 186}" cy="40" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>
<text x="{W - 40}" y="44" class="cnt" text-anchor="end">{log['served']:,} request{'' if log['served'] == 1 else 's'} served</text>
<line x1="20" y1="64" x2="{W - 20}" y2="64" stroke="#21262d"/>
<text x="40" y="84" class="hd">TIME</text><text x="186" y="84" class="hd">CALLER</text><text x="330" y="84" class="hd">REQUEST</text>
<text x="{W - 167}" y="84" class="hd" text-anchor="middle">STATUS</text><text x="{W - 40}" y="84" class="hd" text-anchor="end">REPLIED IN</text>
{''.join(body)}
<text x="40" y="{yb + 8}" class="r"><tspan fill="{VIOLET}">❯</tspan><tspan class="blink" fill="{CYAN}"> ▌</tspan></text>
</svg>
"""


# ---------------------------------------------------------------- trace

SVC_COLOR = {"github": "#8b949e", "actions": AMBER, "runner": "#58a6ff", "git": "#f78166",
             "python": "#79c0ff", "api": VIOLET, "github.api": CYAN, "log": GREEN}


def fmt_span(seconds: float, coarse: bool) -> str:
    if coarse and seconds < 1:
        return "<1 s"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    return f"{seconds:.1f} s" if seconds < 10 else f"{seconds:.0f} s"


def build_trace(tr: dict) -> str:
    """Waterfall of one profile-API request. Spans: {svc, name, start, end|None, depth, coarse}."""
    spans = tr["spans"]
    total = max(tr["total"], max((s["end"] or 0) for s in spans), 1.0)
    W, X0, X1, top, rh = 960, 330, 860, 112, 30
    H = top + len(spans) * rh + 52
    cycle = 6.0
    tx = lambda t: X0 + (X1 - X0) * min(max(t, 0), total) / total  # noqa: E731
    ticks = "".join(f'<line x1="{tx(total * f):.1f}" y1="{top - 18}" x2="{tx(total * f):.1f}" y2="{H - 46}" class="tk"/>'
                    f'<text x="{tx(total * f):.1f}" y="{top - 24}" class="ax" text-anchor="middle">{fmt_span(total * f, False) if f else "0"}</text>'
                    for f in (0, .25, .5, .75, 1))
    rows = []
    for i, s in enumerate(spans):
        y = top + i * rh
        col = SVC_COLOR.get(s["svc"], GREY)
        a, b = tx(s["start"]), tx(s["end"] if s["end"] is not None else total)
        w = max(b - a, 3)
        appear = s["start"] / total * 0.55
        k = kt(0, appear, appear + 0.08, 0.92, 1)
        indent = 40 + s["depth"] * 16
        tree = (f'<path d="M{indent - 10},{y - 22} V{y - 4} H{indent - 3}" class="tree"/>' if s["depth"] else "")
        if s["end"] is None:
            bar = (f'<rect x="{a:.1f}" y="{y - 13}" width="{w:.1f}" height="14" rx="3" fill="url(#flight)" stroke="{col}" stroke-width="1">'
                   f'<animate attributeName="width" values="0;0;{w:.1f};{w:.1f};0" keyTimes="{k}" dur="{cycle}s" repeatCount="indefinite"/></rect>')
            label = "in flight"
        elif s["end"] == s["start"] and s["svc"] == "github":
            bar = (f'<path d="M{a:.1f},{y - 13} l7,7 l-7,7 l-7,-7 Z" fill="{col}">'
                   f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="{k}" dur="{cycle}s" repeatCount="indefinite"/></path>')
            label = "event"
        else:
            bar = (f'<rect x="{a:.1f}" y="{y - 13}" width="{w:.1f}" height="14" rx="3" fill="{col}" fill-opacity=".85">'
                   f'<animate attributeName="width" values="0;0;{w:.1f};{w:.1f};0" keyTimes="{k}" dur="{cycle}s" repeatCount="indefinite"/></rect>')
            label = fmt_span(s["end"] - s["start"], s.get("coarse", False))
        lx = min(a + w + 8, W - 40)
        anchor = "start" if a + w + 8 < W - 90 else "end"
        lx = lx if anchor == "start" else a - 8
        rows.append(f'<rect x="20" y="{y - 20}" width="{W - 40}" height="{rh - 2}" rx="6" class="{"z" if i % 2 else "zz"}"/>'
                    f'{tree}<circle cx="{indent + 4}" cy="{y - 6}" r="4" fill="{col}"/>'
                    f'<text x="{indent + 14}" y="{y - 2}" class="sv" fill="{col}">{esc(s["svc"])}</text>'
                    f'<text x="{indent + 14 + 7.4 * (len(s["svc"]) + 1)}" y="{y - 2}" class="nm">{esc(s["name"])}</text>'
                    f'{bar}<text x="{lx:.1f}" y="{y - 2}" class="du" text-anchor="{anchor}">{esc(label)}</text>')
    when = datetime.fromisoformat(tr["at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    return f"""{svg_open(W, H, f"Distributed trace of the latest profile API request, {tr['request']}: {len(spans)} spans")}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:13px {MONO}}} .ax{{fill:#6e7681;font:10.5px {MONO}}}
  .tk{{stroke:#21262d;stroke-dasharray:2 4}} .sv{{font:600 12px {MONO}}} .nm{{fill:#c9d1d9;font:12px {MONO}}}
  .du{{fill:#8b949e;font:11px {MONO}}} .z{{fill:#161b22;fill-opacity:.35}} .zz{{fill:none}}
  .tree{{fill:none;stroke:#30363d;stroke-width:1.2}} .ft{{fill:#6e7681;font:11px {MONO}}}
  .id{{fill:{CYAN};font:600 12px {MONO}}}
</style>
<defs>
  <pattern id="flight" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="10" height="10" fill="{GREEN}" fill-opacity=".18"/><rect width="4" height="10" fill="{GREEN}" fill-opacity=".55"/>
    <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="10 0" dur=".8s" additive="sum" repeatCount="indefinite"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
<text x="34" y="44" class="h"><tspan fill="{VIOLET}">❯</tspan> trace <tspan class="id">{tr['trace_id'][:16]}</tspan> <tspan fill="#e6edf3">{esc(trunc(tr['request'], 40))}</tspan></text>
<text x="{W - 34}" y="44" class="c" text-anchor="end">@{esc(trunc(tr['caller'], 18))} · {when}</text>
<line x1="20" y1="62" x2="{W - 20}" y2="62" stroke="#21262d"/>
{ticks}
<line x1="{X0}" y1="{top - 18}" x2="{X0}" y2="{H - 46}" stroke="{CYAN}" stroke-opacity=".7" stroke-width="1.5">
  <animate attributeName="x1" values="{X0};{X0};{X1};{X1}" keyTimes="0;.02;.6;1" dur="{cycle}s" repeatCount="indefinite"/>
  <animate attributeName="x2" values="{X0};{X0};{X1};{X1}" keyTimes="0;.02;.6;1" dur="{cycle}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.02;.6;.66;1" dur="{cycle}s" repeatCount="indefinite"/></line>
{''.join(rows)}
<text x="34" y="{H - 20}" class="ft">{len(spans)} spans · Actions steps at 1 s resolution, handler spans timed in-process · the striped span is the commit that published this image</text>
</svg>
"""


# ---------------------------------------------------------------- divider

def build_divider() -> str:
    W, H, y = 960, 28, 14
    nodes = "".join(f'<circle cx="{x}" cy="{y}" r="2.5" fill="#30363d"/>' for x in range(60, W - 40, 120))
    return f"""{svg_open(W, H, "")}
<defs><linearGradient id="pk" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="#30363d" stop-opacity="0"/><stop offset=".5" stop-color="#30363d"/><stop offset="1" stop-color="#30363d" stop-opacity="0"/></linearGradient></defs>
<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="url(#ln)" stroke-width="1.5"/>
{nodes}
<rect y="{y - 1.5}" width="90" height="3" rx="1.5" fill="url(#pk)"><animate attributeName="x" values="-90;{W}" dur="4.5s" repeatCount="indefinite"/></rect>
<rect y="{y - 1.5}" width="50" height="3" rx="1.5" fill="url(#pk)" opacity=".5"><animate attributeName="x" values="-50;{W}" dur="7s" begin="-3s" repeatCount="indefinite"/></rect>
</svg>
"""


# ---------------------------------------------------------------- section headings

HEADINGS = [
    ("api", "0x01", "this profile is an api", "call it from the issues tab"),
    ("work", "0x02", "what i'm building", "six backends, each with one hard problem"),
    ("ci", "0x03", "pipelines", "latest main-branch run, every repo"),
    ("vitals", "0x04", "vital signs", "contributions as a monitor trace"),
    ("rules", "0x05", "how i build", "invariants over features"),
    ("tools", "0x06", "toolbox", "what the above is made of"),
]


def build_heading(code: str, title: str, sub: str) -> str:
    W, H = 960, 70
    cw = 13.6
    tw = len(title) * cw + 4
    t0, t1 = 0.25, 0.25 + len(title) * 0.035
    T = t1 + 0.4
    return f"""{svg_open(W, H, f"{code} {title}: {sub}")}
<style>
  .code{{fill:{VIOLET};font:700 15px {MONO}}} .t{{fill:#e6edf3;font:700 22px {MONO}}} .s{{fill:#6e7681;font:13px {MONO}}}
  .sl{{fill:#30363d;font:700 22px {MONO}}}
</style>
<defs>
  <clipPath id="ty"><rect x="96" y="10" width="{tw:.1f}" height="40">
    <animate attributeName="width" values="0;0;{tw:.1f};{tw:.1f}" keyTimes="{kt(0, t0 / T, t1 / T, 1)}" dur="{T:.2f}s" fill="freeze"/></rect></clipPath>
  <linearGradient id="ul" x1="0" x2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  <linearGradient id="pk" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="14" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="#30363d"/>
<text x="20" y="38" class="code">{code}</text>
<text x="74" y="39" class="sl">/</text>
<text x="96" y="39" class="t" clip-path="url(#ty)">{esc(title)}</text>
<rect x="{96 + tw:.1f}" y="21" width="11" height="22" fill="{CYAN}" opacity="0">
  <animate attributeName="opacity" values="0;0;1" keyTimes="{kt(0, t1 / T, t1 / T)}" dur="{T:.2f}s" fill="freeze"/>
  <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" begin="{T:.2f}s" repeatCount="indefinite"/></rect>
<text x="{W - 20}" y="38" class="s" text-anchor="end">// {esc(sub)}</text>
<rect x="20" y="56" width="{W - 40}" height="1" fill="#21262d"/>
<rect x="20" y="55" width="{W * 0.42:.0f}" height="3" rx="1.5" fill="url(#ul)">
  <animate attributeName="width" values="0;{W * 0.42:.0f}" dur="1.2s" begin=".2s" fill="freeze"/></rect>
<rect y="55.5" width="60" height="2" rx="1" fill="url(#pk)"><animate attributeName="x" values="-60;{W}" dur="5s" begin="1.4s" repeatCount="indefinite"/></rect>
</svg>
"""


# ---------------------------------------------------------------- principles

PRINCIPLES = [
    ("money", "is stored as integer minor units, never floats", "ledgerline, bank-management-system"),
    ("concurrency", "claims a revision or rolls back; no lost updates", "aftermark, ledgerline"),
    ("approvals", "need someone other than the author", "aftermark, ledgerline"),
    ("history", "is append-only and hash-linked, so tampering shows", "ledgerline, aftermark"),
    ("uncertainty", "is reported as 'needs review', never guessed away", "Pactrail, tracebench"),
    ("shipping", "means typecheck, test, build and audit on every push", "every featured repo"),
]


def build_principles() -> str:
    W, lh, top = 960, 30, 128
    n = len(PRINCIPLES)
    H = top + n * lh + 90
    step, start = 0.42, 0.9
    T = start + n * step + 1.6
    rows = []
    for i, (key, rule, where) in enumerate(PRINCIPLES):
        y = top + i * lh
        a = start + i * step
        spin = (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" '
                f'keyTimes="{kt(0, (a - step) / T, (a - step) / T, a / T, a / T, 1)}" dur="{T:.2f}s" fill="freeze"/>'
                f'<circle cx="48" cy="{y - 5}" r="5.5" fill="none" stroke="{AMBER}" stroke-width="2" stroke-dasharray="20 15">'
                f'<animateTransform attributeName="transform" type="rotate" from="0 48 {y - 5}" to="360 48 {y - 5}" dur=".6s" repeatCount="indefinite"/></circle></g>')
        rows.append(
            f'{spin}<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt(0, a / T, a / T + 0.01, 1)}" dur="{T:.2f}s" fill="freeze"/>'
            f'<path d="M43,{y - 5} l3.5,3.5 l6.5,-7" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<text x="66" y="{y}" class="m"><tspan fill="{CYAN}">{esc(key)}</tspan> <tspan fill="#c9d1d9">{esc(rule)}</tspan></text>'
            f'<text x="{W - 40}" y="{y}" class="ms" text-anchor="end">{esc(where)}</text></g>')
    ys = top + n * lh + 18
    done = (start + n * step) / T
    bar_w = W - 80
    return f"""{svg_open(W, H, "How I build, as a passing test suite: " + "; ".join(f"{k} {r}" for k, r, _ in PRINCIPLES))}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:13px {MONO}}} .m{{font:13.5px {MONO}}}
  .ms{{fill:#6e7681;font:12px {MONO}}} .file{{fill:#e6edf3;font:600 13px {MONO}}}
  .sum{{font:600 13px {MONO}}} .pass{{fill:#0d1117;font:700 12px {MONO}}}
  .hd{{fill:#6e7681;font:600 10.5px {MONO};letter-spacing:1px}}
</style>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
<text x="34" y="44" class="h"><tspan fill="{VIOLET}">$</tspan> npx vitest run principles.spec.ts</text>
<line x1="20" y1="62" x2="{W - 20}" y2="62" stroke="#21262d"/>
<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt(0, 0.5 / T, 0.5 / T + 0.01, 1)}" dur="{T:.2f}s" fill="freeze"/>
<rect x="34" y="{top - 46}" width="44" height="20" rx="4" fill="{GREEN}"/><text x="56" y="{top - 32}" class="pass" text-anchor="middle">PASS</text>
<text x="88" y="{top - 32}" class="file">principles.spec.ts <tspan class="c">› how I build</tspan></text>
<text x="{W - 40}" y="{top - 32}" class="hd" text-anchor="end">ENFORCED IN</text></g>
{''.join(rows)}
<rect x="40" y="{ys}" width="{bar_w}" height="4" rx="2" fill="#21262d"/>
<rect x="40" y="{ys}" width="{bar_w}" height="4" rx="2" fill="{GREEN}">
  <animate attributeName="width" values="0;0;{bar_w};{bar_w}" keyTimes="{kt(0, start / T, done, 1)}" dur="{T:.2f}s" fill="freeze"/></rect>
<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt(0, done, done + 0.01, 1)}" dur="{T:.2f}s" fill="freeze"/>
<text xml:space="preserve" x="40" y="{ys + 34}" class="sum"><tspan fill="#6e7681">Tests  </tspan><tspan fill="{GREEN}">{n} passed</tspan><tspan fill="#6e7681"> ({n})   ·   Invariants broken  </tspan><tspan fill="{GREEN}">0</tspan></text>
<text x="{W - 40}" y="{ys + 34}" class="ms" text-anchor="end">exit 0</text></g>
</svg>
"""


# ---------------------------------------------------------------- footer

def build_footer(user: str) -> str:
    W, H = 960, 120
    waves = []
    for i, (c, o, d) in enumerate([(VIOLET, .35, 9), (CYAN, .25, 13), (GREEN, .15, 17)]):
        amp, base = 10 + i * 4, 70 + i * 8
        path = f"M0,{base} " + " ".join(f"Q{x + 60},{base - amp if (x // 120) % 2 == 0 else base + amp} {x + 120},{base}"
                                        for x in range(0, 2 * W, 120)) + f" L{2 * W},{H} L0,{H} Z"
        waves.append(f'<path d="{path}" fill="{c}" fill-opacity="{o}"><animateTransform attributeName="transform" '
                     f'type="translate" from="0 0" to="{-240} 0" dur="{d}s" repeatCount="indefinite"/></path>')
    return f"""{svg_open(W, H, "Thanks for visiting")}
<style>.f{{fill:#c9d1d9;font:600 15px {MONO}}} .s{{fill:#6e7681;font:12px {MONO}}}
.blink{{animation:b 1.1s steps(1) infinite}} @keyframes b{{50%{{opacity:0}}}}</style>
<defs><clipPath id="fc"><rect width="{W}" height="{H}" rx="20"/></clipPath></defs>
<g clip-path="url(#fc)"><rect width="{W}" height="{H}" fill="#0d1117"/>{''.join(waves)}</g>
<text x="{W / 2}" y="44" text-anchor="middle" class="f"><tspan fill="{VIOLET}">❯</tspan> exit 0 <tspan class="s">— thanks for stopping by</tspan><tspan class="blink" fill="{CYAN}"> ▌</tspan></text>
</svg>
"""


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("PROFILE_USER", "devnishantt"))
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 1

    prof = fetch_profile(token, args.user)
    ci = {p["slug"]: fetch_ci(token, args.user, p["repo"]) for p in PROJECTS}

    local = ASSETS / "avatar-embed.jpg"
    avatar = data_uri(local.read_bytes()) if local.exists() else fetch_image(f"https://github.com/{args.user}.png?size=200")

    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "hero.svg").write_text(build_hero(prof, ci, args.user, avatar), encoding="utf-8")
    (ASSETS / "pipeline.svg").write_text(build_pipeline(ci), encoding="utf-8")
    (ASSETS / "stack.svg").write_text(build_stack(prof), encoding="utf-8")
    (ASSETS / "footer.svg").write_text(build_footer(args.user), encoding="utf-8")
    (ASSETS / "heartbeat.svg").write_text(build_heartbeat(prof), encoding="utf-8")
    (ASSETS / "divider.svg").write_text(build_divider(), encoding="utf-8")
    (ASSETS / "principles.svg").write_text(build_principles(), encoding="utf-8")
    trace_file = ROOT / "data" / "last-trace.json"
    if trace_file.exists():  # the API writes the trace; the daily job only re-renders it
        (ASSETS / "trace.svg").write_text(build_trace(json.loads(trace_file.read_text(encoding="utf-8"))), encoding="utf-8")
    for slug, code, title, sub in HEADINGS:
        (ASSETS / f"h-{slug}.svg").write_text(build_heading(code, title, sub), encoding="utf-8")
    (ASSETS / "access-log.svg").write_text(build_access_log(load_log(), args.user), encoding="utf-8")
    for p in PROJECTS:
        (ASSETS / f"card-{p['slug']}.svg").write_text(build_card(p, ci[p["slug"]]), encoding="utf-8")
    passing = sum(1 for r in ci.values() if r and r["conclusion"] == "success")
    print(f"{len(prof['repos'])} public repositories, {passing}/{sum(1 for r in ci.values() if r)} pipelines green, "
          f"rendered {datetime.now(timezone.utc):%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
