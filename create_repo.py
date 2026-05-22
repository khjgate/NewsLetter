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
    repo_name = os.getenv("GITHUB_REPO_NAME", "NewsLetter").strip()

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "name": repo_name,
        "description": "Newsletter hosting for GitHub Pages",
        "private": True,
        "auto_init": True,
    }

    print(f"Creating repository: {repo_name}")
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=data,
        timeout=15,
    )

    if response.status_code == 201:
        repo = response.json()
        print("Repository created.")
        print(f"URL: {repo['html_url']}")
        print(f"Full name: {repo['full_name']}")
        print(f"Pages URL: https://{repo['owner']['login']}.github.io/{repo_name}/")
        return

    if response.status_code == 422 and "name already exists" in response.text.lower():
        print(f"Repository already exists: {repo_name}")
        return

    print(f"Failed to create repository: {response.status_code}")
    print(response.text)
    sys.exit(1)


if __name__ == "__main__":
    main()
