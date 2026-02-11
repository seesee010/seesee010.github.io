#!/usr/bin/env python3
# coding: utf-8
"""
Enhanced fetch_pinned.py
- Reads data/pinned-repos.yml
- Renders ALL repositories into docs/index.html as a responsive grid of repo-cards
- Generates an inline SVG horizontal bar chart of most-used languages
- Uses BeautifulSoup for robust HTML injection
- Keeps a backup docs/index.html.bak

Place as: scripts/fetch_pinned.py
Requires: pyyaml, beautifulsoup4
"""

from __future__ import annotations
import os
import sys
import yaml
from datetime import datetime
from html import escape
from collections import Counter, OrderedDict
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup

HERE = os.path.dirname(__file__)
DATA_FILE = os.path.normpath(os.path.join(HERE, "..", "data", "pinned-repos.yml"))
INDEX_FILE = os.path.normpath(os.path.join(HERE, "..", "docs", "index.html"))
BACKUP_FILE = INDEX_FILE + ".bak"


# Default fallback colours (used when language_color missing)
DEFAULT_COLORS = [
    "#58a6ff", "#3fb950", "#bc8cff", "#ffa657", "#f87171", "#7dd3fc",
    "#f9a8d4", "#f4d35e", "#94a3b8", "#a78bfa"
]


def load_yaml(path: str) -> Dict[str, Any] | None:
    if not os.path.isfile(path):
        print(f"ERROR: YAML not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except Exception as e:
            print("ERROR parsing YAML:", e)
            return None


def collect_language_stats(repos: List[Dict[str, Any]]) -> Tuple[OrderedDict, Dict[str, str]]:
    """
    Count languages over all repos.
    Return (OrderedDict(language -> count sorted desc), mapping language->color).
    If YAML contains language_color, prefer that color.
    """
    counts = Counter()
    color_map: Dict[str, str] = {}
    for r in repos:
        lang = r.get("language") or "Unknown"
        counts[lang] += 1
        lc = r.get("language_color")
        if lc:
            color_map[lang] = lc

    # Fill missing colors from default palette
    defaults = iter(DEFAULT_COLORS)
    for lang in list(counts.keys()):
        if lang not in color_map:
            try:
                color_map[lang] = next(defaults)
            except StopIteration:
                color_map[lang] = "#858585"

    # Order by count desc
    ordered = OrderedDict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
    return ordered, color_map


def build_lang_bar_svg(lang_counts: OrderedDict, color_map: Dict[str, str], max_bars: int = 8) -> str:
    """
    Build a simple horizontal bar SVG showing top languages.
    If more languages than max_bars, aggregate rest into 'Other'.
    """
    items = list(lang_counts.items())
    if not items:
        return "<p>No language data</p>"

    total = sum(count for _, count in items)
    top = items[:max_bars]
    if len(items) > max_bars:
        other_count = sum(c for _, c in items[max_bars:])
        top.append(("Other", other_count))

    # SVG layout
    width = 720
    label_width = 180
    bar_area_w = width - label_width - 40
    bar_h = 22
    gap = 12
    height = gap + len(top) * (bar_h + gap)

    max_count = max(count for _, count in top) or 1

    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Language usage chart">',
        '<style>',
        '  .lbl{font:13px/1.2 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;}',
        '  .meta{font:12px/1.2 system-ui, -apple-system, "Segoe UI", Roboto;}',
        '</style>'
    ]

    y = gap
    for name, count in top:
        bar_w = int((count / max_count) * (bar_area_w))
        color = color_map.get(name, "#858585")
        # label
        svg_parts.append(f'<text x="8" y="{y + bar_h*0.7}" class="lbl" fill="#e6edf3">{escape(name)}</text>')
        # bar background
        svg_parts.append(f'<rect x="{label_width}" y="{y}" width="{bar_area_w}" height="{bar_h}" rx="6" fill="#121317" />')
        # bar value
        svg_parts.append(f'<rect x="{label_width}" y="{y}" width="{bar_w}" height="{bar_h}" rx="6" fill="{color}" />')
        # count text
        percent = (count / total) * 100 if total else 0
        txt = f"{count} • {percent:.0f}%"
        svg_parts.append(f'<text x="{label_width + bar_area_w + 8}" y="{y + bar_h*0.7}" class="meta" fill="#c9d4dd">{escape(txt)}</text>')
        y += bar_h + gap

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def build_repos_grid_html(repos: List[Dict[str, Any]]) -> str:
    """
    Build the HTML string (safe-escaped) for all repo-cards in a grid.
    Uses the same structure/classes as your CSS.
    """
    parts = ['<div class="repos-grid">']
    for r in repos:
        name = escape(str(r.get("name", "") or ""))
        url = escape(str(r.get("url", "#")))
        description = escape(str(r.get("description") or "Keine Beschreibung verfügbar"))
        stars = int(r.get("stars") or 0)
        forks = int(r.get("forks") or 0)
        language = r.get("language") or ""
        language_color = r.get("language_color") or "#858585"
        topics = r.get("topics") or []

        topics_html = ""
        if topics:
            topics_html = '<div class="topics">' + "".join(
                f'<span class="topic-tag">{escape(str(t))}</span>' for t in topics
            ) + '</div>'

        lang_html = (
            f'<div class="meta-item"><span class="language-dot" style="background-color: {escape(language_color)}"></span>'
            f'<span>{escape(language)}</span></div>'
            if language else ""
        )

        card = f"""
<div class="repo-card">
    <div class="repo-header">
        <i class="fas fa-code-branch repo-icon"></i>
        <div class="repo-title">
            <a href="{url}" class="repo-name" target="_blank" rel="noopener">{name}</a>
        </div>
    </div>

    <p class="repo-description">{description}</p>

    <div class="repo-meta">
        {lang_html}
        <div class="meta-item"><i class="fas fa-star"></i><span>{stars}</span></div>
        <div class="meta-item"><i class="fas fa-code-fork"></i><span>{forks}</span></div>
    </div>

    {topics_html}
</div>
"""
        parts.append(card)
    parts.append("</div>")
    return "\n".join(parts)


