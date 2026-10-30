#!/usr/bin/env python3
"""Generate the profile README graphics and pull-request table from live GitHub data.

Writes, all self-contained (images embedded, no third-party services):
  assets/hero.svg      animated terminal intro with live PR numbers
  assets/orbit.svg     every project I contribute to, orbiting at a size set by its stars
  assets/journey.svg   my pull requests drawn as a git graph, oldest first
  assets/stack.svg     tools I use, plus the language split of my own repositories
  assets/card-*.svg    project cards
and the README block between <!-- oss:start --> and <!-- oss:end -->.

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
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
README = ROOT / "README.md"
ICONS = json.loads((ROOT / "scripts" / "icons.json").read_text())
START, END = "<!-- oss:start -->", "<!-- oss:end -->"

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
VIOLET, CYAN, GREEN, GREY = "#a371f7", "#39d0d8", "#3fb950", "#8b949e"
STATE_COLOR = {"MERGED": VIOLET, "OPEN": GREEN, "CLOSED": GREY}
STATE_LABEL = {"MERGED": "merged", "OPEN": "in review", "CLOSED": "closed"}

STACK = ["typescript", "javascript", "nodedotjs", "express", "prisma", "postgresql", "mysql", "mongodb",
         "redis", "zod", "sequelize", "python", "dart", "flutter", "git", "github"]

CARDS = [
    {"slug": "bank", "name": "bank-management-system", "url": "https://github.com/devnishantt/bank-management-system",
     "desc": "Banking API with a double-entry ledger, row-locked transfers that cannot deadlock, "
             "Idempotency-Key retries and rotating refresh tokens.",
     "stack": ["typescript", "express", "prisma", "postgresql", "zod"]},
    {"slug": "hospital", "name": "Hospital-Management", "url": "https://github.com/devnishantt/Hospital-Management",
     "desc": "Hospital management API: JWT access and refresh tokens with rotation, a Redis-backed token "
             "blacklist, rate limiting, file uploads and email.",
     "stack": ["typescript", "express", "prisma", "postgresql", "redis"]},
    {"slug": "flights", "name": "Flight booking microservices", "url": "https://github.com/devnishantt/API-Gateway-Flights",
     "desc": "API gateway, auth, flight and booking services. Bookings check seats with the flight service, "
             "and a cron job cancels stale bookings.",
     "stack": ["nodedotjs", "express", "sequelize", "mysql"]},
    {"slug": "twitter", "name": "TwitterClone", "url": "https://github.com/devnishantt/TwitterClone",
     "desc": "Microblogging API with cookie-based JWT auth, Zod validation and rotating log files.",
     "stack": ["typescript", "express", "prisma", "postgresql", "zod"]},
    {"slug": "teacode", "name": "Tea-Code-Problem-Service", "url": "https://github.com/devnishantt/Tea-Code-Problem-Service",
     "desc": "Problem service for a coding judge. Problems are written in Markdown and sanitized before "
             "they are stored.",
     "stack": ["nodedotjs", "express", "mongodb"]},
]

PR_QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      number title url state createdAt
      repository { nameWithOwner url stargazerCount owner { login } primaryLanguage { name } }
    } }
  }
}"""

PROFILE_QUERY = """
query($login: String!) { user(login: $login) {
  createdAt
  contributionsCollection { contributionCalendar { totalContributions } }
  repositories(ownerAffiliations: OWNER, isFork: false, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
    nodes { name languages(first: 10) { edges { size node { name color } } } }
  }
} }"""


# ---------------------------------------------------------------- data

def gql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-builder"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def fetch_prs(token: str, user: str) -> list[dict]:
    prs, cursor = [], None
    while True:
        data = gql(token, PR_QUERY, {"q": f"author:{user} is:pr", "cursor": cursor})["search"]
        for n in data["nodes"]:
            if not n or n["repository"]["owner"]["login"].lower() == user.lower():
                continue
            r = n["repository"]
            prs.append({"repo": r["nameWithOwner"], "repo_url": r["url"], "owner": r["owner"]["login"],
                        "stars": r["stargazerCount"], "number": n["number"], "title": n["title"],
                        "url": n["url"], "state": n["state"], "created": n["createdAt"]})
        if not data["pageInfo"]["hasNextPage"]:
            return sorted(prs, key=lambda p: p["created"])
        cursor = data["pageInfo"]["endCursor"]


