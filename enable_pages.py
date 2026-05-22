import os
import sys

import requests


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def main() -> None:
    github_token = get_required_env("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPO", "khjgate/NewsLetter").strip()

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{github_repo}/pages"
    data = {"source": {"branch": "main", "path": "/"}}

    print(f"Enabling GitHub Pages for {github_repo}")
    response = requests.post(url, headers=headers, json=data, timeout=15)

    if response.status_code == 201:
        result = response.json()
        print("GitHub Pages enabled.")
        print(f"URL: {result.get('html_url', 'N/A')}")
        return

    if response.status_code == 409:
        print("GitHub Pages is already enabled.")
        status_response = requests.get(url, headers=headers, timeout=15)
        if status_response.status_code == 200:
            result = status_response.json()
            print(f"URL: {result.get('html_url', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
        return

    print(f"Failed to enable GitHub Pages: {response.status_code}")
    print(response.text)
    sys.exit(1)


if __name__ == "__main__":
    main()
