# NewsLetter_sender

주요 IT/AI 뉴스를 수집해 HTML 뉴스레터를 생성하고, 이메일 발송 및 GitHub Pages 업로드까지 자동화하는 프로젝트입니다.

## 주요 기능

- Google News RSS 기반 카테고리별 뉴스 수집
- YouTube 추천 영상 수집(IT/AI 관련 필터)
- 브라우저용/이메일용 HTML 뉴스레터 생성
- Gmail SMTP를 통한 메일 발송
- GitHub API 업로드 및 GitHub Pages 링크 제공
- 실행 전 LowPacket 점검(`LowPacket/LowPacket.py`) 연동

## 프로젝트 구조

- `newsletter_sender.py` : 메인 실행 스크립트 (수집/생성/업로드/발송)
- `newsletter_prompt.py` : 뉴스 수집 키워드/카테고리/신뢰 소스 설정
- `requirements.txt` : Python 의존성 목록
- `config.txt` : 로컬 실행용 설정값(암호화 값 포함 가능)
- `newsletter_preview_auto.html` : 자동 생성 미리보기 결과
- `Bak/` : 기존 미리보기 백업 파일
- `github_upload_log.txt` : GitHub 업로드 로그

## 실행 흐름

1. `run_lowpacket_check()` 실행
   - `LowPacket/LowPacket.py`를 호출해 패킷 점검 수행
2. 메일 설정 유효성 확인
3. 뉴스/유튜브 데이터 수집
4. 브라우저용 HTML 생성 및 저장, 미리보기 오픈
5. GitHub 업로드 시도
6. 이메일용 HTML 생성 후 메일 발송

## 사전 준비

### 1) Python 설치

권장: Python 3.10+

### 2) 의존성 설치

```bash
pip install -r requirements.txt
```

### 3) 설정값 준비

`newsletter_sender.py`는 환경변수 우선, 없으면 `config.txt`에서 값을 읽습니다.

필수 키:

- `SENDER_EMAIL`
- `EMAIL_PASSWORD`
- `RECEIVER_EMAIL`
- `DISPLAY_EMAIL`

GitHub 업로드를 사용하려면:

- `GITHUB_TOKEN` (환경변수 또는 CI Secrets)

보안 정책상 GitHub 토큰은 `config.txt`에 저장하지 말고, 환경변수/Secrets로만 관리하세요.

## 실행 방법

프로젝트 폴더에서:

```bash
python newsletter_sender.py
```

실행하면 다음이 자동으로 수행됩니다.

- 뉴스/영상 수집
- `newsletter_preview_auto.html` 갱신
- 웹브라우저 미리보기 오픈
- GitHub Pages 업로드 시도
- 이메일 발송

## LowPacket 연동 안내

`newsletter_sender.py`는 시작 시 `LowPacket/LowPacket.py`를 서브프로세스로 실행합니다.

- `LowPacket.py`가 없으면 점검 실패 처리
- 점검 자체 실행 실패 시 이후 흐름 중단 가능

즉, 이 프로젝트는 불필요한 패킷 사용을 줄이기 위한 사전 점검 단계가 기본 포함되어 있습니다.

## GitHub Pages 링크

기본 설정값 기준:

- 저장소: `khjgate/NewsLetter`
- Pages URL: `https://khjgate.github.io/NewsLetter`

업로드 성공 시 뉴스레터 웹 버전 링크를 메일 본문에 포함합니다.

## 트러블슈팅

### 1) 메일 발송 실패

- `SENDER_EMAIL`, `EMAIL_PASSWORD`, `RECEIVER_EMAIL`, `DISPLAY_EMAIL` 누락 여부 확인
- Gmail SMTP 정책(앱 비밀번호 등) 확인

### 2) GitHub 업로드 실패

- `GITHUB_TOKEN` 유효성 확인
- 저장소 접근 권한 확인 (`khjgate/NewsLetter`)
- `github_upload_log.txt` 확인

### 3) 뉴스/유튜브 수집 지연

- 네트워크 상태 확인
- 외부 사이트 응답 지연 시 일부 섹션이 비어 있을 수 있음

## 보안 주의사항

- `config.txt`의 민감정보는 저장소에 커밋하지 않는 것을 권장합니다.
- 토큰/비밀번호는 환경변수 사용을 우선 권장합니다.