def fetch_profile(token: str, user: str) -> dict:
    u = gql(token, PROFILE_QUERY, {"login": user})["user"]
    # The profile repository itself is not a project.
    repos = [r for r in u["repositories"]["nodes"] if r["name"].lower() != user.lower()]
    langs: dict[str, list] = {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            entry = langs.setdefault(e["node"]["name"], [0, e["node"]["color"] or GREY])
            entry[0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])
    return {"since": u["createdAt"][:4], "repos": [r["name"] for r in repos],
            "contributions": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
            "languages": [(name, size / total, color) for name, (size, color) in top if size / total >= 0.005]}


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


def summarize(prs: list[dict]) -> dict:
    live = [p for p in prs if p["state"] != "CLOSED"]
    projects: dict[str, dict] = {}
    for p in live:
        pr = projects.setdefault(p["repo"], {"repo": p["repo"], "owner": p["owner"], "stars": p["stars"],
                                              "url": p["repo_url"], "merged": 0, "open": 0})
        pr["merged" if p["state"] == "MERGED" else "open"] += 1
    ordered = sorted(projects.values(), key=lambda r: (-(r["merged"] > 0), -r["stars"]))
    return {"merged": sum(p["state"] == "MERGED" for p in prs), "open": sum(p["state"] == "OPEN" for p in prs),
            "projects": ordered, "reach": sum(r["stars"] for r in ordered)}


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

