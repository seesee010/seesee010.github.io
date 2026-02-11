#!/usr/bin/env python3
"""
Read data/pinned-repos.yml and inject rendered repo <div>s into docs/index.html.

Place this file as scripts/fetch_pinned.py (workflow runs it from repo root: python scripts/fetch_pinned.py).
Requires PyYAML (pip install pyyaml).
"""

import os
import sys
import yaml
import re
from datetime import datetime
from html import escape

HERE = os.path.dirname(__file__)
DATA_PATH = os.path.normpath(os.path.join(HERE, "..", "data", "pinned-repos.yml"))
INDEX_PATH = os.path.normpath(os.path.join(HERE, "..", "docs", "index.html"))  # updated to docs/


def load_yaml(path):
    """Load YAML file from disk; return dict or None."""
    if not os.path.exists(path):
        print(f"ERROR: data file not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_repos_grid(repos):
    """Return HTML string for <div class="repos-grid">...</div>"""
    parts = ['<div class="repos-grid">']
    for r in repos:
        name = escape(str(r.get("name", "")))
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


def find_matching_div_end(html_text, open_tag_start_idx):
    """
    Given the index of '<div' of the opening tag (e.g. <div id="repos-container"...),
    return the index right after the matching closing </div>.
    Handles nested divs.
    """
    open_tag_end = html_text.find(">", open_tag_start_idx)
    if open_tag_end == -1:
        raise ValueError("Malformed HTML: opening <div> has no '>'")
    pos = open_tag_end + 1
    depth = 1

    regex = re.compile(r"<(/?)(div)(\s|>|/)", re.IGNORECASE)
    while True:
        m = regex.search(html_text, pos)
        if not m:
            raise ValueError("Malformed HTML: matching </div> not found")
        is_closing = m.group(1) == "/"
        if not is_closing:
            depth += 1
        else:
            depth -= 1
        pos = m.end()
        if depth == 0:
            closing_end = html_text.find(">", m.start())
            if closing_end == -1:
                raise ValueError("Malformed HTML: closing </div> has no '>'")
            return closing_end + 1


def replace_repos_container(html_text, new_repos_html):
    """Replace the inner content of the div with id='repos-container' with new_repos_html."""
    start_tag_search = re.search(r'<div\s+id=["\']repos-container["\']', html_text, re.IGNORECASE)
    if not start_tag_search:
        raise ValueError('Could not find <div id="repos-container"> in index.html (docs/index.html)')
    open_tag_start = start_tag_search.start()

    end_after_closing = find_matching_div_end(html_text, open_tag_start)

    opening_tag_end = html_text.find(">", start_tag_search.end() - 1)
    if opening_tag_end == -1:
        raise ValueError("Malformed HTML around repos-container opening tag")
    new_html = html_text[:opening_tag_end + 1] + "\n" + new_repos_html + "\n" + html_text[end_after_closing:]
    return new_html


def update_last_updated(html_text, timestamp_text):
    """Replace content of element with id='last-updated'."""
    pattern = re.compile(r'(<p\b[^>]*id=["\']last-updated["\'][^>]*>)(.*?)(</p>)', re.IGNORECASE | re.DOTALL)
    if pattern.search(html_text):
        return pattern.sub(rf'\1{escape(timestamp_text)}\3', html_text, count=1)
    return html_text


def main():
    data = load_yaml(DATA_PATH)
    if not data:
        print("No data loaded; exiting.")
        sys.exit(0)

    repos = data.get("repositories") or []
    if not repos:
        print("No repositories in YAML; nothing to do.")
        sys.exit(0)

    if not os.path.exists(INDEX_PATH):
        print(f"ERROR: docs/index.html not found at {INDEX_PATH}")
        sys.exit(1)

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html_text = f.read()

    new_repos_html = build_repos_grid(repos)

    try:
        new_html = replace_repos_container(html_text, new_repos_html)
    except ValueError as e:
        print(f"ERROR while replacing repos container: {e}")
        sys.exit(1)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    new_html = update_last_updated(new_html, f"Zuletzt aktualisiert: {ts}")

    backup_path = INDEX_PATH + ".bak"
    with open(backup_path, "w", encoding="utf-8") as bf:
        bf.write(html_text)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"Updated {INDEX_PATH} with {len(repos)} repos. Backup saved to {backup_path}")


if __name__ == "__main__":
    main()