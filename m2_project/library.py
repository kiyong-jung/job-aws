"""② 논문 서고: 탑티어 AI·클라우드/시스템 학회 2020~2026 논문 → data/papers/<ai|cloud>/<학회>_<연도>.jsonl.

웹 검색 대신 공식 일괄 내려받기·공식 API·학회 공식 논문 페이지에서 제목·초록·주소를 모아 로컬에 둔다.
실행: python -m m2_project.library papers [출처…] / fill [학회…] / code / pdf / prune / reorganize / stats
출처: acl(ACL Anthology bib), icml(PMLR bib), nips(papers.nips.cc), cvf(CVPR·ICCV), eccv(ecva.net), dblp(제목만),
      usenix(OSDI·NSDI·ATC·FAST 공식 프로그램 쪽), mlsys(proceedings.mlsys.org).
순서: papers → fill → code → pdf → prune → reorganize (자세한 것은 data/papers/README.md).
이어하기: 조각(shard)이 이미 있으면 목록은 다시 받지 않고, 초록이 None 인 글만 채운다 (초록이 없는 글은 "").
막히면(403·429·확인 요구) 그 출처만 멈추고 알린다. 우회하지 않는다.
"""
import gzip
import html
import html.entities
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError

from m2_project.guard import refuse_if_running

PAPERS = Path(__file__).resolve().parents[1] / "data" / "papers"
RAW = PAPERS / "_raw"
UA = "Mozilla/5.0 (research collector)"
GAP = {"papers.nips.cc": 1.1, "openaccess.thecvf.com": 1.1, "www.ecva.net": 1.1, "proceedings.mlr.press": 1.1,
       "export.arxiv.org": 3.5, "dblp.org": 4.0,
       "www.usenix.org": 10.0, "ojs.aaai.org": 1.1}   # 호스트마다 요청 사이 간격(초). dblp·usenix 는 robots.txt 의 Crawl-delay
YEARS = range(2020, 2027)
AI_VENUES = ("ACL", "EMNLP", "NAACL", "ICML", "NeurIPS", "ICLR", "CVPR", "ICCV", "ECCV", "AAAI", "IJCAI", "KDD", "SIGIR", "WWW", "MM", "CHI")
CLOUD_VENUES = ("OSDI", "NSDI", "ATC", "FAST", "MLSys", "SOSP", "EuroSys", "ASPLOS", "SIGCOMM")
FIELD_OF = {**{v: "ai" for v in AI_VENUES}, **{v: "cloud" for v in CLOUD_VENUES}}
FIELD_DIRS = ("ai", "cloud")
FIELDS = ("venue", "year", "title", "abstract", "url", "doi", "arxiv", "abstract_source")
_last = {}


class Blocked(Exception):
    """사이트가 막았다. 그 출처는 멈춘다."""


def get(url, binary=False):
    """주소 → 본문. 호스트별 간격을 지키고 5xx·시간 초과는 세 번 다시 해 본다. 403·429 는 Blocked."""
    host = url.split("/")[2]
    for attempt in range(3):
        wait = _last.get(host, 0) + GAP.get(host, 1.1) - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                body = r.read()
                if "challenge" in r.geturl():
                    raise Blocked(f"{url} 확인 요구")
                return body if binary else body.decode("utf-8", "replace")
        except HTTPError as e:
            if e.code in (403, 429):
                raise Blocked(f"{url} HTTP {e.code}")
            if e.code == 404:
                return None
            if attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(5 * (attempt + 1))


def paper(venue, year, title, url, abstract=None, source=None, doi=None, arxiv=None):
    return dict(venue=venue, year=year, title=title, abstract=abstract, url=url, doi=doi, arxiv=arxiv,
                abstract_source=source, has_code="F", code_url="", code_source="", pdf_url="")


