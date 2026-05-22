# 뉴스레터 자동 발송 프로그램
# 주요 IT 뉴스 수집, HTML 본문 생성, 이메일 발송 기능 포함
# 주석은 한국어로 설명합니다


# 이메일 헤더 한글 인코딩을 위한 Header 추가
# 웹브라우저 자동 오픈을 위한 모듈 추가
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
import datetime
import webbrowser
import os
import shutil
import subprocess
import sys
import base64
import hashlib
# 웹 크롤링을 위한 라이브러리
import requests
from bs4 import BeautifulSoup
import json


if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 네트워크 요청 시 타임아웃 설정 (연결 및 읽기 타임아웃)
# 연결 타임아웃 2초, 읽기 타임아웃 4초로 설정하여 네트워크 지연 시 빠르게 실패하도록 함
DEFAULT_REQUEST_TIMEOUT = (2, 4)
SHORT_REQUEST_TIMEOUT = (2, 2)
MAX_NEWS_KEYWORDS_PER_CATEGORY = 12 # 카테고리당 최대 12개 키워드로 검색하여 다양한 뉴스 수집 (기존 5개에서 확대)
MAX_ACADEMIC_KEYWORDS = 12          # 학술기관 키워드도 최대 12개로 확대하여 AX Trend 섹션 강화 (기존 5개에서 확대)
MAX_YOUTUBE_KEYWORDS = 10           # 유튜브 키워드 최대 10개로 설정
MAX_NEWS_ITEMS_PER_SECTION = 10


def safe_get(url, headers=None, timeout=DEFAULT_REQUEST_TIMEOUT, verify=False):
    """외부 요청 실패 시 None을 반환하여 다음 작업을 계속 진행"""
    try:
        return requests.get(url, headers=headers, timeout=timeout, verify=verify)
    except requests.RequestException:
        return None

# ============================================================
# GitHub 설정 (GitHub Pages 자동 업로드용)
# 환경변수에서 읽거나, 로컬 실행 시 config 파일에서 읽음 (암호화된 값 복호화)
# ============================================================
def decrypt_value(encoded_value):
    """base64로 암호화된 값을 복호화"""
    try:
        return base64.b64decode(encoded_value).decode('utf-8').strip()
    except:
        return encoded_value.strip()

def get_config_value(key):
    """환경변수 또는 config 파일에서 설정값 읽기 (암호화된 값 자동 복호화)"""
    # 환경변수 우선 (GitHub Actions용 - 암호화되지 않은 값)
    value = os.environ.get(key)
    if value:
        return value
    # 로컬 config 파일에서 읽기 (암호화된 값)
    config_path = os.path.join(os.path.dirname(__file__), 'config.txt')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 암호화된 키 (_ENC 접미사) 확인
                enc_key = f'{key}_ENC='
                if line.startswith(enc_key):
                    encrypted_value = line.split('=', 1)[1]
                    return decrypt_value(encrypted_value)
    return ''

# 보안 정책상 GitHub 토큰은 환경변수/Secrets로만 관리합니다.
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
GITHUB_REPO = 'khjgate/NewsLetter'  # GitHub 레포지토리 (소유자/레포명)
GITHUB_BRANCH = 'main'  # 브랜치명
GITHUB_PAGES_URL = 'https://khjgate.github.io/NewsLetter'  # GitHub Pages URL


def validate_github_token(token):
    """GitHub 토큰 유효성 및 저장소 접근 가능 여부를 사전 점검"""
    if not token:
        return False, 'GitHub 토큰이 비어 있습니다.'

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        repo_response = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}', headers=headers, timeout=SHORT_REQUEST_TIMEOUT)
    except requests.RequestException as error:
        return False, f'GitHub 저장소 확인 요청 실패: {error}'

    if repo_response.status_code == 401:
        return False, 'GitHub 토큰이 만료되었거나 잘못되었습니다. 환경변수 `GITHUB_TOKEN`(또는 CI Secrets)을 갱신하세요.'
    if repo_response.status_code == 404:
        return False, f'저장소 `{GITHUB_REPO}` 접근 권한이 없거나 저장소를 찾을 수 없습니다.'
    if repo_response.status_code != 200:
        return False, f'GitHub 저장소 접근 확인 실패: {repo_response.status_code} - {repo_response.text}'

    return True, 'GitHub 토큰 인증 성공'


