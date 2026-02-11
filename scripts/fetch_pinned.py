#!/usr/bin/env python3
"""
Script to fetch pinned repositories from GitHub user profile
"""

import os
import requests
import yaml
from datetime import datetime

GITHUB_USERNAME = "seesee010"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# GitHub GraphQL Query
QUERY = """
query($username: String!) {
  user(login: $username) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          primaryLanguage {
            name
            color
          }
          isPrivate
          updatedAt
          homepageUrl
          repositoryTopics(first: 10) {
            nodes {
              topic {
                name
              }
            }
          }
        }
      }
    }
  }
}
"""

def fetch_pinned_repos():
    """Fetch pinned repositories using GitHub GraphQL API"""
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"username": GITHUB_USERNAME}},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    return data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])

def format_repo_data(repos):
    """Format repository data for YAML output"""
    
    formatted_repos = []
    
    for repo in repos:
        topics = [node["topic"]["name"] for node in repo.get("repositoryTopics", {}).get("nodes", [])]
        
        formatted_repo = {
            "name": repo["name"],
            "description": repo.get("description", ""),
            "url": repo["url"],
            "stars": repo["stargazerCount"],
            "forks": repo["forkCount"],
            "language": repo.get("primaryLanguage", {}).get("name") if repo.get("primaryLanguage") else None,
            "language_color": repo.get("primaryLanguage", {}).get("color") if repo.get("primaryLanguage") else None,
            "homepage": repo.get("homepageUrl"),
            "updated_at": repo["updatedAt"],
            "topics": topics
        }
        
        formatted_repos.append(formatted_repo)
    
    return formatted_repos

def save_to_yaml(repos, filename="data/pinned-repos.yml"):
    """Save repository data to YAML file"""
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "username": GITHUB_USERNAME,
        "repositories": repos
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(output, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    
    print(f"✓ Saved {len(repos)} pinned repositories to {filename}")

def main():
    print(f"Fetching pinned repositories for {GITHUB_USERNAME}...")
    
    repos = fetch_pinned_repos()
    
    if repos is None:
        print("Failed to fetch repositories")
        return
    
    formatted_repos = format_repo_data(repos)
    save_to_yaml(formatted_repos)
    
    print(f"✓ Successfully fetched {len(formatted_repos)} repositories")

if __name__ == "__main__":
    main()