def clean(s):
    """bib·HTML 의 글자 처리: 중괄호·태그를 걷고 공백을 한 칸으로."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s).replace("{", "").replace("}", "").replace("\\&", "&").replace("\\%", "%")
    return re.sub(r"\s+", " ", s).strip()


def norm(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


# 조각 읽고 쓰기

def field_of(venue):
    """학회 → 'ai' | 'cloud'. 표에 없는 학회는 KeyError (조용히 아무 데나 두지 않는다). Findings 는 본 학회를 따른다."""
    return FIELD_OF[venue.removesuffix("-Findings")]


def shard(venue, year):
    """조각 경로. 새 위치(<분야>/)가 기본이고, 아직 옮기기 전의 옛 위치(data/papers/ 바로 아래)에 있으면 그것을 돌려준다."""
    name = f"{venue}_{year}.jsonl"
    new, old = PAPERS / field_of(venue) / name, PAPERS / name
    return old if old.exists() and not new.exists() else new


def all_shards():
    """모든 조각(옛 위치 + 분야 폴더). _raw 는 뺀다."""
    return sorted([*PAPERS.glob("*_*.jsonl"), *(p for d in FIELD_DIRS for p in (PAPERS / d).glob("*_*.jsonl"))], key=lambda p: p.name)


def read_shard(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def write_shard(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def save(venue, year, rows):
    """같은 조각이 이미 있으면 그대로 둔다 (이어하기)."""
    if rows and not shard(venue, year).exists():
        write_shard(shard(venue, year), rows)
        print(f"{venue} {year}: {len(rows)}편 저장", flush=True)


# bib 읽기 (ACL Anthology, PMLR)

def parse_bib(lines):
    """bib 줄들 → 항목(dict) 제너레이터. 값은 "…" 또는 {…} (안에 중괄호가 겹쳐도 된다)."""
    entry = []
    for line in list(lines) + ["@end{"]:
        if line.startswith("@") and entry:
            text = "".join(entry)
            fields = {}
            for m in re.finditer(r"^\s*(\w+)\s*=\s*", text, re.M):
                i, depth, quote = m.end(), 0, text[m.end()] == '"'
                j = i + 1
                while j < len(text):
                    c = text[j]
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        if depth == 0 and not quote:
                            break
                        depth -= 1
                    elif c == '"' and quote and depth == 0:
                        break
                    j += 1
                fields.setdefault(m.group(1).lower(), clean(text[i + 1:j]))
            yield fields
            entry = []
        entry.append(line)


ACL_ID = re.compile(r"^(\d{4})\.(?:(acl|emnlp|naacl)-(?:main|long|short)|findings-(acl|emnlp|naacl))\.\d+$")


def acl_rows(lines):
    """ACL Anthology bib(초록 포함) → (학회, 연도, 논문). 본회의(main·long·short)와 Findings 만. 워크숍·튜토리얼은 뺀다."""
    for f in parse_bib(lines):
        m = ACL_ID.match(f.get("url", "").rstrip("/").rsplit("/", 1)[-1])
        if m and 2020 <= int(m.group(1)) <= 2026 and f.get("title"):
            venue = m.group(2).upper() if m.group(2) else m.group(3).upper() + "-Findings"
            yield venue, int(m.group(1)), paper(venue, int(m.group(1)), f["title"], f["url"], f.get("abstract") or "",
                                               "aclanthology.org (CC BY)", f.get("doi"))


def pmlr_rows(text, year):
    """PMLR bibliography.bib → ICML 논문. 첫 항목은 논문집 자체라 제목이 없는 것은 거른다."""
    for f in parse_bib(text.splitlines(True)):
        if f.get("url") and f.get("title") and f.get("abstract") is not None:
            yield paper("ICML", year, f["title"], f["url"], f["abstract"], "proceedings.mlr.press")


def collect_acl():
    path = RAW / "anthology+abstracts.bib.gz"
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get("https://aclanthology.org/anthology+abstracts.bib.gz", binary=True))
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for venue, year, p in acl_rows(fh):
            out.setdefault((venue, year), []).append(p)
    for (venue, year), rows in sorted(out.items()):
        save(venue, year, rows)


ICML_VOL = {2020: 119, 2021: 139, 2022: 162, 2023: 202, 2024: 235, 2025: 267}   # 2026 권은 아직 PMLR 에 없다


def collect_icml():
    for year, vol in ICML_VOL.items():
        if not shard("ICML", year).exists():
            save("ICML", year, list(pmlr_rows(get(f"https://proceedings.mlr.press/v{vol}/assets/bib/bibliography.bib"), year)))


# 논문 페이지에서 초록 채우기 (NeurIPS, CVF, ECCV)

NIPS_ABS = re.compile(r'<p class="paper-abstract">(.*?)</section>', re.S)
CVF_ABS = re.compile(r'<div id="abstract"[^>]*>(.*?)</div>', re.S)


def abstract_of(page, pattern):
    m = pattern.search(page or "")
    return clean(m.group(1)) if m else ""


def nips_list(page, year, venue="NeurIPS", host="https://papers.nips.cc"):
    """papers.nips.cc 와 proceedings.mlsys.org 는 같은 쪽 모양이다. 주소는 그 사이트의 것으로 만든다."""
    rows = re.findall(r'<a title="paper title" href="(/paper_files/paper/\d+/hash/[^"]+)">([^<]*)', page)
    return [paper(venue, year, clean(t), host + u) for u, t in rows]


def cvf_list(page, venue, year):
    rows = re.findall(r'class="ptitle"><br><a href="/?(content[^"]+)">([^<]*)</a>', page)   # 2020 년 쪽은 앞의 / 가 없다
    return [paper(venue, year, clean(t), "https://openaccess.thecvf.com/" + u) for u, t in rows]


def eccv_list(page):
    """ecva.net/papers.php: 'ECCV 2024 Papers' 단추 뒤 구역마다 연도가 붙는다. → {연도: 논문들}"""
    out = {}
    parts = re.split(r"<!-- ECCV (\d{4}) -->", page)
    for year, body in zip(parts[1::2], parts[2::2]):
        rows = re.findall(r'<dt class="ptitle">\s*(?:<br>)?\s*<a href=(\S+?)>\s*(.*?)</a>', body, re.S)
        out.setdefault(int(year), [])
        out[int(year)] += [paper("ECCV", int(year), clean(t), "https://www.ecva.net/" + u) for u, t in rows]
    return out


def fill_abstracts(venue, year, pattern, label):
    """조각에서 초록이 None 인 글의 페이지를 열어 채운다. 100편마다 저장해 끊겨도 이어진다."""
    rows = read_shard(shard(venue, year))
    todo = [r for r in rows if r["abstract"] is None]
    for n, r in enumerate(todo, 1):
        r["abstract"] = abstract_of(get(r["url"]), pattern)
        r["abstract_source"] = label
        if n % 100 == 0 or n == len(todo):
            write_shard(shard(venue, year), rows)
            print(f"{venue} {year}: 초록 {n}/{len(todo)}", flush=True)


def collect_nips():
    for year in YEARS:
        if not shard("NeurIPS", year).exists():
            page = get(f"https://papers.nips.cc/paper_files/paper/{year}")
            save("NeurIPS", year, nips_list(page, year) if page else [])
        if shard("NeurIPS", year).exists():
            fill_abstracts("NeurIPS", year, NIPS_ABS, "papers.nips.cc")


CVF_EVENTS = [("CVPR", y) for y in YEARS] + [("ICCV", y) for y in (2021, 2023, 2025)]
CVPR2020_DAYS = ("2020-06-16", "2020-06-17", "2020-06-18")


def collect_cvf():
    for venue, year in CVF_EVENTS:
        if not shard(venue, year).exists():
            urls = [f"https://openaccess.thecvf.com/{venue}{year}?day={d}" for d in CVPR2020_DAYS] if (venue, year) == ("CVPR", 2020) \
                else [f"https://openaccess.thecvf.com/{venue}{year}?day=all"]
            rows = [p for u in urls for p in cvf_list(get(u) or "", venue, year)]
            save(venue, year, rows)
        if shard(venue, year).exists():
            fill_abstracts(venue, year, CVF_ABS, "openaccess.thecvf.com")


def collect_eccv():
    done = all(shard("ECCV", y).exists() for y in (2020, 2022, 2024))
    if not done:
        for year, rows in eccv_list(get("https://www.ecva.net/papers.php")).items():
            if year >= 2020:
                save("ECCV", year, rows)
    for year in YEARS:
        if shard("ECCV", year).exists():
            fill_abstracts("ECCV", year, CVF_ABS, "ecva.net")


# USENIX (OSDI·NSDI·ATC·FAST): 공식 프로그램 쪽 하나에 제목·초록이 다 들어 있다. robots.txt Crawl-delay 10초.

USENIX_CONFS = ("OSDI", "NSDI", "ATC", "FAST")
USENIX_SLUG = {"OSDI": "osdi", "NSDI": "nsdi", "ATC": "atc", "FAST": "fast"}
USENIX_PAPER = re.compile(r'<article id="node-\d+" class="node node-paper view-mode-schedule">(.*?)(?=<article id="node-\d+" class="node node-(?:paper|session)|\Z)', re.S)
USENIX_TITLE = re.compile(r'<h2>\s*<a href="(/conference/[^"/]+/presentation/[^"]+)">(.*?)</a>', re.S)
USENIX_ABS = re.compile(r'field-name-field-paper-description-long[^>]*>(.*?)</div>', re.S)


def usenix_pdf(path):
    """/conference/osdi20/presentation/boos → https://www.usenix.org/system/files/osdi20-boos.pdf (files.usenix.org 로 넘어간다)."""
    m = re.match(r"/conference/([^/]+)/presentation/([^/?#]+)", path)
    return f"https://www.usenix.org/system/files/{m.group(1)}-{m.group(2)}.pdf"


