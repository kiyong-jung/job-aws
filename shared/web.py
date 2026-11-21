"""웹에서 받기. 모듈 여럿이 함께 쓴다.

polite_get   채용 사이트와 프로젝트 주소를 읽는다. robots.txt 를 따르고 호스트마다 초당 1번, 다시 시도하지 않는다 (공고 수집, 프로젝트 주소 확인).
fetch        공개 목록과 GitHub API 를 읽는다. GITHUB_TOKEN 이 있으면 붙인다 (은행 만들기).
readme       GitHub 저장소의 README 원문.
html_text    HTML → 평문. strip_tags 는 짧은 요약용으로 태그만 지운다.
"""
import html
import os
import re
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from urllib.parse import urlparse

RAW = "https://raw.githubusercontent.com/{}/HEAD/README.md"
UA = {"User-Agent": "Mozilla/5.0 (research collector)"}
LIST_UA = {"User-Agent": "Mozilla/5.0 (curri material bank; hackathon research)"}
_robots, _last, _lock = {}, {}, threading.Lock()


class Skipped(Exception):
    """요청하지 않은 주소. robots.txt 가 막았거나, robots.txt 를 읽지 못해 확인하지 못한 경우."""


def allowed(url):
    host = urlparse(url).netloc
    with _lock:
        if host not in _robots:
            rp = urllib.robotparser.RobotFileParser(f"https://{host}/robots.txt")
            try:
                with urllib.request.urlopen(urllib.request.Request(rp.url, headers=UA), timeout=15) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:   # RFC 9309: 4xx(없음, 401·403 포함)는 규칙이 없는 것, 5xx 는 모두 막힌 것으로 본다
                if e.code >= 500:
                    rp.disallow_all = True
                    rp.unverified = f"robots.txt 가 서버 오류 {e.code}"
                else:
                    rp.parse([])
            except OSError as e:      # 인증서·연결 오류. 규칙을 모르니 요청하지 않되, 막힌 것과 구분해 적는다
                rp.disallow_all = True
                rp.unverified = f"{type(e).__name__}: {e}"
            _robots[host] = rp
    return _robots[host].can_fetch(UA["User-Agent"], url)


def polite_get(url, data=None, headers=None):
    """호스트마다 초당 1번, 시간 제한 30초, 다시 시도하지 않는다."""
    if not allowed(url):
        if unverified := getattr(_robots[urlparse(url).netloc], "unverified", None):
            raise Skipped(f"robots.txt 를 확인하지 못해 요청하지 않음 ({unverified}): {url}")
        raise Skipped(f"robots.txt 가 막음: {url}")
    host = urlparse(url).netloc
    with _lock:
        wait = _last.get(host, 0) + 1.0 - time.time()
        _last[host] = time.time() + max(wait, 0)
    time.sleep(max(wait, 0))
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "td", "th", "ul", "ol", "table", "section", "article", "h1", "h2", "h3", "h4",
             "h5", "h6", "hr"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style")
        self.out.append("\n- " if tag == "li" else "\n" if tag in self.BLOCK else "")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style")
        self.out.append("\n" if tag in self.BLOCK or tag == "li" else "")

    def handle_data(self, data):
        self.out.append("" if self.skip else data)


def html_text(markup):
    """HTML → 평문. 문단·제목은 줄바꿈으로 나누고 목록 항목은 '- ' 줄로 살린다 (자격요건 같은 머리줄이 한 줄을 차지한다)."""
    p = _Text()
    p.feed(html.unescape(markup) if "&lt;" in markup else markup)
    p.close()
    lines = [re.sub(r"[ \t\u00a0\u200b\ufeff]+", " ", x).strip() for x in "".join(p.out).splitlines()]
    out = []
    for x in lines:
        if out and out[-1] == "-":
            out[-1] = f"- {x}" if x else "-"
        elif x:
            out.append(x)
    return "\n".join(x for x in out if x != "-")


def readme(repo):
    with urllib.request.urlopen(RAW.format(repo), timeout=60) as r:
        return r.read().decode("utf-8")



def fetch(url):
    # 없으면 시간당 60번 한도에 걸린다
    token = os.environ.get("GITHUB_TOKEN") if url.startswith("https://api.github.com/") else None
    headers = {**LIST_UA, **({"Authorization": f"Bearer {token}"} if token else {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_tags(html_text, n=200):
    s = re.sub(r"<[^>]+>", " ", html.unescape(html_text or ""))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()[:n]
