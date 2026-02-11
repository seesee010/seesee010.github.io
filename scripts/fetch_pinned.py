import requests
from datetime import datetime
import json
import os

# GitHub Benutzername
USERNAME = "seesee010"
INDEX_HTML_PATH = "../index.html"  # relativ vom scripts-Ordner

def fetch_pinned_repos(user):
    url = f"https://api.github.com/users/{user}/repos?sort=updated&per_page=100"
    headers = {"Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    repos = resp.json()
    
    # Pinned simulieren: wir nehmen Top 6 nach Sternen
    pinned = sorted(repos, key=lambda r: r['stargazers_count'], reverse=True)[:6]

    result = []
    for r in pinned:
        result.append({
            "name": r["name"],
            "url": r["html_url"],
            "description": r.get("description") or "",
            "stars": r["stargazers_count"],
            "forks": r["forks_count"],
            "language": r.get("language"),
            "language_color": "#858585",  # einfach neutral, du kannst mapping hinzufügen
            "topics": r.get("topics", []),
        })
    return result

def update_index_html(repos, path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    # Neues div für die Repos
    repos_div = '<div class="repos-grid">\n'
    for r in repos:
        topics_html = ""
        if r["topics"]:
            topics_html = '<div class="topics">' + "".join(
                f'<span class="topic-tag">{t}</span>' for t in r["topics"]
            ) + '</div>'
        repos_div += f'''
        <div class="repo-card">
            <div class="repo-header">
                <i class="fas fa-code-branch repo-icon"></i>
                <div class="repo-title">
                    <a href="{r['url']}" class="repo-name" target="_blank" rel="noopener">{r['name']}</a>
                </div>
            </div>
            <p class="repo-description">{r['description']}</p>
            <div class="repo-meta">
                {f'<div class="meta-item"><span class="language-dot" style="background-color: {r["language_color"]}"></span><span>{r["language"]}</span></div>' if r["language"] else ""}
                <div class="meta-item"><i class="fas fa-star"></i><span>{r['stars']}</span></div>
                <div class="meta-item"><i class="fas fa-code-fork"></i><span>{r['forks']}</span></div>
            </div>
            {topics_html}
        </div>
        '''
    repos_div += "\n</div>"

    # Alte Inhalte zwischen <div id="repos-container"> und </div> ersetzen
    start_tag = '<div id="repos-container">'
    end_tag = '</div>'
    start_index = html.find(start_tag)
    if start_index == -1:
        raise ValueError("Konnte <div id=\"repos-container\"> nicht finden")
    start_index += len(start_tag)
    end_index = html.find(end_tag, start_index)
    if end_index == -1:
        raise ValueError("Konnte schließendes </div> nicht finden")

    new_html = html[:start_index] + repos_div + html[end_index:]
    
    # Aktualisiere Zeitstempel
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if 'id="last-updated"' in new_html:
        new_html = new_html.replace(
            '<p class="last-updated" id="last-updated"></p>',
            f'<p class="last-updated" id="last-updated">Zuletzt aktualisiert: {timestamp}</p>'
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

def main():
    repos = fetch_pinned_repos(USERNAME)
    update_index_html(repos, INDEX_HTML_PATH)
    print(f"Updated {INDEX_HTML_PATH} with {len(repos)} pinned repos.")

if __name__ == "__main__":
    main()