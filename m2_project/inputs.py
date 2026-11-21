"""넣는 것 읽기: 공고 하나의 문장과 역량 목록.

받는 것: 한 건의 이름(CASES 의 열쇠). 역량은 팀원이 만든 엑셀(../지원/ 아래, CASES 의 "xlsx")이나 outputs/stages/<공고>.json 에서 온다.
내는 것: build_input → {case, sentences, competencies, posting}.
역량 하나는 {id, name, type, priority, basis, evidence_id} 이고, evidence_id 가 근거 문장의 id 다.
엑셀은 openpyxl 없이 읽는다 (read_xlsx, 파일 맨 아래. 처음 읽을 때는 넘어가도 된다).
"""
import collections
import glob
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from functools import lru_cache
from pathlib import Path

from shared import config, schema

# 엑셀에는 공고 제목과 주소가 없어 손으로 한 결과 파일의 값을 쓴다. "xlsx" 는 지원/ 아래 엑셀 이름의 glob 꼴이다.
# run 은 '일반 방식 × Sonnet' 세 번 가운데 두 번 이상 나온 역량을 모두 담은 실행이다 (naver 2회차, aws 1회차).
CASES = {"aws_fde": {"from": "xlsx", "xlsx": "aws 공고.xlsx", "run": ("general", "claude-sonnet", "1"),
                     "company": "AWS (아마존)", "title": "Forward Deployed Engineer II", "url": ""},
         "naver_ml_intern": {"from": "xlsx", "xlsx": "*(2).xlsx", "run": ("general", "claude-sonnet", "2"),
                             "company": "네이버클라우드",
                             "title": "월드 모델 및 이미지 생성 모델 ML 엔지니어 (체험형 인턴)",
                             "url": "https://inthiswork.com/archives/403902"},
         "K472e3ef0ae": {"from": "stage", "posting": "K472e3ef0ae", "url": ""}}


def xlsx_path(pattern="*(2).xlsx"):
    found = glob.glob(str(config.ROOT.parent / "지원" / pattern))
    if not found:
        raise FileNotFoundError(f"지원/ 아래에서 '{pattern}' 역량 추출 엑셀을 찾지 못했다")
    return found[0]


def xlsx_runs(book):
    """엑셀의 '결과' 시트 → {(method, model, run): [행]}. 엑셀에는 방법·모델·회차마다 한 번의 추출 결과가 있다."""
    runs = collections.defaultdict(list)
    for r in as_dicts(book["결과"]):
        runs[(r["method"], r["model"], r["run"])].append(r)
    return runs


def from_xlsx(path=None, run=("general", "claude-sonnet", "2")):
    """엑셀 한 번의 실행 → {sentences, competencies}. 역량 번호는 실행 안의 순서 C01, C02, ..."""
    book = read_xlsx(path or xlsx_path())
    sentences = [{"id": r["id"], "section": r["section"], "text": r["sentence"]} for r in as_dicts(book["원문"])]
    comps = []
    for n, r in enumerate(xlsx_runs(book)[run], 1):
        comps.append({"id": f"C{n:02d}", "name": r["name"], "type": r["type"], "priority": r["priority"],
                      "basis": r["basis"], "evidence_id": r["evidence_id"]})
    return {"sentences": sentences, "competencies": comps}


@lru_cache(maxsize=1)
def posting_lines():
    """data/banks/posting_lines 표 → {공고 id: 줄 순서대로 정렬한 행}."""
    out = collections.defaultdict(list)
    for r in schema.read("posting_lines"):
        out[r["posting_id"]].append(r)
    return {k: sorted(v, key=lambda r: r["n"]) for k, v in out.items()}


def from_stage(posting_id):
    """outputs/stages/<공고 id>.json 의 competencies → {sentences, competencies, title, company}.
    문장은 posting_lines 표에서 찾는다."""
    d = json.loads((config.OUTPUTS / "stages" / f"{posting_id}.json").read_text(encoding="utf-8"))
    sentences = [{"id": r["id"], "section": r["section"], "text": r["text"]}
                 for r in posting_lines().get(posting_id, [])]
    comps = [{"id": c["cid"], "name": c["name"], "type": c["type"], "priority": c.get("priority", ""),
              "basis": c.get("basis", ""), "evidence_id": c["evidence_id"]}
             for c in d["competencies"]]
    return {"sentences": sentences, "competencies": comps, "title": d.get("title", ""), "company": d.get("company", "")}


def build_input(case_id):
    """CASES 의 한 건 → {case, sentences, competencies, posting}."""
    saved = config.COMPETENCY_DATA / "results" / f"{case_id}.json"      # m1 결과 (공개 레포: 엑셀 대신 JSON)
    if saved.exists():
        return json.loads(saved.read_text(encoding="utf-8"))
    spec = CASES[case_id]
    if spec["from"] == "xlsx":
        path = xlsx_path(spec["xlsx"])
        got = from_xlsx(path, run=spec["run"])
        title, company = spec["title"], spec["company"]
        source = f"지원/{Path(path).name}"
    else:
        got = from_stage(spec["posting"])
        title, company = got.pop("title"), got.pop("company")
        source = f"outputs/stages/{spec['posting']}.json"
    got["posting"] = {"company": company, "title": title, "url": spec["url"], "source": source}
    if "run" in spec:
        method, model, run = spec["run"]
        got["posting"]["run"] = {"method": method, "model": model, "run": int(run)}
    return {"case": case_id, **got}


def evidence_ids(c):
    """역량의 근거 문장 id 목록. 엑셀은 'S03, S04' 처럼 여럿을 한 칸에 적는다."""
    return [x for x in re.split(r"[,\s;/]+", c.get("evidence_id") or "") if x]


def evidence_text(c, by_id):
    """역량의 근거 문장들을 이은 글. by_id 는 {문장 id: 글}."""
    return " ".join(by_id[i] for i in evidence_ids(c) if i in by_id)


_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
_T = "{%s}t" % _NS["m"]


def _column(ref):
    """칸 주소 'C7' → 열 번호 2."""
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def _cell_value(cell, shared):
    v = cell.find("m:v", _NS)
    if cell.get("t") == "s" and v is not None:
        return shared[int(v.text)]
    if cell.get("t") == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(_T))
    return v.text if v is not None else ""


def _sheet_rows(xml, shared):
    rows = []
    for row in ET.fromstring(xml).iter("{%s}row" % _NS["m"]):
        cells = {_column(c.get("r")): _cell_value(c, shared) for c in row.findall("m:c", _NS)}
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def read_xlsx(path):
    """xlsx → {시트 이름: 행 목록}."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter(_T)))
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = {}
    for s in workbook.find("m:sheets", _NS):
        target = rels[s.get("{%s}id" % _NS["r"])]
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        out[s.get("name")] = _sheet_rows(z.read(target), shared)
    return out


def as_dicts(rows):
    """첫 행을 머리줄로 → [{머리: 값}]. 짧은 행은 빈 글로 채운다."""
    head = rows[0]
    return [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in rows[1:]]