def usenix_list(page, venue, year):
    """technical-sessions 쪽 → 논문들. 같은 발표가 두 번 나오면 하나만."""
    out = {}
    for block in USENIX_PAPER.findall(page or ""):
        t = USENIX_TITLE.search(block)
        if t and t.group(1) not in out:
            a = USENIX_ABS.search(block)
            p = paper(venue, year, clean(t.group(2)), "https://www.usenix.org" + t.group(1), clean(a.group(1)) if a else "", "usenix.org")
            p["pdf_url"] = usenix_pdf(t.group(1))
            out[t.group(1)] = p
    return list(out.values())


def collect_usenix():
    for venue in USENIX_CONFS:
        for year in YEARS:
            if not shard(venue, year).exists():
                page = get(f"https://www.usenix.org/conference/{USENIX_SLUG[venue]}{year % 100}/technical-sessions")
                save(venue, year, usenix_list(page, venue, year))


def collect_mlsys():
    for year in YEARS:
        if not shard("MLSys", year).exists():
            page = get(f"https://proceedings.mlsys.org/paper_files/paper/{year}")
            rows = nips_list(page, year, "MLSys", "https://proceedings.mlsys.org") if page else []
            save("MLSys", year, rows)
        if shard("MLSys", year).exists():
            fill_abstracts("MLSys", year, NIPS_ABS, "proceedings.mlsys.org")


