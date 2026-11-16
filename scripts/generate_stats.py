#!/usr/bin/env python3
"""Generate privacy-conscious GitHub profile statistics as static SVG files."""
import html
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "AmuuLakh")
TOKEN = os.environ.get("GH_TOKEN")
OUT = Path("assets")
OUT.mkdir(exist_ok=True)

if not TOKEN:
    raise SystemExit("Missing GH_TOKEN. Add an Actions secret named GH_STATS_TOKEN.")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "AmuuLakh-profile-stats",
})

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    login
    name
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER,
                 isFork: false, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        isPrivate
        stargazerCount
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

def graph_query(cursor):
    for attempt in range(5):
        response = session.post(
            "https://api.github.com/graphql",
            json={"query": QUERY, "variables": {"login": USERNAME, "after": cursor}},
            timeout=45,
        )
        if response.status_code in (429, 502, 503, 504) and attempt < 4:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        result = response.json()
        if result.get("errors"):
            raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in result["errors"]))
        return result["data"]["user"]
    raise RuntimeError("GitHub API remained unavailable after retries.")

def collect():
    cursor = None
    user = None
    stars = 0
    languages = {}
    while True:
        page = graph_query(cursor)
        if page is None:
            raise RuntimeError(f"GitHub user {USERNAME!r} was not found.")
        if user is None:
            user = page
        repos = page["repositories"]
        for repo in repos["nodes"]:
            # Only public repo stars are shown; private repo names are never emitted.
            if not repo["isPrivate"]:
                stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                languages[name] = languages.get(name, 0) + edge["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    return user, stars, languages

def esc(value):
    return html.escape(str(value), quote=True)

def streaks(days):
    counts = {d["date"]: int(d["contributionCount"]) for d in days}
    today = date.today()
    last = today if counts.get(today.isoformat(), 0) else today - timedelta(days=1)
    current = 0
    cursor = last
    while counts.get(cursor.isoformat(), 0):
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    for day in days:
        if int(day["contributionCount"]) > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return current, longest

def write_stats(user, stars):
    c = user["contributionsCollection"]
    cal = c["contributionCalendar"]
    days = [d for week in cal["weeks"] for d in week["contributionDays"]]
    current, longest = streaks(days)
    metrics = [
        ("COMMITS · LAST 12 MONTHS", c["totalCommitContributions"]),
        ("CONTRIBUTIONS · LAST 12 MONTHS", cal["totalContributions"]),
        ("STARS · PUBLIC REPOSITORIES", stars),
        ("PULL REQUESTS", c["totalPullRequestContributions"]),
        ("ISSUES", c["totalIssueContributions"]),
        ("CODE REVIEWS", c["totalPullRequestReviewContributions"]),
        ("CURRENT STREAK", f"{current} days"),
        ("LONGEST STREAK · LAST 12 MONTHS", f"{longest} days"),
    ]
    cards = []
    for i, (label, value) in enumerate(metrics):
        x, y = 28 + (i % 2) * 370, 94 + (i // 2) * 72
        cards.append(
            f'<g transform="translate({x},{y})">'
            f'<text class="label" x="0" y="0">{esc(label)}</text>'
            f'<text class="value" x="0" y="31">{esc(value)}</text></g>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="390" viewBox="0 0 780 390" role="img" aria-label="GitHub statistics">
<style>
.bg{{fill:#111827}} .panel{{fill:#182235;stroke:#29364b}} .title{{fill:#f3f4f6;font:600 21px system-ui,sans-serif}}
.sub{{fill:#9ca3af;font:12px system-ui,sans-serif}} .label{{fill:#9ca3af;font:600 10px system-ui,sans-serif;letter-spacing:1px}}
.value{{fill:#f9fafb;font:700 25px system-ui,sans-serif}}
</style>
<rect class="bg" width="780" height="390" rx="16"/>
<text class="title" x="28" y="38">{esc(user.get("name") or USERNAME)} · GitHub statistics</text>
<text class="sub" x="28" y="60">Rolling 12-month contribution window · generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
<rect class="panel" x="14" y="72" width="752" height="304" rx="12"/>
{''.join(cards)}
</svg>"""
    (OUT / "stats.svg").write_text(svg, encoding="utf-8")

def write_languages(languages):
    ranked = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:8]
    total = sum(size for _, size in ranked)
    palette = ["#60a5fa", "#a78bfa", "#34d399", "#fbbf24", "#f87171", "#22d3ee", "#fb923c", "#c084fc"]
    bar_parts, rows = [], []
    x = 28
    if total:
        for i, (name, size) in enumerate(ranked):
            pct = size / total * 100
            seg = 724 * size / total
            bar_parts.append(f'<rect x="{x:.2f}" y="75" width="{seg:.2f}" height="10" fill="{palette[i]}"/>')
            x += seg
            y = 116 + i * 17
            rows.append(
                f'<circle cx="32" cy="{y-4}" r="4" fill="{palette[i]}"/>'
                f'<text class="item" x="45" y="{y}">{esc(name)}</text>'
                f'<text class="muted" x="744" y="{y}" text-anchor="end">{pct:.1f}%</text>'
            )
    else:
        rows.append('<text class="muted" x="28" y="125">No language data available.</text>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="270" viewBox="0 0 780 270" role="img" aria-label="Most-used languages">
<style>
.bg{{fill:#111827}} .panel{{fill:#182235;stroke:#29364b}} .title{{fill:#f3f4f6;font:600 20px system-ui,sans-serif}}
.item{{fill:#e5e7eb;font:12px system-ui,sans-serif}} .muted{{fill:#9ca3af;font:11px system-ui,sans-serif}}
</style>
<rect class="bg" width="780" height="270" rx="16"/><rect class="panel" x="14" y="14" width="752" height="242" rx="12"/>
<text class="title" x="28" y="48">Most-used languages</text>
<clipPath id="barclip"><rect x="28" y="75" width="724" height="10" rx="4"/></clipPath>
<g clip-path="url(#barclip)">{''.join(bar_parts)}</g>
{''.join(rows)}
<text class="muted" x="28" y="242">Language bytes across owned, non-fork repositories, including accessible private repos.</text>
</svg>"""
    (OUT / "languages.svg").write_text(svg, encoding="utf-8")

def write_activity(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for week in cal["weeks"] for d in week["contributionDays"]][-371:]
    palette = ["#202b3d", "#244b3a", "#26734b", "#32a66b", "#75d39a"]
    max_count = max([int(d["contributionCount"]) for d in days] or [1])
    cells = []
    for i, day in enumerate(days):
        col, row = divmod(i, 7)
        count = int(day["contributionCount"])
        level = 0 if count == 0 else min(4, max(1, round(count / max_count * 4)))
        x, y = 28 + col * 13, 78 + row * 13
        cells.append(
            f'<rect x="{x}" y="{y}" width="9" height="9" rx="2" fill="{palette[level]}">'
            f'<title>{esc(day["date"])}: {count} contributions</title></rect>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="780" height="190" viewBox="0 0 780 190" role="img" aria-label="Contribution activity">
<style>.bg{{fill:#111827}}.panel{{fill:#182235;stroke:#29364b}}.title{{fill:#f3f4f6;font:600 20px system-ui,sans-serif}}.muted{{fill:#9ca3af;font:11px system-ui,sans-serif}}</style>
<rect class="bg" width="780" height="190" rx="16"/><rect class="panel" x="14" y="14" width="752" height="162" rx="12"/>
<text class="title" x="28" y="48">Contribution activity · last 12 months</text>
{''.join(cells)}
<text class="muted" x="28" y="170">GitHub contribution calendar · hover cells for dates and counts.</text>
</svg>"""
    (OUT / "activity.svg").write_text(svg, encoding="utf-8")

def main():
    user, stars, languages = collect()
    write_stats(user, stars)
    write_languages(languages)
    write_activity(user)
    print(f"Generated profile SVGs for {USERNAME}; public stars: {stars}; languages: {len(languages)}")

if __name__ == "__main__":
    main()
