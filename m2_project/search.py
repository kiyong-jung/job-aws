"""① 찾기: 공고 → 샘플 후보 목록.

LLM 이 공고와 역량을 읽고 영어 검색어와 대표 논문·저장소 이름을 한 번에 낸다.
검색어 끝에 'arxiv' 나 'github' 를 붙여 일반 웹 검색으로 찾는다 (문장 그대로 찾을 수 있다).
검색 엔진은 BRAVE_API_KEY 가 있으면 Brave Search API, 없으면 DuckDuckGo (키 필요 없음, robots.txt 가 허락하지만 자주 부르면 막힌다).
찾은 논문의 제목·초록은 arXiv API, 저장소의 별 수·설명은 GitHub API 로 채운다. 여러 검색에 앞쪽으로 걸린 후보가 위.
검색 결과는 outputs/project/<공고>.search.json 에 저장해 다시 돌리면 그대로 쓴다.
"""
import json
from pathlib import Path
import re
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

import requests

from shared import config, llm
from shared.llm import STR, obj

MODEL = "global.anthropic.claude-sonnet-4-6"
PROMPT = Path(__file__).parent / "prompt"   # 지시문은 이 폴더의 txt 로 관리한다
UA = "Mozilla/5.0 (research collector)"
GAP = {"api.search.brave.com": 1.1, "html.duckduckgo.com": 5.0, "api.github.com": 1.0, "export.arxiv.org": 3.5}   # Brave 무료 크레딧은 초당 1회, arXiv 는 3초에 한 번
# export.arxiv.org/robots.txt 는 전부 막지만 arXiv API 이용약관(info.arxiv.org/help/api/tou.html)이 API 사용을 허락한다
TERMS_PERMIT = {"export.arxiv.org", "api.search.brave.com"}   # Brave 는 자동 호출용 유료 API (키로 부른다)
BRAVE_MONTHLY = int(config.get("BRAVE_MONTHLY", "1000"))   # 매달 무료 크레딧 5달러 = 약 1,000번. 넘으면 멈춘다
BRAVE_LOG = config.OUTPUTS / "brave_calls.tsv"

COUNTS = {"paper_queries": 8, "repo_queries": 8, "paper_names": 8, "repo_names": 5}
QUERY_SYSTEM = (PROMPT / "query.txt").read_text("utf-8").format(**COUNTS)
# 구조화 출력은 minItems 2 이상을 받지 않아, 칸 1..n 을 가진 객체로 개수를 못 박는다
QUERY_SCHEMA = obj({k: obj({str(i): STR for i in range(1, n + 1)}) for k, n in COUNTS.items()})
MIN_STARS = 100   # 신빙성 기준표와 같은 문턱. 이보다 적은 저장소는 후보에서 뺀다


def section_of(c, case):
    """역량의 근거 문장이 공고의 어느 구역(자격요건·담당업무·우대사항·팀메시지·부서소개)에 있나."""
    first = c["evidence_id"].split(",")[0].strip()
    return next((s["section"] for s in case["sentences"] if s["id"] == first), "")


def posting_text(case):
    """공고 문장과 역량을 모델에게 줄 글로. 역량마다 유형, 근거 구역, 필수·우대 표시를 붙인다."""
    lines = [f'[{s["id"]} {s["section"]}] {s["text"]}' for s in case["sentences"] if s.get("section") != "전형"]
    comps = [f'{c["id"]} {c["name"]} | 유형 {c["type"]} | 구역 {section_of(c, case)} | {c["priority"]} | 근거 {c["evidence_id"]}'
             for c in case["competencies"]]
    return (f'<posting title="{case["posting"].get("title", "")}">\n' + "\n".join(lines) + "\n</posting>\n"
            "<competencies>\n" + "\n".join(comps) + "\n</competencies>")


_last, _robots = {}, {}


def get(url, params=None, headers=None, tries=5):
    """공식 API 하나를 부른다. robots.txt 를 지키고, 호스트마다 간격을 두고, 속도 제한이면 기다렸다 다시 부른다."""
    host = urlparse(url).netloc
    if host not in _robots and host not in TERMS_PERMIT:
        rp = urllib.robotparser.RobotFileParser()
        r = requests.get(f"https://{host}/robots.txt", headers={"User-Agent": UA}, timeout=20)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [] if r.status_code < 500 else ["User-agent: *", "Disallow: /"])
        _robots[host] = rp
    if host not in TERMS_PERMIT and not _robots[host].can_fetch(UA, url):
        raise PermissionError(f"robots.txt 가 막는다: {url}")
    for n in range(tries):
        wait = GAP.get(host, 1.0) - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        r = requests.get(url, params=params, timeout=60, headers={"User-Agent": UA, **(headers or {})})
        if r.status_code in (429, 502, 503) or (r.status_code == 403 and "rate limit" in r.text.lower()):
            time.sleep(min(60, 4 * 2 ** n))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"{url} 가 계속 막힌다 (속도 제한)")


def brave(q, n=10):
    """Brave Search API → 결과 주소 목록 (순위 차례). 부를 때마다 BRAVE_LOG 에 한 줄 적고, 이번 달 BRAVE_MONTHLY 번을 넘으면 멈춘다."""
    month = time.strftime("%Y-%m")
    used = sum(line.startswith(month) for line in BRAVE_LOG.read_text().splitlines()) if BRAVE_LOG.exists() else 0
    if used >= BRAVE_MONTHLY:
        raise RuntimeError(f"Brave 이번 달 {BRAVE_MONTHLY}번을 다 썼다 ({BRAVE_LOG})")
    BRAVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with BRAVE_LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{q}\n")
    got = get("https://api.search.brave.com/res/v1/web/search", {"q": q, "count": n},
              {"Accept": "application/json", "X-Subscription-Token": config.get("BRAVE_API_KEY", "")}).json()
    return [r["url"] for r in got.get("web", {}).get("results", [])][:n]