def inject_into_index(html_path: str, new_fragment_html: str, timestamp_text: str) -> bool:
    """
    Use BeautifulSoup to replace the inner content of #repos-container with new_fragment_html
    and update the #last-updated element with timestamp_text.
    Returns True on success.
    """
    if not os.path.isfile(html_path):
        print(f"ERROR: index file not found: {html_path}")
        return False

    with open(html_path, "r", encoding="utf-8") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "html.parser")
    container = soup.find(id="repos-container")
    if container is None:
        print("ERROR: Could not find element with id='repos-container' in index.html")
        return False

    # Clear and insert new fragment (parse fragment to preserve nodes)
    fragment = BeautifulSoup(new_fragment_html, "html.parser")
    container.clear()
    for child in fragment.contents:
        container.append(child)

    # Update last-updated text
    last = soup.find(id="last-updated")
    if last:
        last.string = timestamp_text
    else:
        # attempt to insert footer timestamp if missing
        footer = soup.find("footer")
        if footer:
            footer.append(BeautifulSoup(f'<p class="last-updated" id="last-updated">{timestamp_text}</p>', "html.parser"))

    # backup and write
    with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
        bf.write(raw)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return True


def main():
    data = load_yaml(DATA_FILE)
    if not data:
        print("No YAML - exiting.")
        sys.exit(0)

    repos = data.get("repositories") or []
    # ensure we use ALL repos present in YAML
    if not isinstance(repos, list) or len(repos) == 0:
        print("No repos found in YAML - nothing to do.")
        sys.exit(0)

    # Build language stats & chart
    lang_counts, color_map = collect_language_stats(repos)
    svg_chart = build_lang_bar_svg(lang_counts, color_map, max_bars=8)

    # Put chart and grid together
    grid_html = build_repos_grid_html(repos)
    combined_html = f"""
<div class="pinned-dashboard">
  <h2 style="margin-bottom:12px; color: #cfe8ff;">Language usage</h2>
  <div class="lang-chart" style="margin-bottom:24px;">
    {svg_chart}
  </div>

  <h2 style="margin:8px 0 16px; color:#cfe8ff;">Pinned repositories</h2>
  {grid_html}
</div>
"""

    ts = f"Zuletzt aktualisiert: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    ok = inject_into_index(INDEX_FILE, combined_html, ts)
    if not ok:
        sys.exit(1)

    print(f"Updated {INDEX_FILE} with {len(repos)} repos and language chart.")


if __name__ == "__main__":
    main()