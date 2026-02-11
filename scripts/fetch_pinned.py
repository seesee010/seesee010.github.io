#!/usr/bin/env python3
# coding: utf-8
"""
Robustes Skript: liest data/pinned-repos.yml und ersetzt den Inhalt von
<div id="repos-container"> in docs/index.html mit gerenderten repo-cards.
Benötigt: pyyaml, beautifulsoup4
"""
import os
import sys
import yaml
from datetime import datetime
from html import escape
from bs4 import BeautifulSoup

HERE = os.path.dirname(__file__)
DATA_FILE = os.path.normpath(os.path.join(HERE, "..", "data", "pinned-repos.yml"))
INDEX_FILE = os.path.normpath(os.path.join(HERE, "..", "docs", "index.html"))


def load_yaml(path):
    if not os.path.isfile(path):
        print(f"ERROR: YAML not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except Exception as e:
            print("ERROR parsing YAML:", e)
            return None


def build_repo_card_soup(soup, repo):
    name = escape(str(repo.get("name", "") or ""))
    url = escape(str(repo.get("url", "#")))
    description = escape(str(repo.get("description") or "Keine Beschreibung verfügbar"))
    stars = int(repo.get("stars") or 0)
    forks = int(repo.get("forks") or 0)
    language = repo.get("language") or ""
    language_color = repo.get("language_color") or "#858585"
    topics = repo.get("topics") or []

    card_html = f"""
    <div class="repo-card">
        <div class="repo-header">
            <i class="fas fa-code-branch repo-icon"></i>
            <div class="repo-title">
                <a href="{url}" class="repo-name" target="_blank" rel="noopener">{name}</a>
            </div>
        </div>

        <p class="repo-description">{description}</p>

        <div class="repo-meta">
            {"<div class='meta-item'><span class='language-dot' style='background-color: " + escape(language_color) + "'></span><span>" + escape(language) + "</span></div>" if language else ""}
            <div class="meta-item"><i class="fas fa-star"></i><span>{stars}</span></div>
            <div class="meta-item"><i class="fas fa-code-fork"></i><span>{forks}</span></div>
        </div>

        {("<div class='topics'>" + ''.join(f"<span class='topic-tag'>{escape(str(t))}</span>" for t in topics) + "</div>") if topics else ""}
    </div>
    """
    return BeautifulSoup(card_html, "html.parser")


def render_repos_grid(soup, repos):
    wrapper = BeautifulSoup("<div class='repos-grid'></div>", "html.parser").div
    for repo in repos:
        card = build_repo_card_soup(soup, repo)
        # append children of card into wrapper
        wrapper.append(card)
    return wrapper


def main():
    data = load_yaml(DATA_FILE)
    if not data:
        print("No YAML data; exiting.")
        sys.exit(0)

    repos = data.get("repositories") or []
    if not isinstance(repos, list) or len(repos) == 0:
        print("No repositories found in YAML; nothing to do.")
        sys.exit(0)

    if not os.path.isfile(INDEX_FILE):
        print(f"ERROR: docs/index.html not found at {INDEX_FILE}")
        sys.exit(1)

    # Read and parse index.html
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html_raw = f.read()

    soup = BeautifulSoup(html_raw, "html.parser")

    container = soup.find(id="repos-container")
    if container is None:
        print("ERROR: could not find element with id='repos-container' in docs/index.html")
        sys.exit(1)

    # replace inner contents of the container with new grid
    new_grid = render_repos_grid(soup, repos)
    container.clear()
    # maintain existing indentation by inserting as children
    for child in new_grid.contents:
        container.append(child)

    # Update last-updated element if present
    last = soup.find(id="last-updated")
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if last:
        last.string = f"Zuletzt aktualisiert: {ts}"
    else:
        # fallback: try to find footer and append a small timestamp
        footer = soup.find("footer")
        if footer:
            footer.append(BeautifulSoup(f'<p class="last-updated" id="last-updated">Zuletzt aktualisiert: {ts}</p>', "html.parser"))

    # Backup original
    backup_path = INDEX_FILE + ".bak"
    with open(backup_path, "w", encoding="utf-8") as bf:
        bf.write(html_raw)

    # Write updated HTML
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        # use original encoding and minimal prettify to avoid extreme formatting changes
        f.write(str(soup))

    print(f"Updated {INDEX_FILE} with {len(repos)} repositories. Backup: {backup_path}")


if __name__ == "__main__":
    main()