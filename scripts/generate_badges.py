#!/usr/bin/env python3
"""Tạo assets/badges.svg: huy hiệu thành tựu GitHub, tự mở khóa theo số liệu thật.
Không dùng dịch vụ ngoài, chỉ gọi GitHub API bằng token trong biến môi trường GH_TOKEN.
Chạy thử không cần mạng:  python scripts/generate_badges.py --demo
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "thannhf")
TOKEN = os.environ.get("GH_TOKEN", "")
API = "https://api.github.com"
OUT = os.environ.get("BADGES_OUT", "assets/badges.svg")

# ---------- Theme (tokyonight) ----------
BG, CARD, BORDER = "#1a1b27", "#24283b", "#414868"
TEXT, MUTED, TITLE = "#c0caf5", "#565f89", "#7aa2f7"
LOCKED = "#3b4261"
TIERS = [  # (rank, màu, tên)
    ("C", "#cd7f32", "Bronze"),
    ("B", "#c0c0c0", "Silver"),
    ("A", "#ffd166", "Gold"),
    ("S", "#7dcfff", "Diamond"),
]

# ---------- Icon (viewBox 24x24, kiểu Feather) ----------
ICONS = {
    "commit": '<circle cx="12" cy="12" r="4"/><path d="M1.05 12H8M16 12h6.95"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "repo": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "pr": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7M6 9v12"/>',
    "issue": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}

# key, tiêu đề, icon, mốc [C, B, A, S]
BADGES = [
    ("commits", "Committer", "commit", [100, 500, 1000, 5000]),
    ("stars", "Stargazer", "star", [1, 10, 50, 100]),
    ("followers", "Popular", "users", [1, 10, 50, 100]),
    ("repos", "Repo Builder", "repo", [1, 10, 30, 50]),
    ("prs", "PR Master", "pr", [1, 10, 50, 100]),
    ("issues", "Issue Hunter", "issue", [1, 10, 30, 100]),
    ("languages", "Polyglot", "code", [3, 5, 8, 12]),
    ("streak", "On Fire", "zap", [3, 7, 30, 100]),
    ("reviews", "Reviewer", "eye", [1, 10, 30, 100]),
    ("age", "Veteran (năm)", "calendar", [1, 2, 4, 8]),
]


# ---------- Thu thập dữ liệu ----------
def http(url, payload=None):
    headers = {"User-Agent": "badge-generator", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
        return json.load(r)


GQL = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
contributionsCollection(from:$from,to:$to){
totalCommitContributions restrictedContributionsCount totalPullRequestContributions
totalIssueContributions totalPullRequestReviewContributions
contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""


def fetch_stats():
    user = http(f"{API}/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = http(f"{API}/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    commits = prs = issues = reviews = 0
    days = {}
    for year in range(created.year, now.year + 1):
        frm = max(created, datetime(year, 1, 1, tzinfo=timezone.utc))
        to = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        res = http(
            "https://api.github.com/graphql",
            {"query": GQL, "variables": {"login": USER, "from": frm.isoformat(), "to": to.isoformat()}},
        )["data"]["user"]["contributionsCollection"]
        commits += res["totalCommitContributions"] + res["restrictedContributionsCount"]
        prs += res["totalPullRequestContributions"]
        issues += res["totalIssueContributions"]
        reviews += res["totalPullRequestReviewContributions"]
        for w in res["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    return {
        "commits": commits,
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "repos": user["public_repos"],
        "prs": prs,
        "issues": issues,
        "languages": len({r["language"] for r in own if r["language"]}),
        "streak": best_streak(days),
        "reviews": reviews,
        "age": (now - created).days // 365,
    }


def best_streak(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        cur = date.fromisoformat(d)
        if days[d] > 0:
            run = run + 1 if prev and cur - prev == timedelta(days=1) else 1
            best = max(best, run)
            prev = cur
        else:
            run, prev = 0, None
    return best


DEMO = {"commits": 494, "stars": 4, "followers": 3, "repos": 36, "prs": 13,
        "issues": 34, "languages": 14, "streak": 4, "reviews": 0, "age": 4}


# ---------- Vẽ SVG ----------
def tier_of(value, goals):
    return sum(1 for g in goals if value >= g)  # 0..4


def render_badge(i, spec, value):
    _, title, icon, goals = spec
    col, row = i % 5, i // 5
    w, h, gap = 164, 148, 10
    x, y = 20 + col * (w + gap), 56 + row * (h + gap)
    cx = w / 2
    tier = tier_of(value, goals)
    unlocked = tier > 0
    color = TIERS[tier - 1][1] if unlocked else LOCKED
    rank = TIERS[tier - 1][0] if unlocked else "?"
    tname = TIERS[tier - 1][2] if unlocked else "Locked"

    if tier < 4:
        nxt = goals[tier]
        prev = goals[tier - 1] if tier else 0
        ratio = max(0.0, min(1.0, (value - prev) / (nxt - prev)))
        label = f"{value} / {nxt}"
    else:
        ratio, label = 1.0, f"{value} · MAX"

    bar_w = w - 36
    cy = 46
    hexp = f"{cx},{cy-30} {cx+26},{cy-15} {cx+26},{cy+15} {cx},{cy+30} {cx-26},{cy+15} {cx-26},{cy-15}"
    glow = f'filter="url(#glow)"' if unlocked else ""
    opacity = "1" if unlocked else "0.55"
    return f"""
  <g transform="translate({x},{y})" opacity="{opacity}">
    <rect width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-width="1"/>
    <polygon points="{hexp}" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="2" {glow}/>
    <g transform="translate({cx-12},{cy-12})" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>
    <circle cx="{cx+26}" cy="{cy-26}" r="10" fill="{color}"/>
    <text x="{cx+26}" y="{cy-22}" text-anchor="middle" font-size="12" font-weight="800" fill="{BG}">{rank}</text>
    <text x="{cx}" y="96" text-anchor="middle" font-size="14" font-weight="700" fill="{TEXT}">{escape(title)}</text>
    <text x="{cx}" y="112" text-anchor="middle" font-size="11" fill="{MUTED}">{tname} · {escape(label)}</text>
    <rect x="18" y="124" width="{bar_w}" height="6" rx="3" fill="{BG}"/>
    <rect x="18" y="124" width="{bar_w*ratio:.1f}" height="6" rx="3" fill="{color}"/>
  </g>"""


def build_svg(stats):
    cols, rows, w, h, gap = 5, 2, 164, 148, 10
    width = 40 + cols * w + (cols - 1) * gap
    height = 56 + rows * h + (rows - 1) * gap + 20
    unlocked = sum(1 for k, *_r in [(b[0], b[3]) for b in BADGES] if stats[k] >= _r[0][0])
    body = "".join(render_badge(i, b, stats[b[0]]) for i, b in enumerate(BADGES))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="'Segoe UI',Ubuntu,Arial,sans-serif">
  <defs>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" rx="14" fill="{BG}"/>
  <text x="20" y="34" font-size="18" font-weight="700" fill="{TITLE}">🏆 Achievements</text>
  <text x="{width-20}" y="34" text-anchor="end" font-size="13" fill="{MUTED}">{unlocked}/{len(BADGES)} unlocked</text>{body}
</svg>
"""


def main():
    stats = DEMO if "--demo" in sys.argv else fetch_stats()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_svg(stats))
    print("OK", OUT, stats)


if __name__ == "__main__":
    main()