# dblp 일괄 파일: 제목만 (초록은 fill 로 arXiv 에서)

DBLP_BOOK = {"AAAI": "AAAI", "IJCAI": "IJCAI", "KDD": "KDD", "KDD (1)": "KDD", "KDD (2)": "KDD", "SIGIR": "SIGIR", "WWW": "WWW", "ACM Multimedia": "MM",
             "CHI": "CHI", "ICLR": "ICLR",
             "SOSP": "SOSP", "EuroSys": "EuroSys", "SIGCOMM": "SIGCOMM",
             "ASPLOS": "ASPLOS", "ASPLOS (1)": "ASPLOS", "ASPLOS (2)": "ASPLOS", "ASPLOS (3)": "ASPLOS", "ASPLOS (4)": "ASPLOS"}   # dblp booktitle → 학회. 부록(Companion)·워크숍 논문집은 booktitle 이 달라 빠진다 (SOSP·EuroSys·ASPLOS·SIGCOMM 은 클라우드 분야)
DBLP_CHECK = ("nips", "icml", "cvpr", "iccv", "eccv", "acl", "emnlp", "naacl")   # 다른 출처와 편수를 맞춰 볼 학회
ENT = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)(\w+);")


def dblp_rows(lines):
    """dblp.xml 줄들 → ('논문', 학회, 연도, 논문) 또는 ('확인', 학회키, 연도, None). inproceedings 항목만 읽는다."""
    tail = ""
    for line in lines:
        tail += line
        if "<inproceedings " not in tail:
            tail = ""
        while "</inproceedings>" in line and "</inproceedings>" in tail:
            end = tail.index("</inproceedings>") + len("</inproceedings>")
            start = tail.rfind("<inproceedings ", 0, end)
            block, tail = tail[start:end], tail[end:]
            if start >= 0:
                text = ENT.sub(lambda m: html.entities.html5.get(m.group(1) + ";", m.group(0)), block)
                try:
                    el = ET.fromstring(text)
                except ET.ParseError:
                    continue
                year = int(el.findtext("year") or 0)
                if not 2020 <= year <= 2026:
                    continue
                key = el.get("key").split("/")
                if len(key) > 1 and key[1] in DBLP_CHECK:
                    yield "확인", key[1], year, None
                book = el.findtext("booktitle")
                title = clean(el.findtext("title") or "").rstrip(".")
                if book in DBLP_BOOK and title:
                    ees = [e.text for e in el.findall("ee") if e.text]
                    doi = next((e.split("doi.org/")[1] for e in ees if "doi.org/" in e), None)
                    url = next((e for e in ees if "doi.org/" not in e), None) or (ees[0] if ees else "https://dblp.org/rec/" + el.get("key"))
                    yield "논문", DBLP_BOOK[book], year, paper(DBLP_BOOK[book], year, title, url, doi=doi)


