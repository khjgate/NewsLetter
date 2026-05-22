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

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    user_response = requests.get("https://api.github.com/user", headers=headers, timeout=15)
    if user_response.status_code != 200:
        print(f"Failed to read GitHub user: {user_response.status_code}")
        print(user_response.text)
        sys.exit(1)

    username = user_response.json()["login"]
    print(f"GitHub user: {username}")

    target_repo_response = requests.get(
        f"https://api.github.com/repos/{username}/NewsLetter",
        headers=headers,
        timeout=15,
    )
    if target_repo_response.status_code == 200:
        repo = target_repo_response.json()
        print(f"Repository exists: {repo['full_name']}")
        print(f"GitHub Pages URL: https://{username}.github.io/NewsLetter/")
        return

    print(f"Repository not found: {target_repo_response.status_code}")
    sys.exit(1)


if __name__ == "__main__":
    main()