def build_hero(st: dict, prof: dict, user: str, avatar: str | None) -> str:
    W, H, fs, lh, x0, y0 = 960, 300, 14, 26, 314, 98
    cw = fs * 0.62
    listing = ""
    for name in prof["repos"]:
        candidate = f"{listing}  {name}".strip()
        if len(candidate) > 62:
            listing += "  …"
            break
        listing = candidate
    lines = [
        ("cmd", "whoami"),
        ("out", [("Nishant", "name"), (" · backend developer · TypeScript & Node.js", "txt")]),
        ("cmd", "ls ~/projects"),
        ("out", [(listing, "cy")]),
        ("cmd", "cat stats.txt"),
        ("out", [("● ", "mg"), (f"{len(prof['repos'])} repositories   ", "txt"), ("● ", "op"),
                 (f"{prof['contributions']} contributions in the past year", "txt")]),
    ]
    t, timing = 0.6, []
    for kind, content in lines:
        if kind == "cmd":
            end = t + len(content) * 0.055
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
            body.append(f'<text class="m" x="{x0}" y="{y}" clip-path="url(#c{i})"><tspan class="pr">$ </tspan>'
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
            body.append(f'<text class="m" x="{x0}" y="{y}">{spans}'
                        f'<animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt(0, a / T, a / T + 0.01, 1)}" '
                        f'dur="{T:.2f}s" fill="freeze"/></text>')
    yf = y0 + len(lines) * lh
    body.append(f'<text class="m" x="{x0}" y="{yf}"><tspan class="pr">$ </tspan>'
                f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt(0, final / T, final / T)}" '
                f'dur="{T:.2f}s" fill="freeze"/></text>')
    body.append(f'<rect class="cur" x="{x0 + 2 * cw:.1f}" y="{yf - 13}" width="8" height="16">'
                f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt(0, final / T, final / T)}" '
                f'dur="{T:.2f}s" fill="freeze"/>'
                f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" '
                f'begin="{final:.2f}s" repeatCount="indefinite"/></rect>')

    acx, acy, ar = 160, 142, 88
    face = (f'<image href="{avatar}" x="{acx - ar}" y="{acy - ar}" width="{2 * ar}" height="{2 * ar}" '
            f'clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>' if avatar else
            f'<text x="{acx}" y="{acy + 22}" text-anchor="middle" class="mono-big">N</text>')
    return f"""{svg_open(W, H, f"Terminal intro for {user}: backend developer, {len(prof['repos'])} repositories")}
<style>
  .m{{font:{fs}px {MONO};white-space:pre}} .pr{{fill:{VIOLET};font-weight:700}} .cmd{{fill:#e6edf3}}
  .txt{{fill:#c9d1d9}} .name{{fill:{CYAN};font-weight:700}} .mg{{fill:{VIOLET}}} .op{{fill:{GREEN}}}
  .cy{{fill:{CYAN}}} .yl{{fill:#e3b341}} .cur{{fill:{CYAN}}} .dim{{fill:#6e7681;font:12px {MONO}}}
  .handle{{fill:#c9d1d9;font:600 14px {MONO}}} .mono-big{{fill:#e6edf3;font:700 64px {SANS}}}
</style>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#150b2e"/></linearGradient>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".55"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#ffffff" opacity=".06"/></pattern>
  <clipPath id="av"><circle cx="{acx}" cy="{acy}" r="{ar}"/></clipPath>
  {''.join(defs)}
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<rect width="{W}" height="{H}" rx="20" fill="url(#dots)"/>
<circle cx="{acx}" cy="{acy}" r="128" fill="url(#glow)"><animate attributeName="r" values="118;134;118" dur="5s" repeatCount="indefinite"/></circle>
{face}
<circle cx="{acx}" cy="{acy}" r="{ar + 9}" fill="none" stroke="url(#ring)" stroke-width="3" stroke-linecap="round" stroke-dasharray="70 26 14 26">
  <animateTransform attributeName="transform" type="rotate" from="0 {acx} {acy}" to="360 {acx} {acy}" dur="16s" repeatCount="indefinite"/></circle>
<circle cx="{acx}" cy="{acy}" r="{ar + 18}" fill="none" stroke="{CYAN}" stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 7">
  <animateTransform attributeName="transform" type="rotate" from="360 {acx} {acy}" to="0 {acx} {acy}" dur="40s" repeatCount="indefinite"/></circle>
<circle cx="{acx + 62}" cy="{acy + 64}" r="9" fill="{GREEN}" stroke="#0b1020" stroke-width="4"/>
<circle cx="{acx + 62}" cy="{acy + 64}" r="9" fill="none" stroke="{GREEN}" stroke-width="2">
  <animate attributeName="r" values="9;20" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0" dur="2s" repeatCount="indefinite"/></circle>
<text x="{acx}" y="270" text-anchor="middle" class="handle">@{esc(user)}</text>
<rect x="290" y="30" width="644" height="240" rx="14" fill="#0d1117" fill-opacity=".88" stroke="#30363d"/>
<circle cx="312" cy="52" r="6" fill="#ff5f57"/><circle cx="332" cy="52" r="6" fill="#febc2e"/><circle cx="352" cy="52" r="6" fill="#28c840"/>
<text x="612" y="56" text-anchor="middle" class="dim">{esc(user)}@github: ~</text>
<line x1="290" y1="70" x2="934" y2="70" stroke="#21262d"/>
{''.join(body)}
</svg>
"""


# ---------------------------------------------------------------- orbit

