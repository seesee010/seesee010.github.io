#!/usr/bin/env python3
"""
Fetches pinned repositories from GitHub via GraphQL API,
updates data/pinned-repos.yml, and regenerates docs/index.html.
"""

import os
import sys
import yaml
import requests
from datetime import datetime, timezone
from html import escape
from collections import Counter, OrderedDict

USERNAME = "seesee010"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA_FILE = os.path.join(ROOT, "data", "pinned-repos.yml")
INDEX_FILE = os.path.join(ROOT, "docs", "index.html")

GRAPHQL_URL = "https://api.github.com/graphql"
GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          primaryLanguage { name, color }
          homepageUrl
          updatedAt
          repositoryTopics(first: 10) {
            nodes { topic { name } }
          }
        }
      }
    }
  }
}
"""

DEFAULT_COLORS = [
    "#58a6ff", "#3fb950", "#bc8cff", "#ffa657", "#f87171",
    "#7dd3fc", "#f9a8d4", "#f4d35e", "#94a3b8", "#a78bfa",
]


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def fetch_pinned_repos(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()

    if "errors" in body:
        print(f"GraphQL errors: {body['errors']}")
        return None

    nodes = (
        body.get("data", {})
        .get("user", {})
        .get("pinnedItems", {})
        .get("nodes", [])
    )

    repos = []
    for n in nodes:
        lang = n.get("primaryLanguage") or {}
        topics = [
            t["topic"]["name"]
            for t in n.get("repositoryTopics", {}).get("nodes", [])
        ]
        repos.append({
            "name": n["name"],
            "description": n.get("description"),
            "url": n["url"],
            "stars": n.get("stargazerCount", 0),
            "forks": n.get("forkCount", 0),
            "language": lang.get("name"),
            "language_color": lang.get("color"),
            "homepage": n.get("homepageUrl") or "",
            "updated_at": n.get("updatedAt", ""),
            "topics": topics,
        })
    return repos


# ---------------------------------------------------------------------------
# YAML persistence
# ---------------------------------------------------------------------------

def save_yaml(repos, path):
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "username": USERNAME,
        "repositories": repos,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_yaml(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("repositories", [])


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_language_bar(repos):
    counts = Counter()
    color_map = {}
    for r in repos:
        lang = r.get("language") or "Unknown"
        counts[lang] += 1
        lc = r.get("language_color")
        if lc:
            color_map[lang] = lc

    defaults = iter(DEFAULT_COLORS)
    for lang in counts:
        if lang not in color_map:
            color_map[lang] = next(defaults, "#858585")

    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    if not ordered:
        return ""

    total = sum(c for _, c in ordered)
    segments = []
    for lang, count in ordered:
        pct = (count / total) * 100
        color = color_map.get(lang, "#858585")
        segments.append(
            f'<div class="lang-segment" style="width:{pct:.1f}%;background:{color}" '
            f'title="{escape(lang)} {pct:.0f}%"></div>'
        )

    legend = []
    for lang, count in ordered:
        pct = (count / total) * 100
        color = color_map.get(lang, "#858585")
        legend.append(
            f'<span class="lang-legend-item">'
            f'<span class="language-dot" style="background-color:{color}"></span>'
            f'{escape(lang)} <span class="lang-pct">{pct:.0f}%</span></span>'
        )

    return (
        '<div class="lang-bar-wrapper">'
        '<div class="lang-bar">' + "".join(segments) + '</div>'
        '<div class="lang-legend">' + "".join(legend) + '</div>'
        '</div>'
    )


def build_repo_cards(repos):
    cards = []
    for r in repos:
        name = escape(str(r.get("name", "")))
        url = escape(str(r.get("url", "#")))
        desc = escape(str(r.get("description") or "No description available"))
        stars = int(r.get("stars") or 0)
        forks = int(r.get("forks") or 0)
        language = r.get("language") or ""
        lang_color = r.get("language_color") or "#858585"
        topics = r.get("topics") or []

        lang_html = ""
        if language:
            lang_html = (
                f'<div class="meta-item">'
                f'<span class="language-dot" style="background-color:{escape(lang_color)}"></span>'
                f'<span>{escape(language)}</span></div>'
            )

        topics_html = ""
        if topics:
            tags = "".join(f'<span class="topic-tag">{escape(str(t))}</span>' for t in topics)
            topics_html = f'<div class="topics">{tags}</div>'

        cards.append(f"""
        <div class="repo-card">
            <div class="repo-header">
                <i class="fas fa-code-branch repo-icon"></i>
                <div class="repo-title">
                    <a href="{url}" class="repo-name" target="_blank" rel="noopener">{name}</a>
                </div>
            </div>
            <p class="repo-description">{desc}</p>
            <div class="repo-meta">
                {lang_html}
                <div class="meta-item"><i class="fas fa-star"></i><span>{stars}</span></div>
                <div class="meta-item"><i class="fas fa-code-fork"></i><span>{forks}</span></div>
            </div>
            {topics_html}
        </div>""")

    return "\n".join(cards)


def write_index(repos, path):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lang_bar = build_language_bar(repos)
    repo_cards = build_repo_cards(repos)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>seesee010 | Pinned Projects</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    :root {{
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-tertiary: #1c2128;
        --border-color: #30363d;
        --text-primary: #e6edf3;
        --text-secondary: #7d8590;
        --accent-blue: #58a6ff;
        --accent-green: #3fb950;
        --accent-purple: #bc8cff;
        --shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: linear-gradient(135deg, var(--bg-primary) 0%, #0a0e13 100%);
        color: var(--text-primary);
        min-height: 100vh;
        padding: 40px 20px;
        position: relative;
        overflow-x: hidden;
    }}

    body::before {{
        content: '';
        position: fixed;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(88, 166, 255, 0.1) 0%, transparent 70%);
        animation: float 20s ease-in-out infinite;
        pointer-events: none;
    }}

    @keyframes float {{
        0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
        50% {{ transform: translate(-20px, 20px) rotate(180deg); }}
    }}

    .container {{
        max-width: 1200px;
        margin: 0 auto;
        position: relative;
        z-index: 1;
    }}

    header {{
        text-align: center;
        margin-bottom: 60px;
        animation: fadeInDown 0.8s ease-out;
    }}

    @keyframes fadeInDown {{
        from {{ opacity: 0; transform: translateY(-30px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    h1 {{
        font-size: 3.5em;
        font-weight: 800;
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 10px;
        letter-spacing: -1px;
    }}

    .subtitle {{
        color: var(--text-secondary);
        font-size: 1.2em;
        margin-top: 10px;
    }}

    .github-link {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-top: 20px;
        padding: 12px 24px;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
        text-decoration: none;
        transition: all 0.3s ease;
    }}

    .github-link:hover {{
        border-color: var(--accent-blue);
        box-shadow: 0 0 20px rgba(88, 166, 255, 0.3);
        transform: translateY(-2px);
    }}

    /* Language bar */
    .lang-bar-wrapper {{
        margin-bottom: 32px;
    }}

    .lang-bar {{
        display: flex;
        height: 10px;
        border-radius: 6px;
        overflow: hidden;
        background: var(--bg-tertiary);
        margin-bottom: 12px;
    }}

    .lang-segment {{
        min-width: 4px;
        transition: opacity 0.2s;
    }}

    .lang-segment:hover {{
        opacity: 0.8;
    }}

    .lang-legend {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 0.85em;
        color: var(--text-secondary);
    }}

    .lang-legend-item {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    .lang-pct {{
        opacity: 0.7;
    }}

    /* Repo grid */
    .repos-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
        gap: 24px;
        margin-bottom: 40px;
    }}

    .repo-card {{
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        animation: fadeInUp 0.6s ease-out backwards;
    }}

    .repo-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 3px;
        background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }}

    .repo-card:hover::before {{ transform: scaleX(1); }}

    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(30px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    .repo-card:nth-child(1) {{ animation-delay: 0.1s; }}
    .repo-card:nth-child(2) {{ animation-delay: 0.2s; }}
    .repo-card:nth-child(3) {{ animation-delay: 0.3s; }}
    .repo-card:nth-child(4) {{ animation-delay: 0.4s; }}
    .repo-card:nth-child(5) {{ animation-delay: 0.5s; }}
    .repo-card:nth-child(6) {{ animation-delay: 0.6s; }}

    .repo-card:hover {{
        transform: translateY(-8px);
        border-color: var(--accent-blue);
        box-shadow: var(--shadow);
    }}

    .repo-header {{
        display: flex;
        align-items: start;
        gap: 12px;
        margin-bottom: 16px;
    }}

    .repo-icon {{
        font-size: 1.5em;
        color: var(--text-secondary);
        flex-shrink: 0;
    }}

    .repo-title {{ flex: 1; }}

    .repo-name {{
        font-size: 1.3em;
        font-weight: 700;
        color: var(--accent-blue);
        text-decoration: none;
        display: block;
        margin-bottom: 8px;
        transition: color 0.3s ease;
    }}

    .repo-name:hover {{ color: var(--accent-purple); }}

    .repo-description {{
        color: var(--text-secondary);
        line-height: 1.6;
        margin-bottom: 16px;
        min-height: 48px;
    }}

    .repo-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 12px;
        font-size: 0.9em;
    }}

    .meta-item {{
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--text-secondary);
    }}

    .language-dot {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
    }}

    .topics {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
    }}

    .topic-tag {{
        padding: 4px 12px;
        background: rgba(88, 166, 255, 0.1);
        border: 1px solid rgba(88, 166, 255, 0.3);
        border-radius: 16px;
        font-size: 0.85em;
        color: var(--accent-blue);
        transition: all 0.3s ease;
    }}

    .topic-tag:hover {{
        background: rgba(88, 166, 255, 0.2);
        border-color: var(--accent-blue);
    }}

    .footer {{
        text-align: center;
        margin-top: 60px;
        padding-top: 40px;
        border-top: 1px solid var(--border-color);
        color: var(--text-secondary);
    }}

    .last-updated {{
        font-size: 0.9em;
        opacity: 0.7;
    }}

    @media (max-width: 768px) {{
        h1 {{ font-size: 2.5em; }}
        .repos-grid {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1><i class="fab fa-github"></i> seesee010</h1>
        <p class="subtitle">Pinned Projects</p>
        <a class="github-link" href="https://github.com/seesee010" target="_blank" rel="noopener">
            <i class="fab fa-github"></i> Visit GitHub Profile
        </a>
    </header>

    <div id="repos-container">
        {lang_bar}
        <div class="repos-grid">
            {repo_cards}
        </div>
    </div>

    <footer class="footer">
        <p class="last-updated" id="last-updated">Last updated: {now}</p>
    </footer>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    token = os.environ.get("GITHUB_TOKEN")

    repos = None
    if token:
        print(f"Fetching pinned repos for {USERNAME} via GraphQL...")
        repos = fetch_pinned_repos(token)
        if repos is not None:
            print(f"Fetched {len(repos)} pinned repos.")
            save_yaml(repos, DATA_FILE)
        else:
            print("GraphQL fetch failed, falling back to cached YAML.")

    if repos is None:
        print("Loading repos from cached YAML...")
        repos = load_yaml(DATA_FILE)

    if not repos:
        print("No repos found. Nothing to do.")
        sys.exit(0)

    write_index(repos, INDEX_FILE)
    print(f"Generated {INDEX_FILE} with {len(repos)} repos.")


if __name__ == "__main__":
    main()