def web(q):
    """일반 웹 검색. BRAVE_API_KEY 가 있으면 Brave, 없으면 DuckDuckGo."""
    return brave(q) if config.get("BRAVE_API_KEY", "") else ddg(q)


def ddg(q, n=10):
    """DuckDuckGo 검색 → 결과 주소 목록 (순위 차례)."""
    page = get("https://html.duckduckgo.com/html/", {"q": q}).text
    if "anomaly-modal" in page:   # 봇 확인 화면. 우회하지 않고 멈춘다
        raise RuntimeError("DuckDuckGo 가 자동 접근을 막았다 (봇 확인 화면)")
    return [unquote(u) for u in re.findall(r'class="result__a" href="[^"]*?uddg=([^&"]+)', page)][:n]


def arxiv_details(ids):
    """arXiv 번호 목록 → {번호: 후보}. 제목·초록·저자 주석(학회)을 arXiv API 한 번에 받는다."""
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    feed = ET.fromstring(get("https://export.arxiv.org/api/query", {"id_list": ",".join(ids), "max_results": len(ids)}).text)
    out = {}
    for e in feed.findall("a:entry", ns):
        aid = re.sub(r"v\d+$", "", e.findtext("a:id", "", ns).rsplit("/", 1)[-1])
        note = " ".join(filter(None, [e.findtext("x:journal_ref", "", ns), e.findtext("x:comment", "", ns)]))
        out[aid] = {"key": f"arxiv:{aid}", "kind": "paper", "title": " ".join(e.findtext("a:title", "", ns).split()),
                    "year": e.findtext("a:published", "", ns)[:4], "venue": note[:80] or "arXiv",
                    "url": f"https://arxiv.org/abs/{aid}", "text": " ".join(e.findtext("a:summary", "", ns).split())}
    return out


def github_details(full):
    """owner/name → 후보 (별 수, 설명, 주제)."""
    token = config.get("GITHUB_TOKEN", "")
    i = get(f"https://api.github.com/repos/{full}", headers={"Authorization": f"Bearer {token}"} if token else None).json()
    return {"key": f'gh:{i["full_name"].lower()}', "kind": "repo", "title": i["full_name"],
            "year": (i.get("pushed_at") or "")[:4], "venue": f'GitHub ★{i["stargazers_count"]}', "url": i["html_url"],
            "text": " ".join([i.get("description") or ""] + i.get("topics", [])), "stars": i["stargazers_count"]}


def key_of(url):
    """검색 결과 주소 → 'arxiv:번호' 나 'gh:owner/name'. 둘 다 아니면 None."""
    if m := re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", url):
        return f"arxiv:{m.group(1)}"
    if m := re.match(r"https?://github\.com/([\w.-]+)/([\w.-]+)", url):
        return f"gh:{m.group(1).lower()}/{m.group(2).lower().removesuffix('.git')}"
    return None


def ask_queries(case):
    """공고 → {paper_queries, repo_queries, paper_names, repo_names}. LLM 한 번."""
    got = llm.ask_json(posting_text(case), QUERY_SYSTEM, QUERY_SCHEMA, model=MODEL, max_tokens=2000)
    return {k: [got[k][str(i)] for i in range(1, n + 1)] for k, n in COUNTS.items()}


def find_candidates(case, top=20):
    """공고 → {paper_queries, repo_queries, paper_names, repo_names, errors, candidates}. 점수 = 검색마다 1/(순위+1) 의 합. 위 40개만 자세히 받아 별 100 미만 저장소를 빼고 top 개."""
    path = config.OUTPUTS / "project" / f'{case["case"]}.search.json'
    if path.exists():
        return json.loads(path.read_text("utf-8"))
    ask = ask_queries(case)
    searches = ([f"{q} arxiv" for q in ask["paper_queries"] + ask["paper_names"]]
                + [f"{q} github" for q in ask["repo_queries"] + ask["repo_names"]])
    score, errors = {}, []
    for q in searches:
        try:
            found = [k for k in map(key_of, web(q)) if k]
        except (requests.RequestException, RuntimeError, PermissionError) as e:
            errors.append(str(e)[:120])
            continue
        keys = list(dict.fromkeys(found))
        for rank, key in enumerate(keys):
            score[key] = score.get(key, 0) + 1 / (rank + 1)
    shortlist = sorted(score, key=lambda k: -score[k])[:2 * top]
    papers = arxiv_details([k[6:] for k in shortlist if k.startswith("arxiv:")]) if shortlist else {}
    item = {}
    for k in shortlist:
        try:
            it = papers.get(k[6:]) if k.startswith("arxiv:") else github_details(k[3:])
        except requests.RequestException as e:
            errors.append(f"{k}: {str(e)[:100]}")
            continue
        if it and it.get("stars", MIN_STARS) >= MIN_STARS:
            item[k] = it
    ranked = [k for k in shortlist if k in item][:top]
    if not ranked:
        raise RuntimeError(f"후보가 하나도 없다. 검색이 모두 막혔을 수 있다: {errors[:3]}")
    out = {**ask, "errors": errors, "candidates": [{**item[k], "search_score": round(score[k], 3)} for k in ranked]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    return out