def build_orbit(st: dict, sun: str | None, avatars: dict[str, str | None]) -> str:
    W, H, cx, cy = 960, 450, 300, 228
    projects = st["projects"][:11]
    n = len(projects)
    planets, rings, legend = [], [], []
    for i, p in enumerate(projects):
        rx = 84 + i * (262 - 84) / max(n - 1, 1)
        ry = rx * 0.40
        period = 16 * (rx / 84) ** 1.5
        phase = ((i * 0.618) % 1) * period
        r = 8 + 3.0 * math.log10(p["stars"] + 1)
        col = VIOLET if p["merged"] else GREEN
        path = f"M{cx - rx:.1f},{cy} a{rx:.1f},{ry:.1f} 0 1,1 {2 * rx:.1f},0 a{rx:.1f},{ry:.1f} 0 1,1 {-2 * rx:.1f},0"
        rings.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="{col}" '
                     f'stroke-opacity=".22" stroke-width="1" stroke-dasharray="3 6"/>')
        uri = avatars.get(p["owner"])
        face = (f'<image href="{uri}" x="{-r:.1f}" y="{-r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" clip-path="url(#pc)"/>'
                if uri else f'<text y="{r * 0.35:.1f}" text-anchor="middle" class="mono">{esc(p["owner"][:1].upper())}</text>')
        halo = (f'<circle r="{r + 3}" fill="none" stroke="{col}" stroke-width="1.5"><animate attributeName="r" '
                f'values="{r + 3:.1f};{r + 12:.1f}" dur="2.4s" repeatCount="indefinite"/><animate attributeName="opacity" '
                f'values=".7;0" dur="2.4s" repeatCount="indefinite"/></circle>' if p["merged"] else "")
        planets.append(f'<g>{halo}<circle r="{r + 2.5:.1f}" fill="#0d1117" stroke="{col}" stroke-width="2"/>{face}'
                       f'<animateMotion dur="{period:.1f}s" begin="-{phase:.1f}s" repeatCount="indefinite" path="{path}"/></g>')
        ly = 108 + i * 29
        d = 0.25 + i * 0.12
        luri = avatars.get(p["owner"])
        mini = (f'<image href="{luri}" x="618" y="{ly - 13}" width="18" height="18" clip-path="url(#pc)"/>' if luri
                else f'<circle cx="627" cy="{ly - 4}" r="9" fill="#21262d"/>')
        legend.append(f'<g class="row" style="animation-delay:{d:.2f}s"><circle cx="606" cy="{ly - 4}" r="4" fill="{col}"/>{mini}'
                      f'<text x="646" y="{ly}" class="lg">{esc(trunc(p["repo"], 29))}</text>'
                      f'<text x="928" y="{ly}" class="st" text-anchor="end">★ {human(p["stars"])}</text></g>')
    more = len(st["projects"]) - n
    if more > 0:
        legend.append(f'<text x="606" y="{108 + n * 29}" class="st">+{more} more</text>')
    sun_face = (f'<image href="{sun}" x="{cx - 34}" y="{cy - 34}" width="68" height="68" clip-path="url(#pc)"/>' if sun else "")
    return f"""{svg_open(W, H, "Projects I contribute to, orbiting by star count")}
<style>
  .t{{fill:#e6edf3;font:700 18px {SANS}}} .s{{fill:#8b949e;font:13px {SANS}}} .lg{{fill:#c9d1d9;font:13px {MONO}}}
  .st{{fill:#8b949e;font:12px {MONO}}} .mono{{fill:#e6edf3;font:700 12px {SANS}}}
  .row{{animation:in .6s ease-out both}} @keyframes in{{from{{opacity:0;transform:translateX(12px)}}to{{opacity:1;transform:none}}}}
</style>
<defs>
  <radialGradient id="sky" cx=".3" cy=".5" r=".9"><stop offset="0" stop-color="#1a1240"/><stop offset=".55" stop-color="#0b1020"/><stop offset="1" stop-color="#05070f"/></radialGradient>
  <radialGradient id="sunglow"><stop offset="0" stop-color="{CYAN}" stop-opacity=".55"/><stop offset=".45" stop-color="{VIOLET}" stop-opacity=".25"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <clipPath id="pc" clipPathUnits="objectBoundingBox"><circle cx=".5" cy=".5" r=".5"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#sky)"/>
{starfield(W, H, 110, 7)}
<g transform="rotate(-8 {cx} {cy})">{''.join(rings)}</g>
<circle cx="{cx}" cy="{cy}" r="78" fill="url(#sunglow)"><animate attributeName="r" values="70;88;70" dur="6s" repeatCount="indefinite"/></circle>
<circle cx="{cx}" cy="{cy}" r="37" fill="#0d1117" stroke="url(#sunglow)" stroke-width="2"/>
{sun_face}
<g transform="rotate(-8 {cx} {cy})">{''.join(planets)}</g>
<line x1="580" y1="34" x2="580" y2="{H - 34}" stroke="#30363d"/>
<text x="606" y="58" class="t">Projects I contribute to</text>
<text x="606" y="80" class="s"><tspan fill="{VIOLET}">●</tspan> merged    <tspan fill="{GREEN}">●</tspan> in review    · planet size = stars</text>
{''.join(legend)}
</svg>
"""


# ---------------------------------------------------------------- journey