def collect_dblp():
    path = RAW / "dblp.xml.gz"
    if not path.exists():
        raise FileNotFoundError("data/papers/_raw/dblp.xml.gz 가 없다. curl -A UA -C - -o … https://dblp.org/xml/dblp.xml.gz")
    out, check = {}, Counter()
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for kind, venue, year, p in dblp_rows(fh):
            if kind == "확인":
                check[f"{venue}_{year}"] += 1
            else:
                out.setdefault((venue, year), []).append(p)
    for (venue, year), rows in sorted(out.items()):
        save(venue, year, rows)
    (RAW / "dblp_counts.json").write_text(json.dumps(check, indent=1, sort_keys=True))


# arXiv 로 초록 채우기: 제목이 똑같은 글 하나만 받아들인다

def arxiv_find(titles):
    """제목 여럿(5개 이하) → {정규화한 제목: (초록, arXiv 번호)}. 제목이 똑같은 글만. API 이용약관이 허락한다. 3.5초 간격."""
    q = urllib.parse.quote(" OR ".join(f'ti:"{t}"' for t in titles))
    feed = get(f"http://export.arxiv.org/api/query?search_query={q}&max_results={3 * len(titles)}")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    wanted, found = {norm(t) for t in titles}, {}
    for e in ET.fromstring(feed).findall("a:entry", ns):
        key = norm(clean(e.findtext("a:title", "", ns)))
        if key in wanted and key not in found:
            found[key] = (clean(e.findtext("a:summary", "", ns)), e.findtext("a:id", "", ns).rsplit("/abs/", 1)[-1])
    return found


