# GitHub API 업로드 테스트 스크립트
import base64
import datetime
import os
import sys

import requests


def _get_required_env(name: str) -> str:
    """필수 환경변수를 읽고 누락 시 종료합니다."""
    value: str = os.getenv(name, "").strip()
    if not value:
        print(f"❌ 환경변수 `{name}` 이(가) 비어 있습니다.")
        sys.exit(1)
    return value


def main() -> None:
    """GitHub API 업로드 권한을 테스트합니다."""
    github_token: str = _get_required_env("GITHUB_TOKEN")
    github_repo: str = os.getenv("GITHUB_REPO", "khjgate/NewsLetter").strip()
    github_branch: str = os.getenv("GITHUB_BRANCH", "main").strip()

    url = f"https://api.github.com/repos/{github_repo}/contents/test.txt"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    sha = None
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"GET 응답: {response.status_code}")
        if response.status_code == 200:
            sha = response.json().get("sha")
            print(f"기존 파일 발견, SHA: {sha}")
    except Exception as error:
        print(f"확인 오류: {error}")

    content = f"GitHub 연동 테스트 - {datetime.datetime.now()}"
    data = {
        "message": "Test upload",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": github_branch,
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data, timeout=10)
    print(f"PUT 응답: {response.status_code}")
    if response.status_code in [200, 201]:
        print("✅ GitHub 업로드 성공!")
    else:
        print(f"❌ 실패: {response.text}")


if __name__ == "__main__":
    main()