def build_journey(prs: list[dict]) -> str:
    W, row, top = 960, 46, 84
    H = top + max(len(prs), 1) * row + 26
    mx = 54
    rows = []
    for i, p in enumerate(prs):
        y = top + i * row + 10
        col = STATE_COLOR[p["state"]]
        d = 0.35 + i * 0.12
        out = f'<path d="M{mx},{y - 22} C{mx},{y - 6} {mx + 12},{y} {mx + 40},{y} L{mx + 62},{y}" class="br" stroke="{col}"/>'
        back = (f'<path d="M{mx + 62},{y} C{mx + 86},{y} {mx + 86},{y + 26} {mx},{y + 30}" class="br" stroke="{col}" '
                f'stroke-dasharray="0"/>' if p["state"] == "MERGED" else "")
        if p["state"] == "OPEN":
            dot = (f'<circle cx="{mx + 62}" cy="{y}" r="6" fill="{col}"/><circle cx="{mx + 62}" cy="{y}" r="6" fill="none" '
                   f'stroke="{col}"><animate attributeName="r" values="6;14" dur="2s" repeatCount="indefinite"/>'
                   f'<animate attributeName="opacity" values=".8;0" dur="2s" repeatCount="indefinite"/></circle>')
        elif p["state"] == "MERGED":
            dot = f'<circle cx="{mx + 62}" cy="{y}" r="6.5" fill="#0d1117" stroke="{col}" stroke-width="3"/>'
        else:
            dot = f'<circle cx="{mx + 62}" cy="{y}" r="6" fill="#0d1117" stroke="{col}" stroke-width="2"/>'
        date = datetime.fromisoformat(p["created"].replace("Z", "+00:00")).strftime("%b %d")
        label = STATE_LABEL[p["state"]]
        pw = 14 + len(label) * 7
        rows.append(
            f'<g class="row" style="animation-delay:{d:.2f}s">{out}{back}{dot}'
            f'<text x="{mx + 84}" y="{y - 3}" class="repo"><tspan fill="{col}">{esc(p["repo"])}</tspan>'
            f'<tspan class="num"> #{p["number"]}</tspan></text>'
            f'<text x="{mx + 84}" y="{y + 15}" class="ttl">{esc(trunc(p["title"], 92))}</text>'
            f'<text x="{W - 40 - pw - 10}" y="{y + 4}" class="date" text-anchor="end">{date}</text>'
            f'<rect x="{W - 40 - pw}" y="{y - 10}" width="{pw}" height="20" rx="10" fill="{col}" fill-opacity=".15" stroke="{col}" stroke-opacity=".6"/>'
            f'<text x="{W - 40 - pw / 2}" y="{y + 4}" class="pill" text-anchor="middle" fill="{col}">{label}</text></g>')
    main_len = H - 70
    return f"""{svg_open(W, H, "My open-source pull requests drawn as a git graph")}
<style>
  .h{{fill:#e6edf3;font:600 14px {MONO}}} .c{{fill:#6e7681;font:14px {MONO}}}
  .repo{{font:600 14px {SANS}}} .num{{fill:#8b949e;font-weight:400}} .ttl{{fill:#8b949e;font:12.5px {SANS}}}
  .date{{fill:#6e7681;font:12px {MONO}}} .pill{{font:600 11px {SANS}}}
  .br{{fill:none;stroke-width:2.2;stroke-linecap:round}}
  .row{{animation:in .5s ease-out both}} @keyframes in{{from{{opacity:0;transform:translateX(-10px)}}to{{opacity:1;transform:none}}}}
  .trunk{{stroke-dasharray:{main_len};stroke-dashoffset:{main_len};animation:draw 1.4s ease-out forwards}}
  @keyframes draw{{to{{stroke-dashoffset:0}}}}
</style>
<rect width="{W}" height="{H}" rx="20" fill="#0d1117"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#30363d"/>
<text x="34" y="44" class="h"><tspan fill="{VIOLET}">$</tspan> git log --graph --author=devnishantt <tspan class="c"># every PR, oldest first</tspan></text>
<line class="trunk" x1="{mx}" y1="62" x2="{mx}" y2="{H - 14}" stroke="#6e7681" stroke-width="2.2" stroke-linecap="round"/>
{''.join(rows)}
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

def build_card(card: dict) -> str:
    W, H = 460, 168
    lines = wrap(card["desc"], 60)[:3]
    desc = "".join(f'<text class="d" x="24" y="{76 + i * 19}">{esc(l)}</text>' for i, l in enumerate(lines))
    chips, x = [], 24
    for slug in card["stack"]:
        label = ICONS[slug]["title"]
        w = 30 + len(label) * 6.6
        chips.append(f'<rect class="chip" x="{x:.1f}" y="128" width="{w:.1f}" height="24" rx="12"/>'
                     f'{icon(slug, x + 8, 134, 12)}<text class="cl" x="{x + 25:.1f}" y="144">{esc(label)}</text>')
        x += w + 6
    return f"""{svg_open(W, H, f"{card['name']}: {card['desc']}")}
