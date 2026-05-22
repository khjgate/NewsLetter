import base64
import os
import posixpath
import sys
from pathlib import Path

import requests


GITHUB_REPO = os.getenv("GITHUB_REPO", "khjgate/NewsLetter").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "Bak",
}

EXCLUDED_FILES = {
    "config.txt",
    "github_upload_log.txt",
    "newsletter_preview_auto.html",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".log",
}


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def should_upload(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_DIRS for part in relative_parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def github_path_for(path: Path, root: Path) -> str:
    return posixpath.join(*path.relative_to(root).parts)


def upload_file(path: Path, github_path: str, headers: dict[str, str]) -> bool:
    content = path.read_bytes()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{github_path}"

    sha = None
    existing = requests.get(url, headers=headers, timeout=20)
    if existing.status_code == 200:
        sha = existing.json().get("sha")
    elif existing.status_code not in (404,):
        print(f"Failed to inspect {github_path}: {existing.status_code} {existing.text}")
        return False

    data = {
        "message": f"Add/Update {github_path}",
        "content": base64.b64encode(content).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data, timeout=30)
    if response.status_code in (200, 201):
        print(f"Uploaded: {github_path}")
        return True

    print(f"Failed: {github_path} - {response.status_code} {response.text}")
    return False


def main() -> None:
    token = get_required_env("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    root = Path(__file__).resolve().parent
    files = [
        path
        for path in sorted(root.rglob("*"))
        if should_upload(path, root)
    ]

    print(f"Uploading {len(files)} files to {GITHUB_REPO}@{GITHUB_BRANCH}")
    failures = 0
    for path in files:
        if not upload_file(path, github_path_for(path, root), headers):
            failures += 1

    if failures:
        print(f"Completed with {failures} failed uploads.")
        sys.exit(1)

    print("Upload complete.")
    print(f"Actions secrets: https://github.com/{GITHUB_REPO}/settings/secrets/actions")


if __name__ == "__main__":
    main()
