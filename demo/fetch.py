"""공고 주소 한 쪽만 받아 본문 글로 바꾼다. 막히면 우회하지 않고 까닭을 돌려준다.

지키는 것: 처음 받은 주소의 robots.txt 를 먼저 보고 막히면 받지 않는다. 공고 쪽 요청은 한 번만 보내고,
넘겨주기(3xx)는 따라가되 넘겨받은 주소의 robots.txt 는 다시 보지 않는다. User-Agent 는 아래 하나.
인증서 검사를 끄지 않는다. 쿠키를 보내지 않고 로그인을 흉내 내지 않는다. 쪽 안의 링크는 따라가지 않는다.
https 만 받고, 내부망·자기 자신(사설, loopback, link-local) 주소는 첫 주소든 넘겨주기 중간이든 열지 않는다.
기용/demo/fetch.py 에서 옮겨 왔다. 화면 문구(MESSAGES)만 해요체로 바꿨다.
"""
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.request
import urllib.robotparser
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

UA = "Mozilla/5.0 (research collector)"
MIN_BODY = 200      # 본문이 이보다 짧으면 자바스크립트로만 그려지는 쪽으로 본다
MAX_BYTES = 3_000_000


class Blocked(Exception):
    """받지 못한 까닭. reason 은 화면이 쉬운 말로 바꿔 보여 준다."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


MESSAGES = {
    "address": "공고 주소는 https:// 로 시작해야 해요. 주소를 다시 확인해 볼까요?",
    "private": "이 주소는 열 수 없어요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "robots": "이 사이트는 내용을 가져가지 못하게 막혀 있어요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "robots_unknown": "이 사이트가 내용을 가져가도 되는지 알 수 없었어요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "http": "사이트가 열리지 않았어요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "login": "로그인해야 볼 수 있는 페이지예요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "script": "이 페이지는 내용을 가져올 수 없는 방식으로 만들어져 있어요. 공고 내용을 복사해 붙여넣어 볼까요?",
    "type": "공고 글이 있는 페이지가 아니에요. 파일이면 끌어다 놓아 볼까요?",
    "network": "사이트에 연결하지 못했어요. 잠시 뒤 다시 하거나 내용을 붙여넣어 볼까요?",
}


def check_host(url):
    """https 이고, 이름이 가리키는 주소가 모두 바깥(공인) 주소일 때만 통과. 아니면 Blocked.
    이 서버가 내부망(127.0.0.1, 10.x, 169.254.169.254 같은 곳)을 대신 열어 주는 통로가 되지 않게 한다."""
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname:
        raise Blocked("address", url)
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or 443, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError) as e:
        raise Blocked("network", type(e).__name__)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise Blocked("private", f"{u.hostname} → {ip}")


class _CheckRedirect(urllib.request.HTTPRedirectHandler):
    """넘겨주기(3xx)를 따라갈 때마다 다음 주소도 check_host 로 본다."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# 프록시 설정을 타지 않게 ProxyHandler({}) 를 넣는다. 쿠키 처리기는 넣지 않는다
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _CheckRedirect())


def _open(req, timeout):
    """바깥으로 나가는 요청은 모두 여기를 지난다: 첫 주소와 넘겨주기마다 주소 검사."""
    check_host(req.full_url)
    return _OPENER.open(req, timeout=timeout)