<style>
  .bg{{fill:#0d1117;stroke:#30363d}} .n{{fill:#e6edf3;font:700 17px {SANS}}} .d{{fill:#9198a1;font:13px {SANS}}}
  .chip{{fill:#161b22;stroke:#30363d}} .cl{{fill:#9198a1;font:11.5px {SANS}}} .ar{{fill:#6e7681}} .dk{{fill:#e6edf3}}
</style>
<defs><linearGradient id="acc" x1="0" x2="1">
  <stop offset="0" stop-color="{VIOLET}"><animate attributeName="stop-color" values="{VIOLET};{CYAN};{VIOLET}" dur="6s" repeatCount="indefinite"/></stop>
  <stop offset="1" stop-color="{CYAN}"><animate attributeName="stop-color" values="{CYAN};{VIOLET};{CYAN}" dur="6s" repeatCount="indefinite"/></stop>
</linearGradient></defs>
<rect class="bg" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/>
<rect x="0" y="0" width="{W}" height="4" rx="2" fill="url(#acc)"/>
<path class="ar" transform="translate(24,28) scale(1.1)" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>
<text class="n" x="50" y="43">{esc(card['name'])}</text>
<path class="ar" transform="translate({W - 40},28)" d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.854-1h4.146a.25.25 0 0 1 .25.25v4.146a.25.25 0 0 1-.427.177L13.03 4.03 9.28 7.78a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042l3.75-3.75-1.543-1.543A.25.25 0 0 1 10.604 1Z"/>
{desc}
{''.join(chips)}
</svg>
"""


# ---------------------------------------------------------------- README table

def render_table(prs: list[dict]) -> str:
    lines = [START, "", "| | Project | ★ | Pull request |", "|---|---|---:|---|"]
    order = {"MERGED": 0, "OPEN": 1, "CLOSED": 2}
    for p in sorted(prs, key=lambda p: (order[p["state"]], -p["stars"])):
        if p["state"] == "CLOSED":
            continue
        mark = "🟣" if p["state"] == "MERGED" else "🟢"
        title = p["title"].replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"| {mark} | [{p['repo']}]({p['repo_url']}) | {human(p['stars'])} | [#{p['number']}]({p['url']}) {title} |")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines += ["", f"<sub>🟣 merged · 🟢 in review · refreshed {stamp}</sub>", "", END]
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("PROFILE_USER", "devnishantt"))
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 1

    prs = fetch_prs(token, args.user)
    prof = fetch_profile(token, args.user)
    st = summarize(prs)

    local = ASSETS / "avatar-embed.jpg"
    hero_avatar = data_uri(local.read_bytes()) if local.exists() else fetch_image(f"https://github.com/{args.user}.png?size=200")
    small = ASSETS / "avatar-sun.jpg"
    sun = data_uri(small.read_bytes()) if small.exists() else hero_avatar
    avatars = {p["owner"]: fetch_image(f"https://github.com/{p['owner']}.png?size=64") for p in st["projects"][:11]}

    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "hero.svg").write_text(build_hero(st, prof, args.user, hero_avatar), encoding="utf-8")
    (ASSETS / "orbit.svg").write_text(build_orbit(st, sun, avatars), encoding="utf-8")
    (ASSETS / "journey.svg").write_text(build_journey(prs), encoding="utf-8")
    (ASSETS / "stack.svg").write_text(build_stack(prof), encoding="utf-8")
    for card in CARDS:
        (ASSETS / f"card-{card['slug']}.svg").write_text(build_card(card), encoding="utf-8")

    text = README.read_text(encoding="utf-8")
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not block.search(text):
        print("README markers not found", file=sys.stderr)
        return 1
    README.write_text(block.sub(lambda _: render_table(prs), text), encoding="utf-8")
    print(f"{len(prs)} pull requests, {len(st['projects'])} projects rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
