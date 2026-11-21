"""저장소 README 받기와 정리. 판정기가 저장소를 볼 때 이름·설명 한 줄 대신 README 를 같이 본다 (연구 RQ4b·RQ5).

받기: raw.githubusercontent.com 의 기본 가지 README (README.md 다음 흔한 이름 차례로). 인증 없음, 요청 사이 1초,
UA "Mozilla/5.0 (research collector)". robots.txt 는 404 라 막는 규칙이 없다 (2026-11-17 확인). 429 가 오면 우회하지 않고 README 없이 판정한다.
저장: outputs/research/readmes/ (연구 때 받은 636개 저장소를 그대로 다시 쓴다) + index.jsonl. 받은 글은 자료로만 읽는다.
정리: 코드 블록·HTML·그림·배지·링크 주소·표 선·제목 표시를 지우고 공백을 모은 뒤 앞 4,000자.
"""
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

from shared import config

DIR = config.OUTPUTS / "research" / "readmes"
INDEX = DIR / "index.jsonl"
NAMES = ("README.md", "readme.md", "Readme.md", "README.rst", "README", "README.markdown", "README.txt", "readme.rst", "README.MD")
UA = "Mozilla/5.0 (research collector)"
GAP, MAX_BYTES, CHARS = 1.0, 200_000, 4000

_last = [0.0]
_index = {}


def _get(url):
    wait = _last[0] + GAP - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
            return r.status, r.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return f"error:{type(e).__name__}", b""


def _fetch(key):
    full = key.removeprefix("gh:")
    for name in NAMES:
        status, body = _get(f"https://raw.githubusercontent.com/{full}/HEAD/{name}")
        if status == 200:
            fn = full.replace("/", "__") + ".txt"
            (DIR / fn).write_bytes(body)
            return {"key": key, "status": "ok", "file": fn, "name": name, "bytes": len(body)}
        if status != 404:
            return {"key": key, "status": f"fail:{status}"}
    return {"key": key, "status": "none"}


def _load_index():
    if not _index and INDEX.exists():
        for line in INDEX.read_text("utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                _index[r["key"]] = r
    return _index


def fetch_missing(keys):
    """저장소 열쇠(gh:owner/name) 중 아직 안 받은 것만 받는다. 받은 개수를 돌려준다."""
    idx = _load_index()
    todo = [k for k in dict.fromkeys(keys) if k.startswith("gh:") and not (k in idx and not idx[k]["status"].startswith("fail"))]
    DIR.mkdir(parents=True, exist_ok=True)
    with INDEX.open("a", encoding="utf-8") as f:
        for k in todo:
            row = {**_fetch(k), "at": datetime.now().isoformat(timespec="seconds")}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            idx[k] = row
            if row["status"] == "fail:429":
                break
    return len(todo)


def text(key):
    """저장소 열쇠 → 정리한 README 앞 4,000자. 없거나 못 받았으면 빈 글."""
    row = _load_index().get(key)
    if not row or row["status"] != "ok":
        return ""
    return clean((DIR / row["file"]).read_bytes().decode("utf-8", errors="replace"))


FENCE = re.compile(r"^\s*(```|~~~)")
INDENTED = re.compile(r"^(\t| {4,})")
NESTED_ITEM = re.compile(r"^\s+([-*+]|\d+[.)])\s")
RST_DIRECTIVE = re.compile(r"^\s*\.\.\s")
UNDERLINE = re.compile(r"^\s*([=\-~^*#+`'\":_.])\1{2,}\s*$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
GRID_RULE = re.compile(r"^\s*\+[-=+]{3,}\+\s*$")
REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")


def _lines(raw):
    """줄 단위로 지운다: 울타리 코드, 빈 줄 뒤 들여 쓴 코드(목록 안쪽 항목은 남김), rst 지시문과 그 옵션 줄, 밑줄·구분선, 링크 정의."""
    out, fenced, in_indent, in_directive, prev_blank = [], False, False, False, True
    for line in raw.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        blank = not line.strip()
        if RST_DIRECTIVE.match(line):
            in_directive = True
            continue
        if in_directive and (blank or line[:1] in " \t"):
            continue
        in_directive = False
        if INDENTED.match(line) and not NESTED_ITEM.match(line) and (prev_blank or in_indent):
            in_indent = True
            continue
        if not blank:
            in_indent = False
        prev_blank = blank
        if UNDERLINE.match(line) or GRID_RULE.match(line) or TABLE_RULE.match(line) or REF_DEF.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def clean(raw, chars=CHARS):
    t = _lines(raw)
    t = re.sub(r"<!--.*?(-->|$)", " ", t, flags=re.S)
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"</?[a-zA-Z][^<>]{0,5000}>", " ", t)
    t = html.unescape(t).replace("[[", "[").replace("]]", "]")
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"!\[[^\]]*\]\[[^\]]*\]", " ", t)
    t = re.sub(r"\[\s*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", t)
    t = re.sub(r"`([^`\n]*)`_", r"\1", t)
    t = re.sub(r"(https?://|www\.)\S+", " ", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = t.replace("|", " ")
    t = re.sub(r"(\*\*|__|`)", "", t)
    return re.sub(r"\s+", " ", t).strip()[:chars]
