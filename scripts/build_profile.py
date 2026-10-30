#!/usr/bin/env python3
"""Rebuild the open-source sections of the profile README and the stats card.

Pulls every pull request authored by the profile owner from the GitHub GraphQL
API, then rewrites:

* README.md between the <!-- oss:start --> / <!-- oss:end --> markers
* assets/oss-card.svg (a self-hosted stats card, no third-party service)

Standard library only, so the workflow needs no install step.
Usage: GITHUB_TOKEN=... python scripts/build_profile.py [--user LOGIN]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CARD = ROOT / "assets" / "oss-card.svg"
START, END = "<!-- oss:start -->", "<!-- oss:end -->"

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title url state createdAt mergedAt
        repository {
          nameWithOwner url stargazerCount isFork
          owner { login avatarUrl }
          primaryLanguage { name }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class PR:
    repo: str
    repo_url: str
    owner: str
    stars: int
    language: str
    number: int
    title: str
    url: str
    state: str  # MERGED | OPEN | CLOSED
    created: str


def fetch(user: str, token: str) -> list[PR]:
    prs: list[PR] = []
    cursor = None
    while True:
        body = json.dumps({"query": QUERY, "variables": {"q": f"author:{user} is:pr", "cursor": cursor}})
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=body.encode(),
            headers={"Authorization": f"bearer {token}", "User-Agent": f"{user}-profile"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if "errors" in payload:
            raise SystemExit(f"GraphQL error: {payload['errors']}")
        search = payload["data"]["search"]
        for n in search["nodes"]:
            if not n:
                continue
            repo = n["repository"]
            if repo["owner"]["login"].lower() == user.lower():
                continue  # own repositories are not external contributions
            prs.append(
                PR(
                    repo=repo["nameWithOwner"],
                    repo_url=repo["url"],
                    owner=repo["owner"]["login"],
                    stars=repo["stargazerCount"],
                    language=(repo["primaryLanguage"] or {}).get("name") or "",
                    number=n["number"],
                    title=n["title"],
                    url=n["url"],
                    state=n["state"],
                    created=n["createdAt"],
                )
            )
        if not search["pageInfo"]["hasNextPage"]:
            return prs
        cursor = search["pageInfo"]["endCursor"]


def human(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_markdown(prs: list[PR]) -> str:
    merged = [p for p in prs if p.state == "MERGED"]
    open_ = [p for p in prs if p.state == "OPEN"]
    repos = {p.repo for p in prs if p.state != "CLOSED"}
    reach = sum({p.repo: p.stars for p in prs if p.state != "CLOSED"}.values())

    lines = [
        START,
        "",
        f"**{len(merged)} merged · {len(open_)} in review · {len(repos)} projects · "
        f"{human(reach)} combined stars**",
        "",
    ]

    def table(title: str, rows: list[PR], emoji: str) -> None:
        if not rows:
            return
        rows = sorted(rows, key=lambda p: (-p.stars, p.created), reverse=False)
        lines.extend([f"#### {emoji} {title}", "", "| Project | ★ | Pull request |", "|---|---:|---|"])
        for p in rows:
            avatar = f'<img src="https://github.com/{p.owner}.png?size=40" width="16" height="16" alt="">'
            lines.append(
                f"| {avatar} [{p.repo}]({p.repo_url}) | {human(p.stars)} | "
                f"[#{p.number}]({p.url}) {md_escape(p.title)} |"
            )
        lines.append("")

    table("Merged", merged, "🟣")
    table("In review", open_, "🟢")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.extend([f"<sub>Auto-updated daily from the GitHub API · last run {stamp}</sub>", "", END])
    return "\n".join(lines)


def render_card(prs: list[PR]) -> str:
    merged = sum(p.state == "MERGED" for p in prs)
    open_ = sum(p.state == "OPEN" for p in prs)
    live = [p for p in prs if p.state != "CLOSED"]
    projects = len({p.repo for p in live})
    reach = sum({p.repo: p.stars for p in live}.values())
    langs: dict[str, int] = {}
    for p in live:
        if p.language:
            langs[p.language] = langs.get(p.language, 0) + 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]

    stats = [("Merged", str(merged)), ("In review", str(open_)), ("Projects", str(projects)), ("Stars reached", human(reach))]
    cells = []
    for i, (label, value) in enumerate(stats):
        x = 28 + i * 118
        cells.append(
            f'<text class="v" x="{x}" y="92">{html.escape(value)}</text>'
            f'<text class="l" x="{x}" y="114">{html.escape(label)}</text>'
        )

    chips, x = [], 28
    for name, count in top:
        w = 14 + 7.2 * len(f"{name} {count}")
        chips.append(
            f'<rect class="chip" x="{x}" y="138" rx="11" width="{w:.0f}" height="22"/>'
            f'<text class="c" x="{x + 10}" y="153">{html.escape(name)} <tspan class="cn">{count}</tspan></text>'
        )
        x += w + 8

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="184" viewBox="0 0 500 184" role="img" aria-label="Open-source contribution stats">
<style>
  .bg{{fill:#ffffff;stroke:#d0d7de}} .t{{fill:#1f2328}} .l,.c{{fill:#59636e}} .v{{fill:#1f2328}}
  .chip{{fill:#f6f8fa;stroke:#d0d7de}} .cn{{fill:#8250df}} .accent{{fill:#8250df}}
  text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
  .t{{font-size:15px;font-weight:600}} .v{{font-size:26px;font-weight:700}} .l{{font-size:12px}} .c{{font-size:12px}}
  @media (prefers-color-scheme: dark) {{
    .bg{{fill:#0d1117;stroke:#30363d}} .t,.v{{fill:#e6edf3}} .l,.c{{fill:#9198a1}}
    .chip{{fill:#161b22;stroke:#30363d}} .cn,.accent{{fill:#bc8cff}}
  }}
</style>
<rect class="bg" x="0.5" y="0.5" width="499" height="183" rx="12"/>
<rect class="accent" x="28" y="30" width="4" height="18" rx="2"/>
<text class="t" x="40" y="44">Open-source contributions</text>
{''.join(cells)}
{''.join(chips)}
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("PROFILE_USER", "devnishantt"))
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 1

    prs = fetch(args.user, token)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("README markers not found", file=sys.stderr)
        return 1
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    README.write_text(block.sub(lambda _: render_markdown(prs), text), encoding="utf-8")
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(render_card(prs), encoding="utf-8")
    print(f"{len(prs)} external pull requests rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