def fill_arxiv(venues, batch=5):
    for venue in venues:
        for year in YEARS:
            rows = read_shard(shard(venue, year))
            todo = [r for r in rows if r["abstract"] is None]
            for i in range(0, len(todo), batch):
                chunk = todo[i:i + batch]
                try:
                    found = arxiv_find([r["title"] for r in chunk])
                except (HTTPError, URLError, TimeoutError, ET.ParseError) as e:   # 일시 오류(503 등): 이 묶음은 None 으로 두고 다음 실행에서 다시
                    print(f"{venue} {year}: arXiv 묶음 건너뜀 ({type(e).__name__} {e})", flush=True)
                    write_shard(shard(venue, year), rows)
                    time.sleep(30)
                    continue
                for r in chunk:
                    hit = found.get(norm(r["title"]))
                    r["abstract"], r["arxiv"] = (hit[0], hit[1]) if hit else ("", None)
                    r["abstract_source"] = "arxiv.org (exact title)" if hit else "none"
                if (i // batch) % 20 == 19 or i + batch >= len(todo):
                    write_shard(shard(venue, year), rows)
                    print(f"{venue} {year}: arXiv {min(i + batch, len(todo))}/{len(todo)}", flush=True)


# 코드 저장소 연결: has_code "T"/"F". F 는 찾지 못했다는 뜻이지 없다는 증명이 아니다. 몇 번 돌려도 같은 결과(F → T 로만 바뀐다)

GH_URL = re.compile(r"(?:https?://)?(?:www\.)?github\.com/([\w.-]+/[\w.-]+)", re.I)
PWC_FILE = RAW / "pwc_links.parquet"   # Papers with Code 보관본(원 운영팀 pwc-archive, Hugging Face, CC BY-SA 4.0)
PWC_URL = "https://huggingface.co/datasets/pwc-archive/links-between-paper-and-code/resolve/main/data/train-00000-of-00001.parquet"
REPOS = PAPERS.parent / "github_repos"   # 다른 담당이 모으는 저장소 목록. 읽기만 한다
ARXIV_ID = re.compile(r"(?:arxiv[:.\s/]*|abs/)(\d{4}\.\d{4,5})", re.I)


def github_in(text):
    """글 속 github.com/소유자/이름 → 'https://github.com/소유자/이름' 또는 None. 문장 끝 점·.git 은 뗀다."""
    m = GH_URL.search(text or "")
    return "https://github.com/" + re.sub(r"(\.git)?[.,;)]*$", "", m.group(1)) if m else None


def pwc_index():
    """PWC 보관본 → ({arXiv 번호: 주소}, {제목: 주소}). 공식 저장소를 먼저 둔다. 파일이 없으면 받는다."""
    import pandas as pd
    if not PWC_FILE.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        PWC_FILE.write_bytes(get(PWC_URL, binary=True))
    df = pd.read_parquet(PWC_FILE).sort_values("is_official", ascending=True)   # 뒤에 오는 값이 앞을 덮는다
    df = df[df.repo_url.str.contains("github.com", na=False)]
    by_id = dict(zip(df.paper_arxiv_id.fillna(""), df.repo_url))
    by_title = {norm(t): u for t, u in zip(df.paper_title.fillna(""), df.repo_url)}
    by_id.pop("", None)
    return by_id, by_title


def repo_index():
    """저장소 목록의 설명 → ({arXiv 번호: 주소}, {설명 전체가 제목과 같은 것: 주소}). 설명에 번호나 제목이 적힌 저장소만 이어진다."""
    by_id, by_desc = {}, {}
    for path in REPOS.rglob("*__*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            d = r.get("description") or ""
            for i in ARXIV_ID.findall(d):
                by_id.setdefault(i, r["url"])
            by_desc.setdefault(norm(d), r["url"])
    return by_id, by_desc


def code_links():
    """모든 조각에 has_code·code_url·code_source 를 붙인다. 순서: 초록 속 주소 → PWC 보관본 → 저장소 목록 설명."""
    try:
        pwc_id, pwc_title = pwc_index()
    except Exception as e:
        print(f"PWC 보관본 건너뜀: {e}")
        pwc_id, pwc_title = {}, {}
    repo_id, repo_desc = repo_index()
    found = Counter()
    for path in all_shards():
        rows = read_shard(path)
        for r in rows:
            r.setdefault("has_code", "F"); r.setdefault("code_url", ""); r.setdefault("code_source", "")
            if r["has_code"] == "T":
                continue
            t, aid = norm(r["title"]), r.get("arxiv") or ""
            hit = (github_in(r["abstract"]) and (github_in(r["abstract"]), "abstract")) \
                or ((pwc_id.get(aid) or pwc_title.get(t)) and (pwc_id.get(aid) or pwc_title.get(t), "paperswithcode-archive")) \
                or ((repo_id.get(aid) or repo_desc.get(t)) and (repo_id.get(aid) or repo_desc.get(t), "github_repos description"))
            if hit:
                r["has_code"], r["code_url"], r["code_source"] = "T", hit[0], hit[1]
            found[r["code_source"]] += r["has_code"] == "T"
        write_shard(path, rows)
    print("T 개수(출처별):", dict(found))
    readme = PAPERS / "README.md"
    if readme.exists():
        block = "\n".join(f"- {k}: {n}편" for k, n in found.most_common() if k) + f"\n- (집계일 {time.strftime('%Y-%m-%d')})"
        readme.write_text(re.sub(r"(<!-- code-stats -->\n).*?(\n<!-- /code-stats -->)", lambda m: m.group(1) + block + m.group(2),
                                 readme.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")


# 전문(PDF) 규칙: 전문을 내려받을 수 없는 글은 지운다. pdf_url = 학회 공식 공개 PDF → 없으면 arXiv PDF → 없으면 삭제.
# 공식 PDF 주소는 글 주소에서 규칙으로 만든다 (AAAI 만 논문 쪽을 열어 알아낸다: pdf 명령).

def pdf_url_of(r):
    """행 → 전문 PDF 주소 또는 ""(없음). 네트워크를 쓰지 않는다. 이미 pdf_url 이 있으면 그대로."""
    if r.get("pdf_url"):
        return r["pdf_url"]
    venue, url = r["venue"].removesuffix("-Findings"), r.get("url") or ""
    official = ""
    if venue in ("ACL", "EMNLP", "NAACL") and "aclanthology.org" in url:
        official = url.rstrip("/") + ".pdf"
    elif venue == "ICML" and url.endswith(".html"):
        official = url[:-5] + "/" + url.rsplit("/", 1)[-1][:-5] + ".pdf"
    elif venue in ("NeurIPS", "MLSys") and "/hash/" in url and "-Abstract" in url:
        official = url.replace("/hash/", "/file/").replace("-Abstract", "-Paper").removesuffix(".html") + ".pdf"
    elif venue in ("CVPR", "ICCV") and "/html/" in url:
        official = url.replace("/html/", "/papers/").removesuffix(".html") + ".pdf"
    elif venue == "ECCV" and "/html/" in url:
        official = url.replace("/html/", "/papers/").removesuffix(".php") + ".pdf"
    elif venue == "IJCAI" and (m := re.search(r"ijcai\.(\d{4})/(\d+)$", url)):
        official = f"https://www.ijcai.org/proceedings/{m.group(1)}/{int(m.group(2)):04d}.pdf"
    elif venue in USENIX_CONFS and "/presentation/" in url:
        official = usenix_pdf(urllib.parse.urlparse(url).path)
    return official or (f"https://arxiv.org/pdf/{r['arxiv']}" if r.get("arxiv") else "")


AAAI_PDF = re.compile(r'<meta name="citation_pdf_url" content="([^"]+)"')


def resolve_aaai_pdfs():
    """arXiv 에 없는 AAAI 글: doi 주소가 가리키는 ojs.aaai.org 논문 쪽에서 공식 PDF 주소를 읽는다. 100편마다 저장, 이어하기."""
    for year in YEARS:
        path = shard("AAAI", year)
        rows = read_shard(path)
        todo = [r for r in rows if not r.get("pdf_url") and not r.get("arxiv") and r.get("url")]
        for n, r in enumerate(todo, 1):
            m = AAAI_PDF.search(get(r["url"]) or "")
            r["pdf_url"] = m.group(1) if m else ""
            if n % 100 == 0 or n == len(todo):
                write_shard(path, rows)
                print(f"AAAI {year}: pdf {n}/{len(todo)}", flush=True)


def prune():
    """모든 조각: pdf_url 을 채우고, 전문 주소가 없는 글은 지운다. 몇 번 돌려도 같은 결과. _raw 는 건드리지 않는다. → {조각: (전, 후)}"""
    result = {}
    for path in all_shards():
        rows = read_shard(path)
        kept = []
        for r in rows:
            r["pdf_url"] = pdf_url_of(r)
            if r["pdf_url"]:
                kept.append(r)
        write_shard(path, kept)
        result[path.stem] = (len(rows), len(kept))
    before, after = (sum(v[i] for v in result.values()) for i in (0, 1))
    print(f"prune: {before} → {after}편 (삭제 {before - after})")
    (PAPERS / "prune_report.json").write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    return result


def reorganize():
    """옛 위치(data/papers/<학회>_<연도>.jsonl)의 조각을 <분야>/ 로 옮긴다. 이미 옮겼으면 아무것도 안 한다. → 옮긴 개수"""
    moved = 0
    for p in sorted(PAPERS.glob("*_*.jsonl")):
        dest = PAPERS / field_of(p.stem.rsplit("_", 1)[0]) / p.name
        dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"{dest} 가 이미 있다. 손으로 확인")
        p.replace(dest)
        moved += 1
    print(f"reorganize: {moved}개 조각 이동")
    return moved


# 실행

SOURCES = {"acl": collect_acl, "icml": collect_icml, "nips": collect_nips, "cvf": collect_cvf, "eccv": collect_eccv,
           "dblp": collect_dblp, "usenix": collect_usenix, "mlsys": collect_mlsys}


def stats():
    """조각 → 학회·연도별 (편수, 초록 있음, 코드 T) 표. README.md 의 <!-- stats --> 사이를 이 표로 바꾼다."""
    lines = ["| 조각 | 편수 | 초록 있음 | has_code=T |", "|---|---|---|---|"]
    tot = [0, 0, 0]
    for p in all_shards():
        ps = read_shard(p)
        row = [len(ps), sum(bool(r["abstract"]) for r in ps), sum(r.get("has_code") == "T" for r in ps)]
        tot = [a + b for a, b in zip(tot, row)]
        lines.append(f"| {p.stem} | " + " | ".join(map(str, row)) + " |")
    lines.append("| **합계** | " + " | ".join(f"**{n}**" for n in tot) + " |")
    table = "\n".join(lines)
    print(table)
    readme = PAPERS / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        text = re.sub(r"(<!-- stats -->\n).*?(\n<!-- /stats -->)", lambda m: m.group(1) + table + m.group(2), text, flags=re.S)
        readme.write_text(text, encoding="utf-8")


def main(argv):
    cmd, rest = (argv + ["stats"])[0], argv[1:]
    if cmd == "papers":
        for name in rest or SOURCES:
            try:
                SOURCES[name]()
            except Exception as e:   # 한 출처가 실패해도 다른 출처는 계속
                print(f"[{name}] 멈춤: {type(e).__name__}: {e}", flush=True)
    elif cmd == "code":
        code_links()
    elif cmd == "pdf":
        resolve_aaai_pdfs()
    elif cmd == "prune":
        refuse_if_running("m2_project.library", "prune")
        prune()
    elif cmd == "reorganize":
        refuse_if_running("m2_project.library", "reorganize")
        reorganize()
    elif cmd == "fill":
        refuse_if_running("m2_project.library fill", "fill (arXiv 채우기 동시 실행 방지)")
        fill_arxiv(rest or ["ICLR", "AAAI", "IJCAI", "KDD", "SIGIR", "WWW", "MM", "CHI", "SOSP", "EuroSys", "ASPLOS", "SIGCOMM"])
    else:
        stats()


if __name__ == "__main__":
    main(sys.argv[1:])
