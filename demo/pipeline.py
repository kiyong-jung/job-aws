"""공고 → 화면에 흘려보낼 사건들. 서버(server.py)와 떼어 둬서 시험에서 바로 부른다.

사건 하나는 dict 하나다. 화면(static/js/api.js)이 type 으로 가른다.
  stage      {key, label}                진행 단계 (read → split → find → sort)
  posting    {title, company, url, sections:[{name, items:[{id, text, kind}]}], replay, adapted, case, pending}
                                         replay 는 예시 공고를 저장본으로 다시 틀 때만 true (화면이 그렇다고 적는다).
                                         adapted 는 이 공고의 저장본에 응용 프로젝트가 있다 (③ 쪽 이름이 처음부터 "응용").
                                         case 는 예시 공고의 이름(EXAMPLES 의 열쇠), pending 은 저장본이 아직 없는 단계 → 화면 글
                                         (화면은 그 단계의 단추 대신 그 글을 적는다). 둘 다 예시를 다시 틀 때만
  highlight  {sid, n}                    근거 문장 sid 에 번호 n 을 붙여 칠한다
  row        {row:{id, name, type, priority, basis, sids, badges}}
  done       {rows, marks, required, preferred}
  notice     {text}                      예시가 아닌 공고를 오프라인으로 받았을 때
  error      {reason, message}

프로젝트 찾기(2단계, 요청에 step: "project") 는 따로 흐른다. 역량 표가 끝난 뒤 화면이 부른다.
  steps      {items:[{key, label, done}], db:{papers, repos}, pool, shortlist, seconds, tier:{name, total}, adapted}
                                         fit 은 깔때기 끝 칸 {label, n}: 필수를 다 다룬 후보 수, 그런 후보가 없으면 필수를 가장 많이 다룬 후보 수
                                         (m2_project/local.fit 과 같은 셈. aws_fde 는 필수 8개를 다 다룬 후보가 없다)
                                         seconds 는 실제로 걸린 시간. 저장본에 없으면 null (화면이 시간을 지어내지 않는다)
                                         진행 단계 목록 (label 은 하는 중, done 은 끝난 말)과 패널 그림의 숫자 (모두 저장본 그대로)
  stage      {key, label}                그 단계를 하는 중 (search → scan → rerank → judge → pick). pick 에는 top (1위 후보의 순위 번호, 0부터)
  judged     {n, ranks, scores}          판정 한 묶음(5개)이 끝났다. n 은 지금까지 보낸 수, ranks 는 그 묶음 후보들의 순위 번호(0부터),
                                         scores 는 같은 차례의 필수 점수. 저장본에는 점수가 순위 차례로만 남아 있어 실제로 견준
                                         차례는 모른다. 그래서 순위와 상관없는 정해 둔 차례로 보낸다 (1위가 앞 묶음에 오지 않게)
  project    {sample, ranking, tiers, judged, cells:[{id, tier}]}   고른 샘플(글은 근거 구절로 나눈 parts, heading 은 그 글의 이름)과 위 몇 개의 순위.
             tiers 는 [{name, total}] (화면 이름과 만점), url 은 http·https 만 (아니면 ""). cells 는 덮기 띠의 칸 자리 (역량 표 차례):
             화면이 빈 칸 29개를 묶음별로 먼저 깔고 cover 사건마다 그 칸만 칠한다
  cover      {row:{id, name, section, tier, level, badges}}   역량 하나를 샘플이 다루는 정도 (있음·일부·없음). tier 는 필수·우대·나머지
  adapt      {title, goal, base:{title, url}, parts:[{n, title, short, url, fills}], added, packages:[{name, hours, core, from}],
              hours:{core, extension, total, budget}, before, uncovered:[{name, badges, level}], status}
                                         응용 프로젝트: m2_project/adapt.py 가 1위(바탕)에 다른 프로젝트에서 빌린 부분과 AI가 더한 일을 더한 한 건
                                         (data/*.adapt.json, 있을 때만). parts 는 빌린 프로젝트(번호 n 은 띠 칸 아래 배지), fills 와 added 는 그것이 채운 역량 수.
                                         packages[].from 은 묶음의 출처 이름 (바탕, 빌린 프로젝트의 짧은 이름, AI가 더함). before 는 1위 판정의 셈 (있음 1, 일부 0.5).
                                         uncovered 는 응용 뒤에도 '있음'이 아닌 역량 (교육자료에서 습득)
  fill       {id, level, by, count, label}   칸이 바뀌는 역량 하나: 빌린 부분(by 는 그 번호), AI가 더한 일("new"), 바탕("base": 정도만 바뀜).
                                         count 는 거기까지의 셈 (있음 1, 일부 0.5)
  done       {levels:{있음, 일부, 없음}, before, after}   before·after 는 바탕만일 때와 응용 뒤의 셈 (있음 1, 일부 0.5)
  notice     {text}                      예시가 아닌 공고 (돈이 드는 검색은 하지 않는다)

교육자료 찾기(3단계, step: "materials"). m3_materials/pick.py 의 저장된 결과(data/*.m3.json)를 다시 튼다. 공부 시간은 읽지 않는다.
  steps      {items, funnel:[{n, label}]}   단계 목록: targets → search → judge → pick. funnel 은 숫자 흐름 (은행 → BM25 → Rerank → 고른 자료)
  stage      {key, label}
  target     {row:{cid, name, type, priority}}   대상 역량 하나 (유형이 도구·지식인 것)
  pick       {row:{n, role(핵심|보조), title, kind, url, covers:[{cid, name, level, text}]}, levels:{cid:{level, text}}}
                                         고른 자료 하나. levels 는 그 자료까지 고른 뒤 역량마다 덮인 정도 (화면은 더하지 않는다)
  done       {n, targets, covered, missing:[이름], levels, line, rule, left}   covered 는 있음·일부인 역량 수, line 은 답 맨 위 한 줄

12주 계획 짜기(4단계, step: "weeks"). 예시 공고는 주차 계획 md 를 옮긴 것들(data/<예시>.plan.<한 주 상한>.json, 공부 시간과 상관없음, 기본은 중)이 먼저,
없으면 라운드랩 커리큘럼 생성기 결과 (data/<예시>.curriculum.<주당 시간>.json). 하루 1·2·3시간 = 주당 7·14·21시간.
  steps      {items, key, label, plan:[{week, learning, project, cap, goal, method, activities:[{kind(learning|project), title, hours, out, role, ends, cids}], deliverables}],
              cap, learning, project, total, source(md|generator), held:[{id, name}], plans:[같은 꼴 + summary], default, comps}
             goal·method 는 md 계획만, ends 는 작업이 끝나는 주. plans 는 md 계획이 둘 이상일 때 (화면이 크기를 고른다), 맨 위 값은 기본(중) 계획
  stage      {key, label}                order → place → check
  done       {weeks, cap, inside_weeks, learning, project, deliverables, status, source}   기본 계획의 수 (고른 계획의 수는 steps 의 plans[].summary)

정리 리포트(5단계, step: "report"). 사람이 미리 짠 면접 대비 슬라이드(발표 자료 모양, design/build_report_deck.py)를 고른 공부 시간 안으로 보인다.
  steps      {items, per_day}
  stage      {key, label}                pick → answer → typeset
  done       {slides:[쪽 그림 주소], pptx, filename, bullets:[글 둘]}   slides 는 화면에 차례로 보일 쪽 그림, pptx 는 받기, bullets 는 바닥 줄 불렛 둘 (쪽에 적힌 값만)
"""
import json
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

# 예시 공고: 빈 화면 단추의 차례 (AWS 먼저). 열쇠는 m2_project.CASES 의 이름, 저장본은 data/<이름>.<종류>.json
EXAMPLES = {"aws_fde": {"label": "AWS 공고로 해 보기", "filename": "AWS_Forward_Deployed_Engineer_II.txt"},
            "naver_ml_intern": {"label": "네이버클라우드 공고로 해 보기", "filename": "네이버클라우드_ML엔지니어_인턴.txt"}}
DATA = Path(__file__).resolve().parent / "data"
STAGES = {"read": "공고를 읽는 중", "split": "문장을 나누는 중", "find": "핵심 문장을 찾는 중", "sort": "역량을 정리하는 중"}
# 걸음 사이 간격(초). speed 를 곱한다. 예시 다시 틀기가 8초 안팎이 되게 맞췄다
# 형광펜은 WAVES 번에 나눠 몇 줄씩 함께 칠한다 (사용자 11/19: 1.5초 안에 끝). 0.3초 × 3 틈 + 칠하기 0.3초 = 1.2초
WAVES = 4
PACE = {"stage": 0.4, "chunk": 0.035, "wave": 0.3, "search": 0.45, "batch": 0.03, "cover": 0, "item": 0.16, "fill": 0.12, "week": 0}      # week·cover 0: ⑤ 막대는 한 번에, 덮기 칸은 그리는 곳이 없다 (사용자 11/21: 쓸데없이 기다리지 않게)
SECTION_NAMES = {"필수": "자격요건", "우대": "우대사항", "미션": "담당업무", "소개": "소개"}