def upload_to_github(file_content, file_name):
    """
    GitHub API를 사용하여 파일을 레포지토리에 업로드하는 함수
    파일이 이미 존재하면 업데이트, 없으면 새로 생성
    """
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{file_name}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # 파일 내용을 base64로 인코딩
    content_base64 = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    
    # 기존 파일이 있는지 확인 (SHA 값 필요)
    sha = None
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sha = response.json().get('sha')
    except:
        pass
    
    # 업로드 데이터 구성
    data = {
        'message': f'Update {file_name} - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}',
        'content': content_base64,
        'branch': GITHUB_BRANCH
    }
    
    # 기존 파일이 있으면 SHA 추가 (업데이트용)
    if sha:
        data['sha'] = sha
    
    # GitHub API로 파일 업로드/업데이트
    log_path = os.path.join(os.path.dirname(__file__), 'github_upload_log.txt')
    def log_print(msg):
        print(msg)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')

    is_valid_token, validation_message = validate_github_token(GITHUB_TOKEN)
    if not is_valid_token:
        log_print(f'❌ GitHub 인증 실패: {validation_message}')
        return False

    try:
        response = requests.put(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            log_print(f'✅ GitHub 업로드 성공: {file_name}')
            return True
        else:
            if response.status_code == 401:
                log_print('❌ GitHub 업로드 실패: 토큰이 만료되었거나 잘못되었습니다. 새 Personal Access Token으로 교체하세요.')
            else:
                log_print(f'❌ GitHub 업로드 실패: {response.status_code} - {response.text}')
            return False
    except Exception as e:
        log_print(f'❌ GitHub 업로드 오류: {e}')
        return False


# 1. 뉴스 수집 함수 (구글 뉴스 RSS 활용)
def collect_news():
    # 구글 뉴스 RSS를 이용하여 각 카테고리별 키워드로 뉴스 수집
    # 전주 월요일~일요일 사이의 뉴스 우선, 부족하면 2주/3주까지 확대
    import urllib.parse
    import warnings
    # 구글 뉴스 RSS를 이용하여 각 카테고리별 키워드로 뉴스 수집
    # 전주 월요일~일요일 사이의 뉴스 우선, 부족하면 2주/3주까지 확대
    import urllib.parse
    import warnings
    import re
    from datetime import datetime, timedelta
    from email.utils import parsedate_to_datetime
    warnings.filterwarnings('ignore')  # SSL 경고 무시
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 날짜 범위 계산 함수 (weeks_ago: 1=최근 7일, 2=최근 14일, 3=최근 21일)
    today = datetime.now()

    def get_week_range(weeks_ago):
        """오늘 기준 최근 N주(7일 단위) 범위 반환"""
        end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        start = (today - timedelta(days=7 * weeks_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, end

    # 1주~3주 전 날짜 범위 미리 계산
    week_ranges = {
        1: get_week_range(1),  # 최근 7일
        2: get_week_range(2),  # 최근 14일
        3: get_week_range(3),  # 최근 21일
    }

    print(f'📅 뉴스 수집 기간: 최근 3주 기준 ({week_ranges[3][0].strftime("%m/%d")}~{week_ranges[3][1].strftime("%m/%d")})')
    # 프롬프트/조회조건을 별도 파일에서 import
    from newsletter_prompt import trusted_sources, trusted_academic_sources, categories

    news_rss_healthcheck_url = 'https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko'
    if safe_get(news_rss_healthcheck_url, headers=headers, timeout=SHORT_REQUEST_TIMEOUT, verify=False) is None:
        return {category: ['뉴스 서버 연결이 지연되어 이번 회차 수집을 건너뜁니다.'] for category in categories}
    # 날짜 파싱 함수
    def parse_pub_date(pub_date_str):
        """RSS pubDate를 datetime으로 파싱"""
        try:
            return parsedate_to_datetime(pub_date_str)
        except:
            return None
    
    # 날짜가 특정 주 범위 내인지 확인하고 몇 주 전인지 반환
    def get_week_ago(pub_date_str):
        """날짜가 최근 몇 주 범위에 포함되는지 반환 (1, 2, 3 또는 None)"""
        pub_date = parse_pub_date(pub_date_str)
        if pub_date:
            pub_date_naive = pub_date.replace(tzinfo=None)
            for weeks_ago in [1, 2, 3]:
                start, end = week_ranges[weeks_ago]
                if start <= pub_date_naive <= end:
                    return weeks_ago
        return None
    
    # 날짜 포맷 함수 (몇 주 전인지 포함)
    def format_date_with_week(pub_date_str, weeks_ago):
        pub_date = parse_pub_date(pub_date_str)
        if pub_date:
            date_str = pub_date.strftime('%m/%d')
            if weeks_ago == 1:
                return date_str  # 최근 1주는 날짜만 표시
            elif weeks_ago == 2:
                return f"{date_str} 🕐2주전"
            elif weeks_ago == 3:
                return f"{date_str} 🕐3주전"
        return ''
    
    # 중복 제거를 위한 제목 정규화 함수
    def normalize_title(title: str) -> str:
        """언론사 접미사/대괄호 태그/불필요 구두점을 제거해 비교용 문자열로 정규화"""
        # 제목 끝에 붙는 " - 매체명" 패턴을 제거해 기사 본문 제목만 비교하도록 처리
        base_title = re.sub(r'\s+-\s+[^-]+$', '', title)
        # [포토], [단독] 같은 태그는 의미 중복 판단에 노이즈가 되므로 제거
        base_title = re.sub(r'\[[^\]]+\]', ' ', base_title)
        # 괄호 내부 매체명/부연 설명 제거 (예: (연합뉴스))
        base_title = re.sub(r'\([^\)]*\)', ' ', base_title)
        # 비교 안정성을 위해 영문 소문자화 및 불필요 특수문자 제거
        base_title = base_title.lower()
        base_title = re.sub(r'[^\w가-힣\s%]', ' ', base_title)
        # 다중 공백 정리
        return re.sub(r'\s+', ' ', base_title).strip()

    def tokenize_title(title: str) -> list[str]:
        """중복 판별 품질을 높이기 위해 제목을 의미 단위 토큰으로 분리"""
        # 조사/접속사/형식어 등 의미 구분력이 낮은 토큰은 제거해 과중복/미중복을 동시에 줄임
        stop_tokens = {
            '및', '또', '등', '관련', '대한', '위한', '통해', '기반', '올해', '내년', '이번',
            '발표', '강화', '확대', '추가', '결정', '소식', '뉴스', '단독', '속보', '포토',
            '기자', '에서', '으로', '하다', '한다', '했다', '된다', '되다'
        }
        normalized = normalize_title(title)
        raw_tokens = re.findall(r'[가-힣a-z0-9%]+', normalized)
        return [token for token in raw_tokens if len(token) >= 2 and token not in stop_tokens]

    # 유사 제목 체크 함수
    def is_duplicate(new_title: str, existing_titles: list[str]) -> bool:
        """문자열 유사도 + 토큰 자카드 유사도를 함께 사용해 동일 이슈 중복 노출 방지"""
        from difflib import SequenceMatcher

        new_normalized = normalize_title(new_title)
        new_tokens = set(tokenize_title(new_title))

        for existing in existing_titles:
            existing_normalized = normalize_title(existing)
            existing_tokens = set(tokenize_title(existing))

            if not new_normalized or not existing_normalized:
                continue

            # 완전 포함 관계(헤드라인 표현만 조금 다른 경우) 우선 차단
            if new_normalized in existing_normalized or existing_normalized in new_normalized:
                return True

            # 문장 수준 유사도: 헤드라인 어순이 유사한 재작성 기사 탐지
            if SequenceMatcher(None, new_normalized, existing_normalized).ratio() >= 0.74:
                return True

            # 토큰 수준 유사도: 핵심 키워드가 거의 동일한 경우(같은 이슈) 차단
            if new_tokens and existing_tokens:
                intersection_count = len(new_tokens & existing_tokens)
                union_count = len(new_tokens | existing_tokens)
                shorter_count = min(len(new_tokens), len(existing_tokens))
                jaccard_similarity = intersection_count / union_count if union_count else 0
                shorter_overlap_ratio = (
                    intersection_count / shorter_count if shorter_count else 0
                )

                # 동일 이슈 재작성 기사 대응:
                # - 공통 토큰이 충분히 많고(jaccard 완화)
                # - 또는 짧은 제목 기준으로 핵심 토큰의 절반 이상이 겹치면 중복 처리
                if (
                    (intersection_count >= 3 and jaccard_similarity >= 0.32)
                    or (intersection_count >= 2 and shorter_overlap_ratio >= 0.6)
                ):
                    return True

        return False

    # 한화그룹 섹션 전용 우선순위 키워드: 계열사/사업 뉴스를 상단 노출하기 위한 기준
    hot_news_affiliate_keywords = [
        '한화에어로스페이스', '한화오션', '한화솔루션', '한화생명', '한화시스템',
        '한화비전', '한화임팩트', '한화파워시스템', '한화파워', '한화큐셀',
        '한화호텔앤드리조트', '한화투자증권', '한화정밀기계', '한화로보틱스',
        '한화 건설', '한화 건설부문', '한화글로벌부문', '한화모멘텀',
    ]
    hot_news_business_keywords = [
        '투자', '수주', '협약', '파트너십', '실적', '매출', '영업이익', '계약',
        'MOU', 'R&D', '신사업', 'ESG', '친환경', '방산', '우주', '에너지',
    ]
    hot_news_eagles_keywords = [
        '한화 이글스', '한화이글스', '이글스', 'KBO', '선발', '불펜', '타선', '경기',
    ]

    def get_hot_news_priority_score(category: str, title: str, source: str) -> int:
        """한화 섹션 기사 노출 우선순위 점수 계산 (높을수록 우선)"""
        if category != '🔥 한화그룹 Hot News':
            return 0

        text = f'{title} {source}'
        score = 0

        # 계열사 실명 언급 시 최우선 가점
        if any(keyword in text for keyword in hot_news_affiliate_keywords):
            score += 5

        # 사업/투자/수주 등 핵심 비즈니스 문맥 가점
        if any(keyword in text for keyword in hot_news_business_keywords):
            score += 3

        # 스포츠(한화 이글스) 문맥은 허용하되 후순위로 배치
        if any(keyword in text for keyword in hot_news_eagles_keywords):
            score -= 3

        return score
    
    news = {}

    # ...카테고리별 검색 키워드는 newsletter_prompt.py에서 import...

    for category, keyword in categories.items():
        news_list = []
        collected_titles = []  # 중복 체크용 제목 리스트

        # RSS에서 모든 아이템 수집 (날짜 정보 포함)
        all_items_with_date = []

        try:
            # 모든 카테고리가 리스트 형태 - 여러 키워드로 검색하여 다양한 콘텐츠 수집
            keywords = keyword if isinstance(keyword, list) else [keyword]
            keywords = keywords[:MAX_NEWS_KEYWORDS_PER_CATEGORY]
            for kw in keywords:
                try:
                    encoded_keyword = urllib.parse.quote(kw)
                    url = f'https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko'
                    # timeout을 3초로 줄이고, 네트워크 오류 발생 시 해당 키워드는 건너뜀
                    res = safe_get(url, headers=headers, timeout=SHORT_REQUEST_TIMEOUT, verify=False)
                    if res is None:
                        continue
                    soup = BeautifulSoup(res.text, 'xml')
                    items = soup.find_all('item')

                    for item in items:
                        title = item.find('title').get_text(strip=True) if item.find('title') else ''
                        link = item.find('link').get_text(strip=True) if item.find('link') else ''
                        source = item.find('source').get_text(strip=True) if item.find('source') else ''
                        pub_date_str = item.find('pubDate').get_text(strip=True) if item.find('pubDate') else ''

                        weeks_ago = get_week_ago(pub_date_str)
                        # 학술기관 키워드가 제목/소스에 포함된 뉴스는 '학술기관 AX Trend'에서만 보여주고, 다른 카테고리에서는 제외
                        if any(ts in source or ts in title for ts in trusted_academic_sources):
                            continue
                        if weeks_ago:
                            all_items_with_date.append({
                                'title': title,
                                'link': link,
                                'source': source,
                                'pub_date_str': pub_date_str,
                                'weeks_ago': weeks_ago
                            })
                except Exception as e:
                    # 네트워크 오류, 타임아웃 등 발생 시 해당 키워드는 건너뜀
                    continue

            # 발행일 기본 정렬
            all_items_with_date.sort(
                key=lambda x: parse_pub_date(x['pub_date_str']) or datetime.min,
                reverse=True
            )

            # 한화그룹 섹션은 계열사/사업 뉴스 우선 노출을 위해 점수 기반 재정렬
            if category == '🔥 한화그룹 Hot News':
                all_items_with_date.sort(
                    key=lambda x: (
                        get_hot_news_priority_score(category, x['title'], x['source']),
                        parse_pub_date(x['pub_date_str']) or datetime.min,
                    ),
                    reverse=True,
                )

            # 신뢰할 수 있는 언론사 뉴스 먼저 수집 (10개까지)
            for item in all_items_with_date:
                if len(news_list) >= MAX_NEWS_ITEMS_PER_SECTION:
                    break
                title = item['title']
                link = item['link']
                source = item['source']
                pub_date_str = item['pub_date_str']
                weeks_ago = item['weeks_ago']

                # 중복 체크
                if is_duplicate(title, collected_titles):
                    continue

                # 신뢰 언론사만 필터링 (학술기관은 AX Trend에만 사용)
                is_trusted = any(ts in source or ts in title for ts in trusted_sources)
                if title and link and is_trusted:
                    # 날짜 표기 보완: weeks_ago가 None이어도 날짜는 항상 표시
                    date_display_str = format_date_with_week(pub_date_str, weeks_ago)
                    if not date_display_str:
                        # pub_date_str이 있으면 날짜만이라도 표시
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_date = parsedate_to_datetime(pub_date_str)
                            if pub_date:
                                date_display_str = pub_date.strftime('%m/%d')
                        except:
                            pass
                    date_display = f" <span style='color:#3b82f6;font-size:0.8em;'>[{date_display_str}]</span>" if date_display_str else ''
                    news_list.append(f"<a href='{link}' target='_blank'>{title}</a> <span style='color:#888;font-size:0.85em;'>({source})</span>{date_display}")
                    collected_titles.append(title)

            # 10개 미만이면 비신뢰 언론사 뉴스로 채우기
            if len(news_list) < MAX_NEWS_ITEMS_PER_SECTION:
                for item in all_items_with_date:
                    if len(news_list) >= MAX_NEWS_ITEMS_PER_SECTION:
                        break
                    title = item['title']
                    link = item['link']
                    source = item['source']
                    pub_date_str = item['pub_date_str']
                    weeks_ago = item['weeks_ago']

                    # 중복 체크
                    if is_duplicate(title, collected_titles):
                        continue

                    if title and link:
                        # 날짜 표기 보완: weeks_ago가 None이어도 날짜는 항상 표시
                        date_display_str = format_date_with_week(pub_date_str, weeks_ago)
                        if not date_display_str:
                            try:
                                from email.utils import parsedate_to_datetime
                                pub_date = parsedate_to_datetime(pub_date_str)
                                if pub_date:
                                    date_display_str = pub_date.strftime('%m/%d')
                            except:
                                pass
                        date_display = f" <span style='color:#3b82f6;font-size:0.8em;'>[{date_display_str}]</span>" if date_display_str else ''
                        news_list.append(f"<a href='{link}' target='_blank'>{title}</a> <span style='color:#888;font-size:0.85em;'>({source})</span>{date_display}")
                        collected_titles.append(title)

        except Exception as e:
            news_list.append(f'수집 오류: {e}')

        # 수집된 뉴스가 없으면 안내 메시지 추가
        if not news_list:
            news_list.append('최근 3주간 관련 뉴스가 없습니다.')

        news[category] = news_list


    # 학술기관 AX Trend 카테고리: trusted_academic_sources 키워드로 뉴스 10개까지 조회
    academic_news_list = []
    collected_titles = []
    all_items_with_date = []
    try:
        # 정치, 사회, 연예 등 비학술적 키워드 목록
        non_academic_keywords = [
            '정치', '대통령', '총리', '국회', '의원', '선거', '정당', '정부', '청와대',
            '사회', '사건', '사고', '범죄', '재판', '법원', '검찰', '경찰',
            '연예', '연예인', '가수', '배우', '방송', '드라마', '영화', '스포츠',
            '사망', '사건사고', '논란', '입학취소', '징계', '정치권', '정치인', '부정', '비리', '의혹', '논문 표절', '입시', '입학', '퇴출', '징계', '윤리', '조민', '김건희'
        ]
        for kw in trusted_academic_sources[:MAX_ACADEMIC_KEYWORDS]:
            encoded_keyword = urllib.parse.quote(kw)
            url = f'https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko'
            res = safe_get(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT, verify=False)
            if res is None:
                continue
            soup = BeautifulSoup(res.text, 'xml')
            items = soup.find_all('item')
            for item in items:
                title = item.find('title').get_text(strip=True) if item.find('title') else ''
                link = item.find('link').get_text(strip=True) if item.find('link') else ''
                source = item.find('source').get_text(strip=True) if item.find('source') else ''
                pub_date_str = item.find('pubDate').get_text(strip=True) if item.find('pubDate') else ''
                weeks_ago = get_week_ago(pub_date_str)
                # 비학술적 키워드가 제목에 포함되어 있으면 제외
                if any(bad_kw in title for bad_kw in non_academic_keywords):
                    continue
                if weeks_ago:
                    all_items_with_date.append({
                        'title': title,
                        'link': link,
                        'source': source,
                        'pub_date_str': pub_date_str,
                        'weeks_ago': weeks_ago
                    })
        # 발행일 기준 최신순 정렬
        all_items_with_date.sort(
            key=lambda x: parse_pub_date(x['pub_date_str']) or datetime.min,
            reverse=True
        )
        for item in all_items_with_date:
            if len(academic_news_list) >= MAX_NEWS_ITEMS_PER_SECTION: # 10개까지만
                break
            title = item['title']
            link = item['link']
            source = item['source']
            pub_date_str = item['pub_date_str']
            weeks_ago = item['weeks_ago']
            if is_duplicate(title, collected_titles):
                continue
            # 신뢰 학술기관 키워드가 제목 또는 소스에 포함된 경우만
            is_trusted_academic = any(ts in source or ts in title for ts in trusted_academic_sources)
            if title and link and is_trusted_academic:
                date_display_str = format_date_with_week(pub_date_str, weeks_ago)
                if not date_display_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        pub_date = parsedate_to_datetime(pub_date_str)
                        if pub_date:
                            date_display_str = pub_date.strftime('%m/%d')
                    except:
                        pass
                date_display = f" <span style='color:#3b82f6;font-size:0.8em;'>[{date_display_str}]</span>" if date_display_str else ''
                academic_news_list.append(f"<a href='{link}' target='_blank'>{title}</a> <span style='color:#888;font-size:0.85em;'>({source})</span>{date_display}")
                collected_titles.append(title)
        if not academic_news_list:
            academic_news_list.append('최근 3주간 관련 뉴스가 없습니다.')
    except Exception as e:
        academic_news_list.append(f'수집 오류: {e}')
    news['학술기관 AX Trend'] = academic_news_list

    # 카테고리 순서 재정렬: 해외 AI 신규뉴스 뒤에 학술기관 AX Trend, 그 다음 피지컬 AI
    ordered_keys = []
    for k in ['AX 활용 사례', '국내 AI 소식', '해외 AI 신규뉴스', '학술기관 AX Trend', '피지컬 AI', '금융사 AI 적용 사례 및 규제 완화 소식', '🔥 한화그룹 Hot News']:
        if k in news:
            ordered_keys.append(k)
    # 기존 news 딕셔너리의 순서 보장
    news = {k: news[k] for k in ordered_keys}

    return news
def collect_youtube_recommendations():
    # IT/AI 학습 목적의 건전한 영상만 수집 (공개 발표용)
    # 전주 월요일~일요일 사이 영상, 인기순 정렬
    import urllib.parse
    import warnings
    import re
    from datetime import datetime, timedelta
    warnings.filterwarnings('ignore')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 전주 월요일~일요일 날짜 범위 계산
    today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    
    print(f'📺 유튜브 수집 기간: {last_monday.strftime("%Y-%m-%d")} ~ {last_sunday.strftime("%Y-%m-%d")} (인기순)')
    
    # IT/AI 관련 키워드 필터 (이 키워드가 제목에 포함된 영상만 추천)
    it_ai_keywords = [
        'AI', '인공지능', 'GPT', 'ChatGPT', '챗GPT', '머신러닝', '딥러닝',
        '데이터', '분석', '자동화', 'AX', 'DX', '디지털', '전환',
        '로봇', '클라우드', '빅데이터', 'IT', 'RPA', '코딩', '프로그래밍',
        '알고리즘', '테크', '기술', '혁신', '스마트', '플랫폼',
        '비즈니스', '업무', '생산성', '효율', '솔루션'
    ]
    
    youtube_list = []
    
    # IT/AI 키워드 포함 여부 확인 함수
    def is_it_ai_content(title):
        title_lower = title.lower()
        for keyword in it_ai_keywords:
            if keyword.lower() in title_lower:
                return True
        return False
    
    # 날짜가 전주 범위 내인지 확인
    def is_within_week(date_str):
        try:
            if not date_str:
                return False
            # YYYY-MM-DD 형식
            pub_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
            return last_monday.date() <= pub_date.date() <= last_sunday.date()
        except:
            return False
    
    # 날짜 포맷 함수
    def format_date(date_str):
        try:
            if date_str:
                pub_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                return pub_date.strftime('%m/%d')
        except:
            pass
        return ''
    
    # 유튜브 검색 키워드는 newsletter_prompt.py에서 import
    from newsletter_prompt import youtube_search_keywords

    youtube_healthcheck_url = 'https://www.youtube.com/results?search_query=AI'
    if safe_get(youtube_healthcheck_url, headers=headers, timeout=SHORT_REQUEST_TIMEOUT, verify=False) is None:
        return []
    
    for keyword in youtube_search_keywords[:MAX_YOUTUBE_KEYWORDS]:
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            # YouTube 검색 - 이번 주 업로드 + 조회수순 정렬
            # sp=CAMSBAgCEAE: 이번 주 + 조회수순
            # sp=EgQIBRAB: 이번 주만
            url = f'https://www.youtube.com/results?search_query={encoded_keyword}&sp=EgQIBRAB'
            res = safe_get(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT, verify=False)
            if res is None:
                continue
            
            # YouTube 페이지에서 videoId와 viewCount 추출
            video_data = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"viewCountText":\{"simpleText":"조회수 ([0-9,]+)회"\}', res.text)
            
            # viewCount로 정렬이 안되면 기본 videoId만 추출
            if not video_data:
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
                video_data = [(vid, '0') for vid in video_ids[:5]]
            
            # 조회수 기준 내림차순 정렬
            video_data_sorted = sorted(video_data, key=lambda x: int(x[1].replace(',', '')) if x[1] else 0, reverse=True)
            
            for video_id, view_count in video_data_sorted[:3]:  # 상위 3개만 확인
                try:
                    # oEmbed API로 영상 정보 가져오기
                    oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
                    oembed_res = safe_get(oembed_url, timeout=SHORT_REQUEST_TIMEOUT, verify=False)
                    if oembed_res is None:
                        continue
                    
                    if oembed_res.status_code == 200:
                        oembed_data = oembed_res.json()
                        title = oembed_data.get('title', '')
                        channel = oembed_data.get('author_name', '유튜브')
                        thumbnail = f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg'
                        link = f'https://www.youtube.com/watch?v={video_id}'
                        
                        # IT/AI 관련 키워드가 포함된 영상만 추가
                        if title and is_it_ai_content(title):
                            # 중복 체크
                            if any(item['title'] == title for item in youtube_list):
                                continue
                            
                            # 조회수 파싱
                            views = int(view_count.replace(',', '')) if view_count else 0
                            
                            youtube_list.append({
                                'channel': channel,
                                'title': title,
                                'link': link,
                                'thumbnail': thumbnail,
                                'date': '',  # 검색 결과에서는 날짜 추출 어려움
                                'views': views
                            })
                            break  # 키워드당 1개만
                except:
                    continue
        except:
            continue
    
    # 조회수 기준 내림차순 정렬
    youtube_list.sort(key=lambda x: x.get('views', 0), reverse=True)
    
    # 중복 제거 및 상위 5개만 반환
    seen_titles = set()
    unique_list = []
    for item in youtube_list:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_list.append(item)
    
    return unique_list[:5]  # 최대 5개만 반환

# 2. HTML 본문 생성 함수
def generate_html(news, youtube_recommendations=None, email_version=True):
    """
    HTML 뉴스레터 생성
    email_version=True: 이메일용 (단색 배경, 호환성 우선)
    email_version=False: 브라우저용 (그라데이션 배경, 풀 디자인)
    """
    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    # 이메일 버전과 브라우저 버전의 배경 스타일 분리
    if email_version:
        header_bg = 'background-color:#1e3a8a;'
        subheader_bg = 'background-color:#1e3a8a;'
        footer_bg = 'background-color:#1e3a8a;'
        banner_bg = 'background-color:#f7931e;'  # 이메일용 단색
    else:
        header_bg = 'background:linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);'
        subheader_bg = 'background:linear-gradient(90deg, #1e3a8a 0%, #2563eb 100%);'
        footer_bg = 'background:linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);'
        banner_bg = 'background:linear-gradient(90deg, #ff6b35 0%, #f7931e 100%);'  # 브라우저용 그라데이션
    
    browser_banner_html = ""
    if email_version:
        browser_banner_html = """
        <table width='100%' cellpadding='0' cellspacing='0' border='0' style='max-width:1000px; width:100%; margin:0 auto 15px auto;'>
            <tr>
                <td align='center' bgcolor='#f7931e' style='background-color:#f7931e; border-radius:12px; mso-padding-alt:15px 20px;'>
                    <a href='{{web_version_url}}' target='_blank' style='display:block; padding:15px 20px; color:#ffffff; font-family:Segoe UI,Arial,sans-serif; font-size:15px; font-weight:bold; text-decoration:none; text-align:center;'>
                        &#10024; 더 멋진 디자인으로 보기 - 클릭하여 웹 브라우저에서 열기 &#8594;
                    </a>
                </td>
            </tr>
        </table>
        """

    html = f"""
    <style>
        .date-badge {{{{
            display: none !important;
        }}}}
        .content-cell {{{{
            padding: 15px !important;
        }}}}
        .section-title {{{{
            font-size: 1em !important;
        }}}}
        .news-item {{{{
            font-size: 14px !important;
        }}}}
        .youtube-thumb {{{{
            width: 120px !important;
            height: 68px !important;
        }}}}
        .youtube-title {{{{
            font-size: 13px !important;
        }}}}
        .footer-cell {{{{
            padding: 15px !important;
        }}}}
        .logo-badge {{{{
            padding: 8px 12px !important;
        }}}}
        .logo-text {{{{
            font-size: 14px !important;
        }}}}
    </style>
    </head>
    <body style='font-family:Segoe UI,Arial,sans-serif; background-color:#f5f5f5; margin:0; padding:10px; word-wrap:break-word; word-break:break-word;'>
        {browser_banner_html}
        <!-- 뉴스레터 헤더 배너 -->
        <table class='email-container' width='100%' cellpadding='0' cellspacing='0' border='0' style='max-width:1000px; width:100%; margin:0 auto;'>
            <tr>
                <td class='header-cell' style='{header_bg} border-radius:16px 16px 0 0; padding:20px;'>
                    <!-- 로고 + 날짜 한 줄 -->
                    <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                        <tr>
                            <td style='vertical-align:middle;'>
                                <div style='display:inline-block; background:#fff; border-radius:10px; padding:8px 12px;'>
                                    <span style='font-size:20px;'>🚀</span>
                                    <span style='font-size:14px; font-weight:700; color:#1e3a8a;'>Hanwha Systems/ICT</span>
                                </div>
                            </td>
                            <td style='text-align:right; vertical-align:middle;'>
                                <span style='color:#fff; font-size:13px; background:rgba(255,255,255,0.2); padding:6px 12px; border-radius:8px;'>📅 {today}</span>
                            </td>
                        </tr>
                    </table>
                    <!-- 메인 타이틀 -->
                    <h1 style='color:#ffffff; font-size:24px; font-weight:800; margin:15px 0 5px 0;'>
                        AX / IT 트랜드 뉴스레터
                    </h1>
                    <p style='color:rgba(255,255,255,0.85); font-size:12px; margin:0;'>
                        AI Transformation & Digital Innovation Weekly Digest
                    </p>
                </td>
            </tr>
            <!-- 서브 헤더 바 -->
            <tr>
                <td class='content-cell' style='{subheader_bg} padding:10px 25px;'>
                    <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                        <tr>
                            <td class='header-subtitle' style='color:rgba(255,255,255,0.9); font-size:11px;'>
                                📊 AX &nbsp;|&nbsp; 🤖 AI &nbsp;|&nbsp; 🌍 글로벌 &nbsp;|&nbsp; 🔥 한화
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <!-- 본문 컨테이너 -->
            <tr>
                <td class='content-cell' style='background:#ffffff; padding:20px 25px;'>
    """
    # 카테고리별 아이콘 매핑
    section_icons = {
        'AX 활용 사례': '⚡',
        '국내 AI 소식': '🇰🇷',
        '해외 AI 신규뉴스': '🌍',
        '피지컬 AI': '🤖',
        '금융사 AI 적용 사례 및 규제 완화 소식': '💰',
        '🔥 한화그룹 Hot News': '🔥'
    }
    
    for section, items in news.items():
        icon = section_icons.get(section, '📰')
        # 한화그룹 뉴스는 특별 스타일
        if '한화' in section:
            html += f"""
            <div style='background-color:#ff6b35; border-radius:12px; padding:20px; margin:25px 0 15px 0;'>
                <h2 class='section-title' style='color:#fff; margin:0; font-size:1.3em;'>{section}</h2>
            </div>
            <ul style='list-style:none; padding:0; margin:0;'>
            """
        else:
            html += f"""
            <div style='border-left:4px solid #3b82f6; padding-left:15px; margin:25px 0 15px 0;'>
                <h2 class='section-title' style='color:#1e3a8a; margin:0; font-size:1.2em;'>{icon} {section}</h2>
            </div>
            <ul style='list-style:none; padding:0; margin:0;'>
            """
        for item in items:
            html += f"<li class='news-item' style='padding:8px 0; border-bottom:1px solid #f0f0f0; word-wrap:break-word; word-break:break-word; overflow-wrap:break-word;'>{item}</li>"
        html += "</ul>"
    
    # 유튜버 추천 섹션 추가 (썸네일 Base64 인라인 포함)
    if youtube_recommendations:
        html += """
        <div style='margin-top:40px; padding:25px; background:#f8f9fa; border-radius:16px;'>
            <h2 style='color:#333; margin-top:0; margin-bottom:8px; font-size:1.4em;'>🎬 추천 AX 영상</h2>
            <p style='color:#666; font-size:0.9em; margin-bottom:20px;'>이번 주 주목할 만한 AI/AX 관련 유튜브 콘텐츠를 추천합니다.</p>
            <table cellpadding='0' cellspacing='0' border='0' width='100%'>
        """
        for idx, video in enumerate(youtube_recommendations, 1):
            date_str = video.get('date', '')
            thumbnail_url = video.get('thumbnail', '')
            
            # 썸네일 이미지를 Base64로 인코딩
            thumbnail_base64 = ''
            if thumbnail_url:
                try:
                    import warnings
                    warnings.filterwarnings('ignore')
                    img_response = safe_get(thumbnail_url, timeout=SHORT_REQUEST_TIMEOUT, verify=False)
                    if img_response is None:
                        continue
                    if img_response.status_code == 200:
                        thumbnail_base64 = base64.b64encode(img_response.content).decode('utf-8')
                except:
                    pass
            
            # 썸네일이 있으면 이미지 표시, 없으면 대체 아이콘
            if thumbnail_base64:
                img_html = f"<img class='youtube-thumb' src='data:image/jpeg;base64,{thumbnail_base64}' alt='썸네일' style='width:160px; height:90px; object-fit:cover; border-radius:8px; display:block;'>"
            else:
                img_html = "<div class='youtube-thumb' style='width:160px; height:90px; background-color:#ff0000; border-radius:8px; display:table-cell; vertical-align:middle; text-align:center; color:#fff; font-size:32px;'>▶</div>"
            
            html += f"""
                <tr>
                    <td style='padding:10px 0; border-bottom:1px solid #eee;'>
                        <table cellpadding='0' cellspacing='0' border='0' width='100%'>
                            <tr>
                                <td width='170' valign='top'>
                                    <a href='{video['link']}' target='_blank'>{img_html}</a>
                                </td>
                                <td valign='top' style='padding-left:15px;'>
                                    <a class='youtube-title' href='{video['link']}' target='_blank' style='text-decoration:none; color:#222; font-size:0.95em; font-weight:600; line-height:1.4;'>{video['title']}</a>
                                    <div style='margin-top:8px;'>
                                        <span style='color:#ff0000; font-size:0.8em; font-weight:500;'>{video['channel']}</span>
                                    </div>
                                    <div style='color:#888; font-size:0.75em; margin-top:4px;'>{date_str}</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            """
        html += """
            </table>
        </div>
        """
    
    html += f"""
                </td>
            </tr>
            <!-- 푸터 -->
            <tr>
                <td class='footer-cell' style='{footer_bg} border-radius:0 0 16px 16px; padding:20px 25px;'>
                    <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                        <tr>
                            <td style='color:#ffffff; font-size:11px; line-height:1.6; vertical-align:middle;'>
                                <div class='logo-badge' style='font-weight:600; font-size:13px; margin-bottom:8px;'>🚀 Hanwha Systems/ICT</div>
                                매주 월요일 오전 8시 자동 발송<br>
                                AI/AX 트랜드 & 한화그룹 뉴스
                            </td>
                            <td style='color:rgba(255,255,255,0.7); font-size:10px; text-align:right; vertical-align:middle;'>
                                Copyright 2026. hanwhasystem Inc. All rights reserved.
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html

# 3. 이메일 발송 함수
def send_email(html):
    # Gmail SMTP 설정
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    
    # 이메일 설정 (암호화된 config 파일 또는 환경변수에서 읽음)
    sender_email = get_config_value('SENDER_EMAIL')
    sender_password = get_config_value('EMAIL_PASSWORD')
    receiver_email = get_config_value('RECEIVER_EMAIL')

    # 메일 메시지 구성
    msg = MIMEMultipart('alternative')
    # 한글 제목을 위한 Header 적용
    msg['Subject'] = Header('AX / IT 트랜드 뉴스레터', 'utf-8')
    # 발신자 이름 및 표시 이메일 설정 (암호화된 config에서 읽음)
    sender_name = 'AX / IT Trend for U'
    display_email = get_config_value('DISPLAY_EMAIL')
    msg['From'] = f'{sender_name} <{display_email}>'
    msg['To'] = receiver_email
    # 한글 인코딩 오류 방지를 위해 charset을 utf-8로 명시
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    # SMTP 서버 연결 및 메일 발송
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        # 한글 인코딩 문제 방지를 위해 as_bytes()로 전송
        server.sendmail(sender_email, receiver_email, msg.as_bytes())
        server.quit()
        print('뉴스레터 발송 완료!')
    except Exception as e:
        print('메일 발송 오류:', e)


def validate_email_config():
    """메일 발송에 필요한 설정값 누락 여부를 확인"""
    required_keys = [
        'SENDER_EMAIL',
        'EMAIL_PASSWORD',
        'RECEIVER_EMAIL',
        'DISPLAY_EMAIL'
    ]
    missing_keys = [key for key in required_keys if not get_config_value(key)]

    if missing_keys:
        print(f'필수 메일 설정이 누락되었습니다: {", ".join(missing_keys)}')
        return False

    return True


def run_lowpacket_check():
    """프로그램 시작 전 `LowPacket.py`를 실행하여 패킷 점검을 수행"""
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print('Skipping LowPacket check in GitHub Actions.')
        return True

    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(current_dir)
    lowpacket_path = os.path.join(workspace_dir, 'LowPacket', 'LowPacket.py')
    lowpacket_prompt = '뉴스레터 자동 발송 프로그램 실행 전 패킷 점검'

    if not os.path.exists(lowpacket_path):
        print(f'패킷 점검 파일을 찾을 수 없습니다: {lowpacket_path}')
        return False

    print('패킷 점검을 시작합니다...')

    try:
        subprocess.run([sys.executable, lowpacket_path, lowpacket_prompt], check=True)
        print('패킷 점검이 완료되었습니다.')
        return True
    except subprocess.CalledProcessError as error:
        print(f'패킷 점검 실행 중 오류가 발생했습니다: {error}')
        return False


def backup_existing_preview(preview_path):
    """기존 미리보기 파일이 있으면 `Bak` 폴더로 이동하여 누적 백업"""
    if not os.path.exists(preview_path):
        return None

    preview_dir = os.path.dirname(preview_path)
    backup_dir = os.path.join(preview_dir, 'Bak')
    os.makedirs(backup_dir, exist_ok=True)

    file_name = os.path.basename(preview_path)
    file_stem, file_ext = os.path.splitext(file_name)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'{file_stem}_{timestamp}{file_ext}')
    duplicate_index = 1

    # 같은 초에 여러 번 저장될 때도 파일명이 겹치지 않도록 보정
    while os.path.exists(backup_path):
        backup_path = os.path.join(backup_dir, f'{file_stem}_{timestamp}_{duplicate_index}{file_ext}')
        duplicate_index += 1

    shutil.move(preview_path, backup_path)
    return backup_path

if __name__ == '__main__':
    run_lowpacket_check()
    if not validate_email_config():
        sys.exit(1)

    news = collect_news()
    # 카테고리별 수집 결과를 콘솔에 출력
    for section, items in news.items():
        print(f'[{section}]')
        for item in items:
            print(item)
        print('-' * 40)

    # 유튜브 추천 영상 수집
    print('[유튜브 추천 영상]')
    youtube_recommendations = collect_youtube_recommendations()
    for video in youtube_recommendations:
        print(f"▶ {video['title']} ({video['channel']})")
        print(f"   썸네일: {video.get('thumbnail', 'N/A')}")
    print('-' * 40)

    # 미리보기용 HTML 파일 경로 설정 (현재 스크립트 위치 기준)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    preview_path = os.path.join(script_dir, 'newsletter_preview_auto.html')

    # 1. 브라우저 버전 HTML 생성 (그라데이션 적용)
    html_browser = generate_html(news, youtube_recommendations, email_version=False)

    web_version_url = f'{GITHUB_PAGES_URL}/newsletter_preview_auto.html'
    html_browser = html_browser.replace('{{web_version_url}}', web_version_url)

    backup_path = backup_existing_preview(preview_path)
    if backup_path:
        print(f'기존 미리보기 백업 완료: {backup_path}')

    # 브라우저 버전 HTML 파일로 로컬 저장
    with open(preview_path, 'w', encoding='utf-8') as f:
        f.write(html_browser)
    print(f'브라우저 버전 HTML 저장 완료: {preview_path}')

    # 웹브라우저로 자동 오픈
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        webbrowser.open('file://' + preview_path)

    # GitHub Pages용 HTML 업로드 시도
    github_uploaded = False
    if GITHUB_TOKEN:
        github_uploaded = upload_to_github(html_browser, 'newsletter_preview_auto.html')
    else:
        print('GitHub 토큰이 없어 웹 버전 업로드를 건너뜁니다.')

    if not github_uploaded:
        print('웹 버전 업로드에 실패하여 기본 GitHub Pages URL을 메일 본문에 사용합니다.')

    # 2. 이메일 버전 HTML 생성 및 발송
    html_email = generate_html(news, youtube_recommendations, email_version=True)
    html_email = html_email.replace('{{web_version_url}}', web_version_url)
    send_email(html_email)