def _robots_ok(url):
    p = urlparse(url)
    rp = urllib.robotparser.RobotFileParser(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        with _open(urllib.request.Request(rp.url, headers={"User-Agent": UA}), timeout=15) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:     # RFC 9309: 4xx 는 규칙 없음, 5xx 는 모두 막힘
        if e.code >= 500:
            raise Blocked("robots_unknown", f"robots.txt 서버 오류 {e.code}")
        return True
    except OSError as e:
        raise Blocked("robots_unknown", type(e).__name__)
    return rp.can_fetch(UA, url)


FOCUS = re.compile(r"job[-_ ]?(detail|description|posting|content|view)|description|recruit[-_ ]?(detail|view|content)|posting[-_ ]?(detail|body)", re.I)


class _Text(HTMLParser):
    """본문 글을 모으면서, 공고 본문으로 보이는 요소(main, article, id·class 에 job-detail, description 같은 낱말)의 글은 따로도 모은다.
    메뉴, 머리, 바닥 글이 공고 문장으로 섞이지 않게 하려는 것이다."""
    BLOCK = {"p", "div", "br", "tr", "ul", "ol", "table", "section", "article", "main", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "dt", "dd"}
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg", "form"}

    def __init__(self):
        super().__init__()
        self.out, self.skip, self.title, self.in_title = [], 0, "", False
        self.ld, self.in_ld, self.password = [], False, False
        self.open, self.focus = [], []      # 열린 본문 후보 [태그, 깊이, 글 조각들], 닫힌 후보의 글

    def _emit(self, piece):
        self.out.append(piece)
        for o in self.open:
            o[2].append(piece)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for o in self.open:
            o[1] += o[0] == tag
        if tag in ("main", "article") or FOCUS.search(f'{a.get("id", "")} {a.get("class", "")}'):
            self.open.append([tag, 1, []])
        if tag == "script" and a.get("type") == "application/ld+json":
            self.in_ld = True
        if tag == "input" and a.get("type") == "password":
            self.password = True
        self.in_title = tag == "title"
        self.skip += tag in self.SKIP
        self._emit("\n- " if tag == "li" else "\n" if tag in self.BLOCK else "")

    def handle_endtag(self, tag):
        self.in_ld = False
        self.in_title = False
        self.skip -= tag in self.SKIP and self.skip > 0
        self._emit("\n" if tag in self.BLOCK or tag == "li" else "")
        for o in self.open:
            o[1] -= o[0] == tag
        self.focus += ["".join(o[2]) for o in self.open if o[1] == 0]
        self.open = [o for o in self.open if o[1] > 0]

    def handle_data(self, data):
        if self.in_ld:
            self.ld.append(data)
        elif self.in_title:
            self.title += data
        elif not self.skip:
            self._emit(data)


def _lines(raw):
    rows = [re.sub(r"[ \t ​﻿]+", " ", x).strip() for x in raw.splitlines()]
    out = []
    for x in rows:
        if out and out[-1] == "-":
            out[-1] = f"- {x}" if x else "-"
        elif x:
            out.append(x)
    return "\n".join(x for x in out if x != "-")


def _job_posting(ld_blocks):
    """쪽에 심어 둔 JobPosting 구조 자료(schema.org)가 있으면 그 설명이 가장 깨끗한 본문이다."""
    for block in ld_blocks:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for d in data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []:
            if isinstance(d, dict) and d.get("@type") == "JobPosting" and d.get("description"):
                return d.get("title", ""), d["description"]
    return None


def page_text(markup):
    """HTML → (제목, 본문 글, 비밀번호 칸이 있었나)."""
    p = _Text()
    p.feed(markup)
    p.close()
    title = " ".join(p.title.split())
    jp = _job_posting(p.ld)
    if jp:
        inner = _Text()
        inner.feed(unescape(jp[1]))
        inner.close()
        return jp[0] or title, _lines("".join(inner.out)), p.password
    whole = _lines("".join(p.out))
    parts = [_lines(x) for x in p.focus + ["".join(o[2]) for o in p.open]]
    parts = [x for x in parts if len(x) >= MIN_BODY]
    # 본문 후보 가운데 가장 짧은 것(가장 안쪽)을 고른다. 다만 전체의 1/4 은 넘어야 공고 일부만 잘라 오지 않는다
    body = min((x for x in parts if len(x) * 4 >= len(whole)), key=len, default=whole)
    return title, body, p.password


def fetch(url):
    """공고 주소 → {url, host, title, text}. 받지 못하면 Blocked."""
    u = urlparse(url.strip())
    url = u.geturl()
    check_host(url)
    if not _robots_ok(url):
        raise Blocked("robots")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with _open(req, timeout=20) as r:
            kind = r.headers.get_content_type()
            body = r.read(MAX_BYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")
            final = r.geturl()
    except urllib.error.HTTPError as e:
        raise Blocked("login" if e.code in (401, 407) else "http", f"HTTP {e.code}")
    except OSError as e:
        raise Blocked("network", type(e).__name__)
    if kind not in ("text/html", "application/xhtml+xml"):
        raise Blocked("type", kind)
    if re.search(r"/(login|signin|sign-in|auth)\b", urlparse(final).path, re.I):
        raise Blocked("login", "로그인 쪽으로 넘어감")
    title, text, password = page_text(body)
    if password and len(text) < 1500:
        raise Blocked("login", "비밀번호 칸")
    if len(text) < MIN_BODY:
        raise Blocked("script", f"본문 {len(text)}자")
    return {"url": url, "host": u.netloc, "title": title, "text": text}


def message(e):
    return MESSAGES[e.reason]