def evidence_ids(c):
    """'S03, S04' 처럼 한 칸에 여럿 적힌 근거 문장 id 를 목록으로."""
    return [x for x in re.split(r"[,\s;/]+", c.get("evidence_id") or "") if x]


@lru_cache(maxsize=None)
def example_case(name):
    from m2_project import build_input
    return build_input(name)


@lru_cache(maxsize=1)
def examples():
    """화면에 낼 예시 공고의 이름 (EXAMPLES 차례). m2_project 에 아직 없거나 읽다가 멈추는 것은 빼고 까닭을 적는다
    (한 예시가 깨져도 다른 예시는 돈다)."""
    from m2_project import CASES
    out = []
    for name in EXAMPLES:
        if name not in CASES:
            continue
        try:
            example_case(name)
        except Exception as e:      # m2_project 는 다른 모듈이다: 그 쪽이 깨져도 데모 서버는 뜬다
            print(f"예시 공고 {name} 를 읽지 못해 뺐다: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        out.append(name)
    return tuple(out)


def which(text):
    """붙여넣은 글과 같은 예시 공고 (build_input 결과). 없으면 None."""
    return next((example_case(n) for n in examples() if matches(text, example_case(n))), None)


def data_file(name, kind):
    return DATA / f"{name}.{kind}.json"


def saved(name, kind):
    """예시 공고 name 의 저장본 data/<name>.<kind>.json. 없으면 None (그 단계는 pending 이 막는다)."""
    f = data_file(name, kind)
    return _read(f) if f.exists() else None


@lru_cache(maxsize=None)
def _read(f):
    return json.loads(f.read_text(encoding="utf-8"))


# 2~5단계: 요청의 step → 화면 이름과 그 단계가 읽는 저장본의 종류. 하나라도 없으면 그 단계는 준비 중이다
STEPS = {"project": ("프로젝트 찾기", ("project",)), "materials": ("교육자료 찾기", ("m3",)),
         "weeks": ("12주 계획 짜기", ("materials", "weeks")), "report": ("정리 리포트 만들기", ("project", "materials", "weeks", "report"))}


def pending(name):
    """저장본이 아직 없는 단계 → 화면 글 {step: 글}. 화면은 그 단계의 단추 대신 이 글을 적고, 서버도 같은 글로 막는다."""
    return {k: f"이 공고의 {what}는 아직 준비 중이에요." for k, (what, kinds) in STEPS.items()
            if not all(data_file(name, x).exists() for x in kinds)}


def posting_text(case):
    """문장 목록 → 사람이 붙여넣을 법한 공고 글. 구역 이름을 머리줄로, 마침표가 없는 문장은 불릿으로."""
    out, last = [], None
    for s in case["sentences"]:
        if s["section"] != last:
            out += ["", s["section"]] if out else [s["section"]]
            last = s["section"]
        out.append(s["text"] if s["text"].endswith(".") else f"- {s['text']}")
    return "\n".join(out)


def _squash(text):
    return re.sub(r"\s+", "", text)


def matches(text, case, share=0.6):
    """붙여넣은 글에 저장본 문장 머리(공백 없이 20자)가 share 이상 들어 있으면 같은 공고로 본다."""
    flat = _squash(text)
    hits = sum(_squash(s["text"])[:20] in flat for s in case["sentences"])
    return hits >= share * len(case["sentences"])


def sections(sentences):
    """문장 → 구역별 묶음. 마침표로 끝나는 문장은 문단(p), 아니면 목록(li)."""
    out = []
    for s in sentences:
        if not out or out[-1]["name"] != s["section"]:
            out.append({"name": s["section"], "items": []})
        kind = "p" if s["text"].rstrip().endswith((".", "다", "요")) else "li"
        out[-1]["items"].append({"id": s["id"], "text": s["text"], "kind": kind})
    return out


def plan(sentences, competencies):
    """근거 문장에 공고 순서대로 번호를 붙이고, 역량 줄마다 그 번호(배지)를 단다.
    한 문장에서 역량이 여럿 나오면 그 줄들은 같은 번호를 나눠 가진다. 근거가 공고에 없는 역량은 버린다."""
    order = {s["id"]: i for i, s in enumerate(sentences)}
    used = sorted({sid for c in competencies for sid in evidence_ids(c) if sid in order}, key=order.get)
    number = {sid: n for n, sid in enumerate(used, 1)}
    rows = []
    for c in competencies:
        sids = sorted((x for x in evidence_ids(c) if x in number), key=order.get)
        if sids:
            rows.append({"id": c["id"], "name": c["name"], "type": c["type"], "priority": c["priority"],
                         "basis": c.get("basis", ""), "sids": sids, "badges": [number[x] for x in sids]})
    rows.sort(key=lambda r: (r["badges"][0], r["id"]))
    return [{"sid": sid, "n": number[sid]} for sid in used], rows


def stage(key, speed):
    yield {"type": "stage", "key": key, "label": STAGES[key]}
    time.sleep(PACE["stage"] * speed)


def paint(sentences, competencies, posting, speed, stop=None):
    """문장 나누기 뒤의 공통 흐름: 원문 → 근거 문장 칠하기(줄 함께) → 정리 → 끝. competencies 는 목록이나 목록을 내는 함수.
    stop 이 'split' 이면 원문만, 숫자면 그만큼 칠하고 멈춘다(화면 찍기용)."""
    yield {"type": "posting", **posting, "sections": sections(sentences),
           "ko": {s["id"]: ko(s["text"]) for s in sentences if ko(s["text"])}}
    if stop == "split":
        return
    yield from stage("find", speed)
    marks, rows = plan(sentences, competencies() if callable(competencies) else competencies)
    size = -(-len(marks) // WAVES) or 1      # 한 번에 함께 칠하는 줄 수
    for i, m in enumerate(marks, 1):
        yield {"type": "highlight", **m}
        for r in rows:
            if r["badges"][0] == m["n"]:
                yield {"type": "row", "row": r}
        if isinstance(stop, int) and i >= stop:
            return
        if i % size == 0 and i < len(marks):
            time.sleep(PACE["wave"] * speed)
    yield from stage("sort", speed)
    need = sum(r["priority"] == "필수" for r in rows)
    plus = sum(r["priority"] == "우대" for r in rows)
    yield {"type": "done", "rows": len(rows), "marks": len(marks), "required": need, "preferred": plus}


def posting_shot(name):
    """실제 공고 사이트 화면과 핵심 문장 자리 (design/build_posting_shot.py). 없으면 None (화면은 원문 글에 칠한다)"""
    f = DATA / f"{name}.posting.json"
    if not f.is_file() or not (DATA / f"{name}.posting.png").is_file():
        return None
    meta = json.loads(f.read_text(encoding="utf-8"))
    return {"png": f"/posting/{name}.png", "url": meta["url"], "width": meta["width"], "height": meta["height"], "marks": meta["marks"]}


def replay(case, speed=1.0, stop=None):
    """저장된 예시 결과를 단계마다 간격을 두고 흘린다. 모델을 부르지 않는다."""
    p = case["posting"]
    yield from stage("read", speed)
    yield from stage("split", speed)
    yield from paint(case["sentences"], case["competencies"], {"title": p["title"], "company": p["company"], "url": p.get("url", ""), "replay": True,
                                                               "adapted": bool(adapt_case(case["case"])), "case": case["case"], "pending": pending(case["case"]),
                                                               "shot": posting_shot(case["case"])},
                     speed, stop)


def live(text, title="", url="", speed=1.0, extract=None):
    """새 공고를 실제로 돌린다. 문장 나누기는 m1_competency.collect, 역량 뽑기는 m1_competency.extract(돈이 든다)."""
    from m1_competency import collect
    if extract is None:
        from m1_competency.extract import extract
    yield from stage("read", speed)
    posting = collect.from_text(title, text)
    yield from stage("split", speed)
    sentences = [{"id": x["line_id"], "section": SECTION_NAMES.get(x["section"], x["section"]), "text": x["text"]}
                 for x in collect.lines(posting)]
    got = []

    def comps():      # 근거 문장 찾기 단계가 화면에 뜬 뒤에 부른다 (몇십 초 걸린다)
        got.extend({**c, "id": c.get("cid") or c.get("id")} for c in extract(posting))
        return got
    yield from paint(sentences, comps, {"title": posting["title"], "company": "", "url": url}, speed)
    # 다음 단계(demo/live.py)가 쓸 공고 한 건 (m2_project.inputs.build_input 과 같은 꼴). 화면이 들고 있다가 단계 요청에 싣는다
    yield {"type": "live_state", "key": "case", "value": {"case": posting["id"], "sentences": sentences, "competencies": got,
                                                         "posting": {"title": posting["title"], "company": "", "url": url}}}


def plain_sentences(text):
    """모델 없이 줄만 나눈다. 짧고 마침표 없는 줄은 구역 이름으로 본다."""
    out, sec = [], "공고"
    for n, line in enumerate((x.strip() for x in text.splitlines()), 1):
        body = line.lstrip("-•·*#> ").strip()
        if not body:
            continue
        if len(body) <= 20 and not body.endswith((".", "다", "요")) and not line.startswith(("-", "•", "*")):
            sec = body.strip("[]【】:")
        else:
            out.append({"id": f"L{n:03d}", "section": sec, "text": body})
    return out


def offline(text, title=""):
    """오프라인에서 예시가 아닌 공고: 원문만 보여 주고 이유를 쉬운 말로 알린다."""
    yield from stage("read", 0.3)
    yield from stage("split", 0.3)
    first = next((x.strip() for x in text.splitlines() if x.strip()), "붙여넣은 공고")
    yield {"type": "posting", "title": title or first[:60], "company": "", "url": "",
           "sections": sections(plain_sentences(text))}
    # 새 공고를 끝까지 보려면 서버를 --live 로 켠다 (README). 그 말은 화면에 내지 않는다
    yield {"type": "notice", "text": "지금은 예시 공고만 보여 드릴 수 있어요. 원문은 오른쪽에 펼쳐 두었어요."}


# ── 2단계: 역량 → 프로젝트 ──────────────────────────────────────────
# 저장본(data/<예시>.project.json)은 outputs/project/<예시>.local.json 에서 화면에 쓰는 것만 옮겨 온 것 (README). 돈이 드는 검색·판정은 하지 않는다
# 순위는 앞 단계부터 견준다 (m2_project/pick.py TIERS 와 같다): 필수를 하나라도 더 다루는 후보가 먼저, 같으면 우대, 그다음 나머지.
# 단계는 역량의 필수·우대 표시로 가른다 (둘 다 아니면 나머지). 저장본의 열쇠이자 화면 이름이다 (표 머리·설명·첫 글 모두 이 이름)
TIERS = ("필수", "우대", "나머지")


def tier_of(c):
    return c["priority"] if c["priority"] in TIERS[:2] else TIERS[2]


def said(case, cid):
    """역량 cid 의 근거가 된 공고 문장 (첫 문장 그대로). 없으면 빈 글"""
    comp = next((c for c in case["competencies"] if c["id"] == cid), None)
    text = {s["id"]: s["text"] for s in case["sentences"]}
    return next((text[x] for x in evidence_ids(comp) if x in text), "") if comp else ""


LEVEL_RANK = {"있음": 0, "일부": 1, "없음": 2}


@lru_cache(maxsize=1)
def _ko():
    f = DATA / "ko.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


@lru_cache(maxsize=1)
def _proofs():
    f = DATA / "proof" / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def proof_shot(url, quote):
    """근거 구절의 원문 캡처 (design/build_proof_shots.py, 구절에 형광펜). 없으면 빈 글 (화면은 글과 원문 링크만)"""
    pid = _proofs().get(f"{url}\t{quote}")
    return f"/proof/{pid}.png" if pid and (DATA / "proof" / f"{pid}.png").is_file() else ""


def ko(text):
    """영어 근거 문장의 한국어 옮김 (data/ko.json, 사람이 옮김). 없으면 빈 글 (화면은 원문을 그대로 쓴다)"""
    return _ko().get((text or "").strip(), "")


def fit_rows(case, cov, body):
    """② 1위가 왜 이 공고에 맞나 (사용자 11/21: 근거 문장을 보여 줘라). 필수·우대 역량마다 공고 문장과 1위 글의 근거 구절, 판정.
    필수 먼저, 같은 묶음 안에서는 다룸 → 일부만 → 없음 차례"""
    rows = [{"cid": c["cid"], "name": c["name"], "tier": tier_of(c), "level": c["level"], "posting": said(case, c["cid"]),
             "quote": unbreak(c.get("quote") or "", body)} for c in cov if tier_of(c) in TIERS[:2]]
    rows = [{**r, "posting_ko": ko(r["posting"]), "quote_ko": ko(r["quote"])} for r in rows]
    return sorted(rows, key=lambda r: (TIERS.index(r["tier"]), LEVEL_RANK[r["level"]]))
KIND = {"paper": "논문", "repo": "저장소"}
BATCH = 5      # 판정 한 번에 견주는 후보 수 (m2_project/pick.py BATCH 와 같다)
TOPIC = {"paper": "이", "repo": "가"}      # 논문이, 저장소가


def project_case(name):
    return saved(name, "project")


# 응용 프로젝트: m2_project/adapt.py 가 1위를 바탕으로 만든 한 건에서 화면에 쓰는 값만 옮긴 것 (design/build_adapt.py). 없으면 ② 는 1위 요약에서 끝난다
def adapt_case(name):
    return saved(name, "adapt")


def where(item):
    """논문은 '학회 연도', 저장소는 '★별 수'."""
    if item["kind"] == "repo":
        return f"★{item['stars']:,}" if item.get("stars") else "GitHub"
    return " ".join(x for x in (item.get("venue", ""), str(item.get("year", ""))) if x)


def web(url):
    """화면에 링크로 낼 주소는 http·https 만. 다른 것(javascript: 등)은 빈 값이라 화면이 링크를 달지 않는다."""
    return url if re.match(r"https?://", url or "") else ""


def unbreak(text, whole=None):
    """PDF 줄바꿈이 남긴 'mod- els' 를 고친다. 붙인 낱말('models')이 글 전체(whole)에 따로 나오면 붙이고,
    붙임표 낱말('high-quality')이 나오면 붙임표로 잇는다. 둘 다 없으면 그대로 둔다 ('data- and compute-efficient', 'state- of-the-art').
    저장본은 outputs/ 와 글자까지 같게 두고(시험이 본다) 화면에 낼 때만 고친다."""
    seen = set(re.findall(r"[\w-]+", (whole or text).lower()))

    def fix(m):
        a, b = m.group(1), m.group(2)
        return a + b if (a + b).lower() in seen else f"{a}-{b}" if f"{a}-{b}".lower() in seen else m.group(0)
    return re.sub(r"\b([A-Za-z]+)- ([a-z]+)\b", fix, text)


def points(x):
    return f"{x:g}"      # 5.0 → 5, 4.5 → 4.5 (글 안에서)


def quote_parts(text, coverage):
    """요약 글을 판정이 인용한 구절과 나머지로 나눈다. 구절은 문장부호·공백이 달라도 낱말 순서로 찾고, 겹치면 합친다.
    구절은 고치기 전 글('mod- els' 그대로)에서 옮겨 왔으니 고치기 전 글에서 찾고, unbreak 는 나눈 뒤에 한다."""
    spans = []
    for c in coverage:
        words = re.findall(r"\w+", c.get("quote") or "")
        m = re.search(r"\W+".join(map(re.escape, words)), text) if words else None
        if m:
            spans.append([m.start(), m.end(), {c["cid"]}])
    merged = []
    for a, b, ids in sorted(spans, key=lambda x: x[0]):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
            merged[-1][2] |= ids
        else:
            merged.append([a, b, set(ids)])
    parts, at = [], 0
    for a, b, ids in merged:
        if a > at:
            parts.append({"text": text[at:a]})
        parts.append({"text": text[a:b], "cids": sorted(ids)})
        at = b
    if at < len(text):
        parts.append({"text": text[at:]})
    return parts


def project_steps(counts):
    # 하는 중과 끝난 말은 같은 일을 같은 말로 ("DB" 는 사용자가 고른 말이라 그대로 둔다). 깔때기: DB → 낱말로 모은 후보 → 뜻으로 다시 고른 후보 → 1위
    seen = f"논문 {counts['papers']:,}개와 저장소 {counts['repos']:,}개에서 낱말이 맞는 후보 {counts['pool']:,}개를"
    again = f"역량마다 뜻이 가까운 후보 {counts['shortlist']:,}개로"
    return [{"key": "search", "label": "역량으로 DB를 검색하는 중", "done": "역량으로 DB를 검색했어요"},
            {"key": "scan", "label": f"{seen} 모으는 중", "done": f"{seen} 모았어요"},
            {"key": "rerank", "label": f"{again} 줄이는 중", "done": f"{again} 줄였어요"},
            {"key": "judge", "label": f"다시 고른 후보 {counts['shortlist']:,}개를 역량마다 견줘 보는 중",
             "done": f"다시 고른 후보 {counts['judged']:,}개를 역량마다 견줘 봤어요"},
            # 이 후보의 이름은 어디서나 "1위" (② 띠만 "필수 먼저 1위": 무엇이 먼저인지 그 자리에서 말한다)
            {"key": "pick", "label": f"{TIERS[0]}를 가장 많이 다루는 1위를 고르는 중", "done": f"{TIERS[0]}를 가장 많이 다루는 1위를 골랐어요"}]


# 응용 프로젝트가 저장본에 있을 때만 붙는 두 단계
ADAPT_STEPS = [{"key": "borrow", "label": "1위가 못 다룬 역량을 채울 부분을 고르는 중", "done": "1위가 못 다룬 역량을 채울 부분을 골랐어요"},
               {"key": "merge", "label": "1위에 빌린 부분을 더해 한 프로젝트로 묶는 중", "done": "1위에 빌린 부분을 더해 한 프로젝트로 묶었어요"}]
# 묶음의 종류 셋 (④ 저장본의 kind): 바탕, 빌림(다른 프로젝트에서 빌린 부분), 새로 더함(다른 프로젝트 없이 새로 더한 일)
NEW = "새로 더함"
# 덮는 정도의 셈 (발표 자료와 같다): 있음 1, 일부 0.5
WORTH = {"있음": 1, "일부": 0.5, "없음": 0}
AI_ADDED = "AI가 더함"      # 다른 프로젝트 없이 AI 가 새로 더한 일 (저장본 packages[].added)


def adapt_fills(a, judged):
    """응용 뒤에 정도가 바뀌는 역량마다 누가 채웠나. judged 는 1위 판정 {역량 id: 있음·일부·없음}.
    by: 보완 프로젝트 번호(1부터, 저장본 complements 차례) > "base"(바탕의 일이 정도만 바꿈) > "new"(AI가 더함). 출처가 없으면 멈춘다.
    판정보다 낮아지는 칸은 바탕의 일을 덜 쓰는 것뿐이다 (aws_fde 의 Go: 팀 주 언어를 TypeScript 로 잡아 일부.
    React: 묶음 글에 React 가 없어 뺐고 출처도 없다, 교육자료에서 배움). 다른 출처면 멈춘다.
    package 는 덮기 표가 그 역량을 배운다고 적은 묶음 (AI가 더한 일은 다른 묶음의 added 에 적히기도 한다: Blender 는 W5 에, 배우는 곳은 W4)."""
    lent = {c["title"]: n for n, c in enumerate(a["complements"], 1)}
    pkg = {p["id"]: p["name"] for p in a["packages"]}
    out = []
    for c in a["coverage"]:
        cid, was, level = c["id"], judged[c["id"]], c["expect"]
        if level == was:
            continue
        src = [s["project"] for p in a["packages"] for s in p["sources"] if cid in s["for"]]
        by = next((lent[t] for t in src if t in lent), None) or ("base" if a["base"]["title"] in src else None) \
            or ("new" if any(cid in p["added"] for p in a["packages"]) else None) \
            or ("base" if WORTH[level] < WORTH[was] else None)
        by = by or "new"      # 출처가 없으면 AI가 더한 일로 본다 (새 공고는 저장본처럼 미리 확인하지 못한다)
        if WORTH[level] < WORTH[was]:
            by = "base"
        out.append({"cid": cid, "was": was, "level": level, "by": by, "package": names(pkg[k] for k in c["packages"]) or "교육자료에서 배움"})
    return out


def words(text, case, packages):
    """AI가 더한 까닭 글을 화면 말로: 할 일을 말하는 마디만 남기고 모듈 안의 셈(BASE, complement, 셀, added)을 말하는 마디는 뺀다.
    남은 마디의 역량·묶음 id(C40, W4)는 이름으로"""
    names = {c["id"]: c["name"] for c in case["competencies"]} | {p["id"]: f"'{p['name']}'" for p in packages}
    parts = re.split(r"(?<=[.다])\s+|(?<=며),\s+", text)
    keep = [s for s in parts if not re.search(r"BASE|complement|셀|added|입력 프로젝트", s)] or parts
    out = " ".join(re.sub(r"며$", "다.", re.sub(r"하며$", "한다.", s)) for s in keep)
    return re.sub(r"(?<![A-Za-z0-9])([CW]\d{1,2})(?!\d)", lambda m: names.get(m.group(1), m.group(1)), out)


def adapt_tiers(a, judged):
    """필수·우대 묶음마다 응용 전(1위 판정)과 뒤(덮기 표)의 셈 (있음 1, 일부 0.5)"""
    out = []
    for name in TIERS[:2]:
        cs = [c for c in a["coverage"] if c["tier"] == name]
        out.append({"name": name, "total": len(cs), "before": sum(WORTH[judged[c["id"]]] for c in cs), "after": sum(WORTH[c["expect"]] for c in cs)})
    return out


def fill_evidence(case, a, fills, cov):
    """③ 1위에 없던(또는 일부만 다룬) 필수·우대 역량을 어떤 일로 채우나: 공고 문장, 채우는 일(묶음 이름과 할 일), 그 근거
    (빌린 프로젝트면 그 글의 구절, AI가 더한 일이면 더한 까닭, 바탕이면 1위 글의 구절), 출처 이름"""
    tier = {c["cid"]: tier_of(c) for c in cov}
    short = {c["title"]: c["short"] for c in a["complements"]} | {a["base"]["title"]: BASE}
    link = {c["title"]: web(c["url"]) for c in a["complements"]} | {a["base"]["title"]: web(a["base"]["url"])}
    out = []
    for x in fills:      # 오른 칸만 (판정보다 낮아진 칸은 바탕의 일을 덜 쓰는 것이라 "채움"이 아니다, adapt_fills)
        if tier.get(x["cid"]) not in TIERS[:2] or WORTH[x["level"]] <= WORTH[x["was"]]:
            continue
        cid, by, src, proof, job = x["cid"], x["by"], AI_ADDED, "", None
        want = a["complements"][by - 1]["title"] if isinstance(by, int) else a["base"]["title"] if by == "base" else None
        for p in sorted(a["packages"], key=lambda p: p["order"]):
            hit = next((s for s in p["sources"] if cid in s["for"] and s["project"] == want), None)
            if hit:
                src, proof, job = short[want], hit.get("quote", ""), p
                break
            if want is None and cid in p.get("why", {}):
                proof, job = words(p["why"][cid], case, a["packages"]), p
                break
        name = next(c["name"] for c in a["coverage"] if c["id"] == cid)
        out.append({"cid": cid, "name": name, "tier": tier[cid], "was": x["was"], "level": x["level"], "posting": said(case, cid),
                    "job": job["name"] if job else x["package"], "proof": proof, "from": src, "url": link.get(want, "") if want else ""})
    return sorted(out, key=lambda r: (TIERS.index(r["tier"]), LEVEL_RANK[r["level"]]))


def final_rows(case, a, judged, filled, cov, body):
    """② 최종 응용 프로젝트 한 쪽 (사용자 11/21: 1위와 응용을 따로 두지 말고 최종만). 필수·우대 역량마다 한 줄:
    공고 문장 | 이 프로젝트에서 다루는 곳과 근거. 채운 역량은 fill_evidence 그대로(빌린 구절·AI가 더한 일),
    1위가 원래 다루는 역량은 1위 글의 구절, 끝까지 없는 역량은 교육자료에서 배운다고 적는다. 필수 먼저, 다룸 → 일부만 → 없음 차례"""
    got = {r["cid"]: r for r in filled}
    quote = {c["cid"]: unbreak(c.get("quote") or "", body) for c in cov}
    pkg = {p["id"]: p["name"] for p in a["packages"]}
    rows = []
    for c in a["coverage"]:
        cid = c["id"]
        if c["tier"] not in TIERS[:2]:
            continue
        if cid in got:
            rows.append(got[cid])
            continue
        job = names(pkg[k] for k in c["packages"] if k in pkg)
        base = c["expect"] != "없음" and quote.get(cid)
        rows.append({"cid": cid, "name": c["name"], "tier": c["tier"], "was": judged.get(cid, "없음"), "level": c["expect"],
                     "posting": said(case, cid), "job": job if base else "교육자료에서 배워요",
                     "proof": quote[cid] if base else "프로젝트로는 다루지 않아요. 다음 단계에서 이 역량을 가르치는 교육자료를 골라요.",
                     "from": BASE if base else "", "url": web(a["base"]["url"]) if base else ""})
    rows = [{**r, "posting_ko": ko(r["posting"]), "proof_ko": ko(r["proof"]), "shot": proof_shot(r.get("url", ""), r["proof"])} for r in rows]
    return sorted(rows, key=lambda r: (TIERS.index(r["tier"]), LEVEL_RANK[r["level"]]))


def package_from(p, a):
    """묶음이 어디서 왔나: 바탕, 보완 프로젝트의 짧은 이름, AI가 더함 (그 차례로, 한 번씩)."""
    used = {s["project"] for s in p["sources"]}
    return ([BASE] if a["base"]["title"] in used else []) + [c["short"] for c in a["complements"] if c["title"] in used] + ([AI_ADDED] if p["added"] else [])


BASE = "바탕"


def plain(text, case, packages=()):
    """손 사례의 까닭 글을 화면 말로: 문장 id(S21)는 "공고의 한 문장", 역량 id(C19)는 그 이름, 묶음 id(W5)는 그 묶음 이름, 모듈 이름은 뺀다."""
    names = {c["id"]: c["name"] for c in case["competencies"]}
    jobs = {q["id"]: q["name"] for q in packages}
    t = re.sub(r"\b(C\d{2})\b", lambda m: names.get(m.group(1), "그 역량"), text)
    t = re.sub(r"\b(W\d{1,2})\b", lambda m: f"'{jobs[m.group(1)]}'" if m.group(1) in jobs else "다른 묶음", t)
    t = re.sub(r"공고 S\d{2}", "공고의 한 문장", t)
    t = re.sub(r"\bS\d{2}\b", "공고의 한 문장", t)
    return re.sub(r"커리큘럼\(m\d\)|커리큘럼", "주차 계획", t)


def ranking_rule(ranking, tiers):
    """순위 표 아래의 보기 한 줄: 아래 단계 점수가 1위보다 높아도 필수가 낮아 뒤에 선 후보가 위 몇 개 안에 있으면 그 후보로 말한다. 없으면 빈 글."""
    top, (a, b, c) = ranking[0], TIERS
    for i, r in enumerate(ranking[1:], 2):
        if r[a] < top[a] and r[b] > top[b] and r[c] > top[c]:
            return f"그래서 {i}위 {r['title'].split(':')[0]}는 {b}·{c}가 1위보다 높아도 {a}가 {points(r[a])}점이라 {i}위예요."
    return ""


def decided(ranking, i):
    """i번째 줄의 순위를 가른 칸: 바로 위 줄과 처음 다른 단계의 번호 (첫 줄은 0)."""
    if not i:
        return 0
    return next((k for k, t in enumerate(TIERS) if ranking[i][t] != ranking[i - 1][t]), len(TIERS) - 1)


def judge_order(n):
    """다시 틀 때 판정 묶음을 보내는 차례: 순위 r 을 (r*7919 + n//2 + 1) % n 자리에 둔다. 7919 는 소수이고 n(100, 200)의
    약수가 아니라 0..n-1 을 한 번씩 다 지나고(순열), n//2 + 1 이 1위(r=0)를 한가운데로 보낸다. 돌 때마다 같다."""
    return sorted(range(n), key=lambda r: (r * 7919 + n // 2 + 1) % n)


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+")
# 저장해 둔 README 에서 코드 블록을 지운 자리에 머리말만 남은 것 (이 샘플의 것). 화면에 낼 때만 뺀다
LEFTOVER = re.compile(r"\b(?:Install & run|Or compose in Python):\s*")


def tidy(text):
    """저장소 소개 글(README)을 화면에 낼 때만 다듬는다: 그림 문자, 코드 블록이 남긴 머리말, 강조·인용 표시를 빼고
    문단과 목록에서 줄을 바꾼다. 저장본은 그대로 둔다. 낱말은 건드리지 않아 근거 구절(quote_parts)은 다듬은 글에서도 그대로 찾는다."""
    t = LEFTOVER.sub("", text)
    t = re.sub(r"\*([^*\n]+)\*", r"\1", t)                     # *강조*
    t = re.sub(r"(?:^|\s)>\s+", "\n\n", t)                      # 인용 표시
    t = EMOJI.sub(" ", t)                                       # 그림 문자
    t = re.sub(r"\s+(?=\d\. [A-Z])", "\n\n", t)                # 1. 2. 3. 대목
    t = re.sub(r" - (?=\S)", "\n- ", t)                         # 목록
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


LIVE_BUDGETS = [{"key": "84", "hours": 84, "per_day": 1}, {"key": "168", "hours": 168, "per_day": 2}, {"key": "252", "hours": 252, "per_day": 3}]


def project(case, speed=1.0, data=None, live=False):
    """저장된 2단계 결과를 다시 튼다. 역량 표의 문장 번호(plan)를 그대로 달아, 화면이 줄 ↔ 원문 문장을 짝짓게 한다.
    live: 새 공고 (demo/live.py 가 data 를 만들어 넘긴다). 단계·판정 사건은 live.py 가 실제 때에 내고, 여기서는 결과 사건만. 응용은 다음 요청(adapt_part)"""
    name_ = case["case"]
    data = data or project_case(name_)
    counts, cov, sample = data["counts"], data["coverage"], data["sample"]
    adapted = None if live else adapt_case(name_)
    budgets = LIVE_BUDGETS if live else budget_list(name_)
    steps, scores = project_steps(counts) + (ADAPT_STEPS if adapted else []), data["scores"]
    tiers = [{"name": name, "total": sum(tier_of(c) == name for c in cov)} for name in TIERS]
    full = sum(x == tiers[0]["total"] for x in scores)      # 필수를 다 다룬 후보 수
    fit = {"label": f"{TIERS[0]}를 다 다룬 후보", "n": full} if full else {"label": f"{TIERS[0]}를 가장 많이 다룬 후보", "n": scores.count(max(scores))}
    if not live:
        yield {"type": "steps", "items": steps, "db": {"papers": counts["papers"], "repos": counts["repos"], "total": counts["papers"] + counts["repos"]}, "pool": counts["pool"],
               "shortlist": counts["shortlist"], "seconds": data["seconds"], "tier": tiers[0], "fit": fit, "adapted": bool(adapted),
               "names": data.get("names")}      # 단계별 실제 후보 이름 (design/build_names.py)
    only = (f"{TIERS[0]} {tiers[0]['total']}개를 다 다룬 후보는 " + ("이것 하나예요" if full == 1 else f"{full}개예요")) if full else ""
    for s in ([] if live else steps[:len(steps) - len(ADAPT_STEPS) if adapted else len(steps)]):
        # pick 에는 최종 순위를 싣는다 (order[k] = k번째로 설 후보의 번호. 저장본의 차례가 곧 필수 → 우대 → 나머지 순위다). 화면은 순위를 셈하지 않는다
        yield {"type": "stage", "key": s["key"], "label": s["label"],
               **({"top": 0, "order": list(range(len(scores))), "full": full, "note": only} if s["key"] == "pick" else {})}
        # 판정은 5개씩 묶어 보낸다 (m2_project/pick.py BATCH 와 같은 크기). 점수는 저장본 그대로지만 저장본은 순위 차례로만 남아
        # 실제로 견준 차례를 모른다. 순위 차례로 보내면 1위가 맨 앞에 와 결과를 미리 말하니, 순위와 상관없는 정해 둔 차례로 보낸다
        if s["key"] == "judge":
            order = judge_order(len(scores))
            for i in range(0, len(order), BATCH):
                ranks = order[i:i + BATCH]
                yield {"type": "judged", "n": min(i + BATCH, len(scores)), "ranks": ranks, "scores": [scores[r] for r in ranks]}
                time.sleep(PACE["batch"] * speed)
        else:
            time.sleep(PACE["search"] * speed)
    # 저장소는 판정이 읽은 소개 글(README)에서 근거 구절이 든 곳만 보인다 (저장본의 readme_shown. 없으면 앞부분 전체). 논문은 요약 글
    body = sample.get("readme_shown") or (tidy(sample["readme"]) if sample.get("readme") else sample["text"])
    heading = "소개 글에서 근거 구절이 있는 곳" if sample.get("readme_shown") else "소개 글 앞부분" if sample.get("readme") else "요약"
    _, rows = plan(case["sentences"], case["competencies"])
    badges = {r["id"]: r["badges"] for r in rows}
    level = {c["cid"]: c for c in cov}
    yield {"type": "project", "judged": counts["judged"], "tiers": tiers, "adapted": bool(adapted) or live, "rule": ranking_rule(data["ranking"], tiers),
           # 덮기 띠의 칸 자리 (역량 표와 같은 차례, 묶음은 필수 | 우대 | 나머지). 화면은 빈 칸을 먼저 깔고 cover 사건마다 그 칸만 칠한다
           "cells": [{"id": r["id"], "tier": tier_of(level[r["id"]])} for r in rows if r["id"] in level],
           "sample": {"title": sample["title"], "kind": KIND[sample["kind"]], "where": where(sample), "url": web(sample["url"]),
                      "heading": heading, "cut": bool(sample.get("readme_shown")),
                      "parts": [{**x, "text": unbreak(x["text"], body)} for x in quote_parts(body, cov)]},
           "ranking": [{"rank": i, "title": r["title"], "kind": KIND[r["kind"]], "where": where(r), "url": web(r["url"]),
                        "scores": [r[k] for k in TIERS], "decided": decided(data["ranking"], i - 1)} for i, r in enumerate(data["ranking"], 1)],
           # 결과와 근거 (사용자 11/21): 1위 소개 한 줄과 필수·우대 역량마다 "공고 문장 ↔ 1위 글의 구절"
           "fit": {"intro": data.get("intro"), "rows": fit_rows(case, cov, body)}}
    levels = {k: sum(c["level"] == k for c in cov) for k in ("있음", "일부", "없음")}
    for r in rows:      # 역량 표와 같은 순서 (문장 번호 차례)
        c = level.get(r["id"])
        if c:
            yield {"type": "cover", "row": {"id": r["id"], "name": r["name"], "section": c["section"], "tier": tier_of(c),
                                            "level": c["level"], "badges": badges[r["id"]]}}
            time.sleep(PACE["cover"] * speed)
    if live:      # 응용은 다음 요청에서 (Vercel 300초 안에 들게 둘로 나눈다)
        yield {"type": "pending_adapt", "levels": levels}
        return
    if not adapted:
        yield {"type": "done", "levels": levels, "budgets": budgets}
        return
    yield from adapt_part(case, data, adapted, speed, budgets)


def adapt_part(case, data, adapted, speed=1.0, budgets=None):
    """응용 프로젝트 사건들 (저장본은 project() 끝에서, 새 공고는 live.py 의 두 번째 요청에서)."""
    cov, sample = data["coverage"], data["sample"]
    body = sample.get("readme_shown") or (tidy(sample["readme"]) if sample.get("readme") else sample.get("text", ""))
    _, rows = plan(case["sentences"], case["competencies"])
    badges = {r["id"]: r["badges"] for r in rows}
    levels = {k: sum(c["level"] == k for c in cov) for k in ("있음", "일부", "없음")}
    # 응용 프로젝트: m2_project/adapt.py 가 1위(바탕)에 보완 프로젝트에서 빌린 부분과 AI가 더한 일을 더한 한 건 (data/*.adapt.json).
    # 셈은 있음 1, 일부 0.5. 처음 수는 1위 판정 그대로 (대화 칸 덮기 띠), 끝 수는 저장본의 덮기 표(expect)에서 센 값
    borrow, merge = ADAPT_STEPS
    yield {"type": "stage", "key": borrow["key"], "label": borrow["label"]}
    time.sleep(PACE["search"] * speed)
    judged = {c["cid"]: c["level"] for c in cov}
    fills = adapt_fills(adapted, judged)
    before, after = sum(WORTH[v] for v in judged.values()), sum(WORTH[c["expect"]] for c in adapted["coverage"])
    left = [c for c in adapted["coverage"] if c["expect"] != "있음"]
    yield {"type": "adapt", "title": adapted["title"], "goal": adapted["goal"], "status": "AI가 미리 만든 결과를 다시 보여 드려요",
           "base": {"title": adapted["base"]["title"], "url": web(adapted["base"]["url"])},
           # 빌린 프로젝트: 번호(띠 칸 아래 배지)와 그 프로젝트가 채운 역량 수
           "parts": [{"n": n, "title": c["title"].strip('"'), "short": c["short"], "url": web(c["url"]), "fills": sum(x["by"] == n for x in fills)}
                     for n, c in enumerate(adapted["complements"], 1)],
           "added": sum(x["by"] == "new" for x in fills),
           "packages": [{"name": p["name"], "hours": p["hours"], "core": p["core"], "from": package_from(p, adapted)} for p in adapted["packages"]],
           "hours": adapted["hours"], "before": before,
           "tiers": adapt_tiers(adapted, judged),
           "filled": fill_evidence(case, adapted, fills, cov),
           "rows": final_rows(case, adapted, judged, fill_evidence(case, adapted, fills, cov), cov, body),
           "jobs": [{"id": p["id"], "name": p["name"], "hours": p["hours"], "core": p["core"], "out": p.get("out", ""), "from": package_from(p, adapted)}
                    for p in sorted(adapted["packages"], key=lambda p: p["order"])],
           # 끝까지 프로젝트로 다 못 배우는 역량: 교육자료에서 익힌다 (③ 교육자료 단계)
           "uncovered": [{"name": c["name"], "badges": badges[c["id"]], "level": c["expect"]} for c in left]}
    yield {"type": "stage", "key": merge["key"], "label": merge["label"]}
    short = {n: c["short"] for n, c in enumerate(adapted["complements"], 1)} | {"base": BASE, "new": AI_ADDED}
    got = before
    tier = {c["cid"]: tier_of(c) for c in cov}
    per = {t["name"]: t["before"] for t in adapt_tiers(adapted, judged)}      # 필수·우대 묶음마다 셈 (③ 큰 숫자)
    for x in fills:
        got += WORTH[x["level"]] - WORTH[x["was"]]
        t_ = tier[x["cid"]]
        if t_ in per:
            per[t_] += WORTH[x["level"]] - WORTH[x["was"]]
        yield {"type": "fill", "id": x["cid"], "level": x["level"], "by": x["by"], "count": got, "label": f"{x['package']} · {short[x['by']]}",
               "tier": t_, "tier_count": per.get(t_)}
        time.sleep(PACE["fill"] * speed)
    if left:      # 같은 사실은 단계마다 같은 말로: "프로젝트로 다 못 배우는 역량"
        yield {"type": "facts", "items": [{"text": f"프로젝트로 다 못 배우는 역량은 {names(c['name'] for c in left)} {len(left)}개예요. 교육자료에서 습득해요.",
                                           "badges": sorted({n for c in left for n in badges[c["id"]]})}]}
    yield {"type": "done", "levels": levels, "before": before, "after": after, "budgets": budgets if budgets is not None else LIVE_BUDGETS}


def project_offline(what="프로젝트 찾기"):
    """예시가 아닌 공고의 프로젝트 찾기(와 그 뒤 단계): 돈이 드는 검색은 하지 않고 쉬운 말로 알린다."""
    yield {"type": "notice", "text": f"{what}는 지금 예시 공고로만 보여 드릴 수 있어요."}


# ── 3단계: 교육자료, 4단계: 12주 계획 ─────────────────────────────────
# 저장본 둘은 design/build_data.py 가 만든다 (design/data_spec.md). 사람이 손으로 고른 결과라 걸린 시간이 없다.
# 화면에 내는 것은 쉬운 이름(short)·문장 번호·시간·자료의 제목·종류·사이트뿐이다 (L01·W3 같은 번호, hours_how·note 는 내지 않는다)
def materials_case(name):
    return saved(name, "materials")


def weeks_case(name):
    return saved(name, "weeks")


def report_case(name):
    return saved(name, "report")


def hm(hours):
    """시간을 소리 내 읽히게: 3 → '3시간', 1.3 → '1시간 18분', 0.72 → '43분'."""
    minutes = round(hours * 60)
    h, m = divmod(minutes, 60)
    return " ".join(x for x in (f"{h}시간" if h else "", f"{m}분" if m or not h else "") if x)




def budget_keys(name):
    """공부 시간 안의 열쇠 ("84"·"168"·"252"). 저장본의 budgets 에서 읽는다 (화면도 서버가 보낸 목록만 쓴다)."""
    return list(materials_case(name)["budgets"])


def budget_list(name):
    """2단계 끝에 싣는 안 목록. 이 예시의 4단계 저장본이 아직 없으면 빈 목록 (그때 12주 계획은 pending 이 막는다)."""
    mats = materials_case(name)
    return [{"key": k, "hours": b["hours"], "per_day": b["per_day"]} for k, b in mats["budgets"].items()] if mats else []


def budget_of(key, name):
    """요청의 budget 값을 열쇠로: 없으면 "84", 정수·문자열 숫자는 저장본 열쇠에 있을 때만. 아니면 None."""
    if key is None:
        key = "84"
    if isinstance(key, bool) or not isinstance(key, (str, int)):
        return None
    key = str(key)
    return key if key in materials_case(name)["budgets"] else None


def tagged(fn):
    """사건마다 budget_key 를 단다 (화면이 늦게 온 옛 안의 응답을 버릴 수 있게)."""
    def run(case, speed=1.0, budget="84", **kw):
        for ev in fn(case, speed, budget, **kw):
            yield {**ev, "budget_key": budget}
    run.__name__, run.__doc__ = fn.__name__, fn.__doc__
    return run


def names(xs):
    return ", ".join(xs)


LEVEL_TEXT = {"있음": "다룸", "일부": "일부만", "없음": "자료 없음"}      # ② 와 같은 말


def m3_case(name):      # m3_materials/pick.py 결과에서 화면 값만 옮긴 것 (design/build_m3.py)
    return saved(name, "m3")


def m3_steps(data):
    n, pool = len(data["targets"]), data["candidates"]
    core = sum(p["role"] == "핵심" for p in data["picks"])
    return [{"key": "targets", "label": "도구·지식 역량을 고르는 중", "done": f"도구·지식 역량 {n}개를 골랐어요"},
            {"key": "search", "label": "역량마다 교육자료 후보를 찾는 중", "done": f"교육자료 후보 {pool}개를 찾았어요"},
            {"key": "judge", "label": "후보마다 어느 역량을 가르치는지 보는 중", "done": f"후보 {pool}개가 가르치는 역량을 봤어요"},
            {"key": "pick", "label": "핵심 자료와 보조 자료를 고르는 중", "done": f"핵심 {core}개, 보조 {len(data['picks']) - core}개를 골랐어요"}]


LEVELS_ORDER = {"없음": 0, "일부": 1, "있음": 2}


def best(a, b):
    return a if LEVELS_ORDER[a] >= LEVELS_ORDER[b] else b


def materials(case, speed=1.0, data=None, live=False):
    """3단계: m3_materials/pick.py 가 고른 교육자료(핵심 1~2개, 보조 3~4개)를 다시 튼다.
    target 은 대상 역량 하나(level 은 처음엔 없음), pick 은 고른 자료 하나와 그때까지 역량마다 덮인 정도(levels).
    끝(done)의 levels 는 저장본의 coverage 와 같다. 시간은 쓰지 않는다 (공부 시간은 ④ 에서 고른다)."""
    data = data or m3_case(case["case"])
    steps = m3_steps(data)
    names_ = {t["cid"]: t["name"] for t in data["targets"]}
    tiers_ = {t["cid"]: t["priority"] for t in data["targets"]}
    r = data["rules"]      # 숫자 흐름 (발표 27쪽과 같다): 은행 → BM25 → Cohere Rerank → AI 판정으로 고른 자료
    funnel = [{"n": r["bank_rows"], "label": "교육자료 은행"}, {"n": r["wide"], "label": "BM25"},
              {"n": r["shortlist"], "label": "Cohere Rerank"}, {"n": len(data["picks"]), "label": "AI 판정"}] if "bank_rows" in r else []
    if not live:      # 새 공고는 live.py 가 단계를 실제 때에 낸다
        yield {"type": "steps", "items": steps, "funnel": funnel}
    levels = {t["cid"]: "없음" for t in data["targets"]}
    for s in steps:
        if not live:
            yield {"type": "stage", "key": s["key"], "label": s["label"]}
        if s["key"] == "targets":
            for t in data["targets"]:
                yield {"type": "target", "row": {"cid": t["cid"], "name": t["name"], "type": t["type"], "priority": t["priority"]}}
                time.sleep(PACE["cover"] * speed)
        elif s["key"] == "pick":
            for i, p in enumerate(data["picks"], 1):
                for c in p["covers"]:
                    levels[c["cid"]] = best(levels[c["cid"]], c["level"])
                yield {"type": "pick", "row": {"n": i, "role": p["role"], "title": p["title"], "kind": p["type"], "url": web(p["url"]),
                                               "covers": [{"cid": c["cid"], "name": names_[c["cid"]], "level": c["level"], "text": LEVEL_TEXT[c["level"]],
                                                           "tier": tiers_[c["cid"]], "posting": said(case, c["cid"]), "quote": c.get("quote", ""),
                                                           "posting_ko": ko(said(case, c["cid"])), "quote_ko": ko(c.get("quote", "")),
                                                           "shot": proof_shot(p["url"], c.get("quote", ""))} for c in p["covers"]]},
                       "levels": {k: {"level": v, "text": LEVEL_TEXT[v]} for k, v in levels.items()}}
                time.sleep(PACE["item"] * 2 * speed)
        else:
            time.sleep(PACE["stage"] * speed)
    r = data["rules"]
    left = [t["name"] for t in data["targets"] if levels[t["cid"]] == "없음"]
    covered = len(data["targets"]) - len(left)
    part = sum(levels[t["cid"]] == "일부" for t in data["targets"])
    yield {"type": "done", "n": len(data["picks"]), "targets": len(data["targets"]), "covered": covered, "missing": left,
           "levels": {k: {"level": v, "text": LEVEL_TEXT[v]} for k, v in levels.items()},
           "line": f"도구·지식 역량 {len(data['targets'])}개 중 {covered - part / 2:g}개를 자료로 배워요"
                   + (f" (일부만 다루는 {part}개는 0.5로 세요)" if part else ""),
           "rule": f"필수 역량은 {r['must']:,}점, 우대·나머지는 {r['other']}점으로 세어, 점수를 가장 많이 채우는 자료부터 핵심 {r['core'][0]}~{r['core'][1]}개, "
                   f"보조 {r['support'][0]}~{r['support'][1]}개를 골랐어요",
           "left": f"{names(left)} {len(left)}개는 맞는 자료를 찾지 못했어요" if left else ""}


def exam_weeks(data):
    """시험 주 (학기 주차 7·8·15·16). 저장본 team.exams 에서만 읽는다"""
    return [k for e in data["team"]["exams"] for k in e["weeks"]]


def full_id(case, x):
    """생성기 역량 표시('C14', '입문-C14') → 이 공고의 역량 id. 새 공고는 'P57eea47158-C14' 꼴이라 끝 번호로 잇는다"""
    tail = x.split("-")[-1]
    return next((c["id"] for c in case["competencies"] if c["id"].split("-")[-1] == tail), tail)


def skill_names(case, ids):
    """생성기의 역량 표시('C44', '입문-C21') → 이름 ('입문-' 은 '기초'). 한 번씩"""
    names = {full_id(case, c["id"]): c["name"] for c in case["competencies"]}
    out = []
    for x in ids:
        cid = full_id(case, x)
        if cid in names:
            out.append(names[cid] + (" 기초" if x.startswith("입문-") else ""))
    return list(dict.fromkeys(out))


def skill_ids(case, ids):
    """생성기의 역량 표시 → [{cid, basic}] (한 번씩). basic 은 '입문-' (그 역량의 기초)"""
    known = {c["id"] for c in case["competencies"]}
    out = {}
    for x in ids:
        cid = full_id(case, x)
        if cid in known:
            out[cid] = out.get(cid, True) and x.startswith("입문-")
    return [{"cid": k, "basic": v} for k, v in out.items()]


def comp_refs(case, cids):
    """역량마다 화면 카드에 띄울 것: 이름, 필수·우대, 유형, 근거가 된 공고 원문 문장(최대 둘, 부분 이름과 한국어 옮김)"""
    by = {c["id"]: c for c in case["competencies"]}
    sents = {s["id"]: s for s in case["sentences"]}
    out = {}
    for cid in cids:
        c = by.get(cid)
        if c:
            said_ = [{"section": sents[x]["section"], "text": sents[x]["text"], "ko": ko(sents[x]["text"])} for x in evidence_ids(c) if x in sents]
            out[cid] = {"name": c["name"], "tier": tier_of(c), "type": c.get("type", ""), "said": said_[:2]}
    return out


def curriculum_case(name, hours):
    """라운드랩 커리큘럼 생성기 결과 (design/build_curriculum.py → data/<예시>.curriculum.<주당 시간>.json). 없으면 None"""
    f = DATA / f"{name}.curriculum.{hours}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


SIZES = ("소", "중", "대")      # 주차 계획 크기 (사용자 11/21). 기본은 중 (한 주 14시간), 대 = 한 주 28시간. 소·52시간 안은 아직 없다


def plans_case(name):
    """응용 프로젝트 작업(W1~W10)과 교육자료를 주마다 배치한 계획 md 를 옮긴 것들 (design/build_curriculum_md.py → data/<예시>.plan.<상한>.json).
    한 주 상한이 작은 차례. 없으면 [] (그때는 생성기 결과를 쓴다)"""
    return sorted((_read(f) for f in DATA.glob(f"{name}.plan.*.json")), key=lambda d: d["constraints"]["hours_per_week"])


def blocked_case(name):
    """배정을 보류한 계획 md (data/<예시>.blocked.<한 주 시간>.json): 그 시간으로는 짜지 않고 주당 최소 시간을 알린다. 한 주 시간이 작은 차례"""
    return sorted((_read(f) for f in DATA.glob(f"{name}.blocked.*.json")), key=lambda d: d["hours_per_week"])


DEFAULT_WEEK_HOURS = 14      # 계획이 여럿인 예시의 처음 보이는 계획 (사용자 11/21: 기본 14시간)


def scale_line(views, blocks):
    """한 주 공부 시간에 따라 분량이 맞춰진다는 한 줄 (사용자 11/21). 숫자는 모두 계획 파일 값:
    '한 주 공부 시간은 정수로 정한다. 14시간이면 W9·W10을 미루고, 15시간이면 W10만 미루고, 28시간이면 모두 들어간다. 7시간이면 …'"""
    parts = [f"{v['cap']:g}시간이면 " + ("·".join(h["id"] for h in v["held"]) + ("만" if len(v["held"]) == 1 else "을") + " 미루고" if v["held"] else "모두 들어가고")
             for v in views]
    line = "한 주 공부 시간은 정수로 정한다. " + re.sub(r"(미루|들어가)고$", lambda m: {"미루": "미룬다", "들어가": "들어간다"}[m.group(1)], ", ".join(parts)) + "."
    for b in blocks:
        line += (f" {b['hours_per_week']}시간이면 12주 {b['available_minutes'] // 60}시간으로 필요한 {b['needed_minutes'] // 60}시간에 못 미쳐 계획을 보류하고, "
                 f"한 주 최소 {span_text(b['min_per_week_minutes'])}이 필요하다고 알려 준다.")
    return line


def span_text(m):
    """분 → '11시간 40분'"""
    h, mm = divmod(int(m), 60)
    return " ".join(x for x in (f"{h}시간" if h else "", f"{mm}분" if mm else "") if x)


def plan_view(case, d, hours, source):
    """계획 하나 → 화면 값: 주마다 활동(배우기·만들기), 합, 보류 작업, 바닥 줄 숫자(summary)"""
    s = d["summary"]
    plan_ = [{"week": w["week"], "learning": w["learning_minutes"] / 60, "project": w["implementation_minutes"] / 60, "cap": w["capacity_minutes"] / 60,
              "goal": w.get("goal", ""), "method": w.get("method", ""), "goal_steps": w.get("goal_steps", []), "method_steps": w.get("method_steps", []),
              "activities": [{"id": x["id"], "done": x.get("completed_in_this_chunk", True), "kind": x["kind"], "title": re.sub(r"\s*\(준비:.*\)$", "", x["title"]), "hours": x["hours"], "out": x.get("out", ""), "role": x.get("role", ""),
                              "url": web(x.get("url", "")), "skills": skill_names(case, x.get("competencies", [])), "ends": x.get("ends_week"),
                              "cids": skill_ids(case, x.get("competencies", [])), "check": x.get("completion_check", "")} for x in w["activities"]],
              "deliverables": w["deliverables_completed"]} for w in d["weeks"]]
    summary = {"weeks": len(d["weeks"]), "cap": hours, "inside_weeks": sum(w["used_minutes"] <= w["capacity_minutes"] for w in d["weeks"]),
               "learning": s["learning_hours"], "project": s["implementation_hours"], "deliverables": sum(len(w["deliverables_completed"]) for w in d["weeks"]),
               "source": source}
    return {"key": f"{hours:g}", "label": f"주 {hours:g}시간", "source": source,
            "plan": plan_, "cap": hours, "learning": s["learning_hours"], "project": s["implementation_hours"],
            "total": s.get("scheduled_hours", s["learning_hours"] + s["implementation_hours"]),
            "assigned": d.get("assigned", []), "held": d.get("held", []), "summary": summary}


@tagged
def weeks(case, speed=1.0, budget="84", curriculum=None):
    """⑤ 12주 계획. 예시 공고에 주차 계획 md(plans_case)가 있으면 그것들을 보인다: 화면이 한 주 공부 시간(주 14·15·28시간)을 고르고, 기본은 14.
    그 예시는 ④ 쪽에서 하루 1·2·3시간 칸을 숨기고 그 선택과 상관없다 (그 선택은 ⑥ 리포트가 쓴다). 보류 md(blocked_case)는 분량 한 줄(scale)에만.
    없거나 새 공고면 라운드랩 커리큘럼 생성기(github.com/gaori2952/Round_labcurriculum) 결과: 하루 1·2·3시간 = 주당 7·14·21시간 (한 사람).
    주마다 교육자료 공부 → 프로젝트 작업 → 산출물. 12주를 사건 하나로 보내 화면이 한 번에 그린다."""
    name_ = case["case"]
    mds = [] if curriculum is not None else plans_case(name_)
    if mds:
        views = [plan_view(case, d, d["constraints"]["hours_per_week"], "md") for d in mds]
        first = next((v for v in views if v["cap"] == DEFAULT_WEEK_HOURS), views[0])
        status, generator, scale = mds[0]["status"], "", scale_line(views, blocked_case(name_))
    else:
        per_day = {b["key"]: b["per_day"] for b in LIVE_BUDGETS}[budget] if curriculum is not None else materials_case(name_)["budgets"][budget]["per_day"]
        hours = 7 * per_day
        d = curriculum if curriculum is not None else curriculum_case(name_, hours)
        if not d:
            yield {"type": "notice", "text": "이 공고의 12주 계획은 아직 준비 중이에요."}
            return
        views = [plan_view(case, d, hours, "generator")]
        first, status, generator, scale = views[0], d["status"], d.get("generator_commit", ""), ""
    learning_n = sum(a["kind"] == "learning" for w in first["plan"] for a in w["activities"])
    steps = [{"key": "order", "label": (f"응용 프로젝트 작업 {len(first['assigned'])}개와 교육자료 {learning_n}개의 순서를 정하는 중" if mds
                                       else "교육자료와 프로젝트 작업의 순서(선수 관계)를 정하는 중"), "done": "순서를 정했어요"},
             {"key": "place", "label": f"한 주 {first['cap']:g}시간 안에 12주로 나누는 중", "done": "12주로 나눴어요"},
             {"key": "check", "label": "주마다 시간 한도와 산출물을 확인하는 중", "done": "한도와 산출물을 확인했어요"}]
    cids = list(dict.fromkeys(r["cid"] for v in views for w in v["plan"] for a in w["activities"] for r in a["cids"]))
    yield {"type": "steps", "items": steps, **{k: v for k, v in first.items() if k != "summary"},
           "plans": views if len(views) > 1 else [], "default": first["key"], "scale": scale, "generator": generator, "comps": comp_refs(case, cids)}
    for st in steps:
        yield {"type": "stage", "key": st["key"], "label": st["label"]}
        time.sleep(PACE["stage"] * speed)
    yield {"type": "done", **first["summary"], "status": status}


# ── 5단계: 정리 리포트 ──────────────────────────────────────────────
# 핵심 문장 하나에 한 줄: 문장 → 역량 → 어디서(프로젝트 일·교육자료)와 주 → 해 본 일 → 면접 질문 → 말로 하는 짧은 답.
# 질문은 공개 면접 질문 은행에 있는 질문이거나 AI가 만든 질문이다 (저장본의 origin). 답의 숫자는 예시 숫자다 (실제로 잰 값이 아니다).
# 줄 목록은 ⑥ 쪽에만 그린다 (대화 칸은 맨 위 한 줄, 짧은 줄, `리포트 보기` 단추)
def weeks_text(w, exams):
    """학기 주차 범위를 글로. 시험 주는 일하는 주처럼 쓰지 않는다: 6~11주차 → "6주차, 9~11주차".
    시험 주(exams, 저장본 team.exams)만 덮는 범위는 글이 비므로 저장본이 틀린 것이다: 멈춘다."""
    work = [k for k in range(w["from"], w["to"] + 1) if k not in exams]
    if not work:
        raise ValueError(f"{w['from']}~{w['to']}주차는 시험 주뿐이라 일하는 주가 없다")
    runs = []
    for k in work:
        if runs and runs[-1][1] == k - 1:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    return ", ".join(f"{a}주차" if a == b else f"{a}~{b}주차" for a, b in runs)


def mark_numbers(points, values):
    """답 점들을 조각으로 나눈다: 예시 숫자 값(values)마다 그 글자가 처음 나오는 곳을 {text, example: true} 로.
    값은 답 글에 글자 그대로 있어야 하고, 둘이 겹치면 안 된다 (저장본을 만들 때 검사한다)."""
    spans = {i: [] for i in range(len(points))}
    for v in values:
        hit = next(((i, at) for i, p in enumerate(points) for at in [p.find(v)] if at >= 0), None)
        if hit is None:
            raise ValueError(f"예시 숫자 '{v}' 가 답에 없다")
        i, at = hit
        if any(a < at + len(v) and at < b for a, b in spans[i]):
            raise ValueError(f"예시 숫자 '{v}' 가 다른 값과 겹친다")
        spans[i].append((at, at + len(v)))
    out = []
    for i, p in enumerate(points):
        parts, pos = [], 0
        for a, b in sorted(spans[i]):
            if a > pos:
                parts.append({"text": p[pos:a]})
            parts.append({"text": p[a:b], "example": True})
            pos = b
        if pos < len(p):
            parts.append({"text": p[pos:]})
        out.append(parts)
    return out


def report_steps(data):
    c = data["counts"]
    return [{"key": "pick", "label": f"핵심 문장 {c['rows']}개에서 면접 질문을 고르는 중", "done": "면접 질문을 골랐어요"},
            {"key": "answer", "label": "질문마다 프로젝트 일로 답 요점을 짜는 중", "done": "답 요점을 짰어요"},
            {"key": "typeset", "label": "발표 슬라이드로 짜는 중", "done": "슬라이드로 짰어요"}]


def report_page(name, budget):
    """발표 자료 모양의 면접 대비 슬라이드 (design/build_report_deck.py 가 만든 data/<예시>.report.<시간>.<쪽>.png·.pptx·.json). 없으면 None"""
    facts_, pptx = DATA / f"{name}.report.{budget}.json", DATA / f"{name}.report.{budget}.pptx"
    if not facts_.is_file() or not pptx.is_file():
        return None
    facts = json.loads(facts_.read_text("utf-8"))
    slides = [f"/report/{name}.{budget}.{k}.png" for k in range(1, facts["slides"] + 1)]
    if not all((DATA / f"{name}.report.{budget}.{k}.png").is_file() for k in range(1, facts["slides"] + 1)):
        return None
    return {**facts, "slides": slides, "pptx": f"/report/{name}.{budget}.pptx", "filename": f"면접대비리포트_{name}_{budget}시간.pptx"}      # facts 의 쪽 수(slides)를 쪽 주소 목록이 덮는다


@tagged
def report(case, speed=1.0, budget="84"):
    """정리 리포트: 사람이 미리 짠 면접 대비 슬라이드를 고른 공부 시간 안으로 보인다. 바닥 줄 불렛 둘은 그 쪽에 적힌 값만."""
    name_ = case["case"]
    data, page = report_case(name_), report_page(name_, budget)
    if not page:
        yield {"type": "notice", "text": "이 공고의 정리 리포트는 아직 준비 중이에요."}
        return
    steps = report_steps(data)
    yield {"type": "steps", "items": steps, "per_day": materials_case(name_)["budgets"][budget]["per_day"]}
    for s in steps:
        yield {"type": "stage", "key": s["key"], "label": s["label"]}
        time.sleep(PACE["stage"] * speed)
    companies = page["companies"]
    yield {"type": "done", "slides": page["slides"], "pptx": page["pptx"], "filename": page["filename"],
           "bullets": [f"공고 핵심 문장 {data['counts']['rows']}개에서 고른 면접 질문 {page['questions']}개 · 공개 면접 질문 은행 {page['bank']}개",
                       f"질문 출처 {', '.join(companies)}" if companies else "모두 직접 만든 질문"]}
