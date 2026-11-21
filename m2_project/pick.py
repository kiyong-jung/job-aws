"""② 고르기: 후보 목록 → 가장 좋은 샘플 하나와 역량별 덮기 표.

LLM 은 후보마다 역량별로 있음·일부·없음과 후보 글에서 베낀 근거 구절만 낸다 (5개씩 묶어 부름).
보여 주는 글: 논문 = 초록 전체 (2026-11-18 RQ4f 뒤 900자에서 바꿈), 저장소 = 이름·설명·주제어 + 정리한 README 앞 4,000자 (readme.py).
구절이 보여 준 글에 없으면 코드가 그 칸을 한 단계 내린다. 구절을 '…' 로 줄였으면 조각(3낱말 이상)이 차례대로 모두 있어야 한다.
순위는 코드가 단계별로 정한다: ① 필수 역량을 많이 덮는 후보 → 같으면 ② 우대 역량 → 같으면 ③ 나머지 역량.
앞 단계가 반 개라도 많으면 뒤 단계 점수와 상관없이 이긴다 (2026-11-18 사용자 규칙: 필수 하나가 우대 전부보다 크다).
덮는 정도 = 있음 1 + 일부 0.5 의 합. 필수·우대는 1단계 역량 표의 표시(priority)다.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from shared import llm
from shared.llm import STR, arr, obj

from . import readme
from .search import MODEL, PROMPT, posting_text, section_of

LEVELS = ("없음", "일부", "있음")
VALUE = {"없음": 0, "일부": 0.5, "있음": 1}
TIERS = ("필수", "우대", "나머지")   # 역량의 priority 로 가른 단계. 필수·우대가 아니면 나머지


def tier_of(c):
    return c["priority"] if c["priority"] in TIERS[:2] else TIERS[2]
BATCH = 5
CELL_TOKENS = 50   # 판정 칸 하나의 출력 토큰 상한 어림. 네이버(역량 29)는 칸마다 평균 약 20토큰을 썼다
WORKERS = 8   # 묶음을 동시에 몇 개 부르나
SHOWN = ("key", "kind", "url", "year", "venue", "stars")   # 순위 표에 같이 싣는 후보 칸
CUT = 900   # 저장소 설명은 앞 900자. 논문 초록은 자르지 않는다 (RQ4f: 900자와 전체가 사실상 같고 자를 근거가 없음)

JUDGE_SYSTEM = (PROMPT / "judge.txt").read_text("utf-8")
JUDGE_SCHEMA = obj({"items": arr(obj({"n": {"type": "integer"},
                                       "coverage": arr(obj({"cid": STR, "level": {"type": "string", "enum": list(LEVELS)},
                                                            "quote": STR}))}))})


def _norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[\.\.\.\])\s*")


def quote_ok(quote, text, min_words=3):
    """구절이 글에 그대로 있거나, '…' 로 나뉜 조각이 둘 이상이고 조각마다 3낱말 이상이며 글에 차례대로 모두 있으면 참."""
    q = _norm(quote)
    if not q:
        return False
    tn = " " + _norm(text) + " "
    if q in tn:
        return True
    segs = [x for x in (_norm(s) for s in _ELLIPSIS.split(quote)) if x]
    if len(segs) < 2 or any(len(x.split()) < min_words for x in segs):
        return False
    at = 0
    for x in segs:
        i = tn.find(" " + x + " ", at)
        if i < 0:
            return False
        at = i + len(x) + 1
    return True


def settle(level, quote, text):
    """칸 하나 → (등급, 내렸는가). 근거 구절이 보여 준 글에서 확인되지 않으면 한 단계 내린다."""
    if level != "없음" and not quote_ok(quote, text):
        return LEVELS[LEVELS.index(level) - 1], True
    return level, False


def shown(c):
    """후보 → 판정기에게 보여 줄 글. 저장소면 README 를 붙인다 (받아 둔 것이 있을 때)."""
    text = c["text"] if c["kind"] == "paper" else c["text"][:CUT]
    if c["kind"] == "repo" and c.get("key", "").startswith("gh:"):
        r = readme.text(c["key"])
        if r:
            text += "\n\nREADME:\n" + r
    return text


def judge(case, candidates):
    """후보 목록 → 후보마다 {cid: {level, quote, downgraded}}. 5개씩 묶어 LLM 에 묻는다 (WORKERS 개 묶음을 동시에)."""
    cids = {c["id"] for c in case["competencies"]}
    out = [{} for _ in candidates]
    readme.fetch_missing([c["key"] for c in candidates if c["kind"] == "repo" and "key" in c])
    texts = [shown(c) for c in candidates]
    limit = max(8000, CELL_TOKENS * BATCH * len(cids))   # 역량이 많은 공고(AWS 58개)는 묶음 답이 8000토큰을 넘을 수 있다

    def ask(start):
        part = candidates[start:start + BATCH]
        body = "\n".join(f'<candidate n="{start + i}" title="{c["title"]}"><text>{texts[start + i - 1]}</text></candidate>'
                         for i, c in enumerate(part, 1))
        return start, part, llm.ask_json(posting_text(case) + "\n" + body, JUDGE_SYSTEM, JUDGE_SCHEMA, model=MODEL, max_tokens=limit)

    with ThreadPoolExecutor(WORKERS) as pool:
        answers = list(pool.map(ask, range(0, len(candidates), BATCH)))
    for start, part, got in answers:
        for item in got["items"]:
            if not start < item["n"] <= start + len(part):
                continue
            text = texts[item["n"] - 1]
            for cell in item["coverage"]:
                if cell["cid"] in cids:
                    level, down = settle(cell["level"], cell["quote"], text)
                    out[item["n"] - 1][cell["cid"]] = {"level": level, "quote": cell["quote"] if level != "없음" else "",
                                                       "downgraded": down}
    return out


def tier_scores(cells, case):
    """한 후보의 칸들 → 단계별 덮는 정도 (단계 1, 단계 2, 단계 3)."""
    return tuple(sum(VALUE[cells.get(c["id"], {}).get("level", "없음")] for c in case["competencies"]
                     if tier_of(c) == tier) for tier in TIERS)


def pick_best(case, candidates):
    """case, 후보 목록 → {sample, runner_up, ranking, coverage, cells, order}. 순위는 tier_scores 를 앞 단계부터 견준다.
    cells 는 후보 전부의 칸(후보 차례), order 는 순위 차례의 후보 번호다. 응용 단계(adapt.py)가 보완을 고를 때 쓴다 (이미 낸 판정이라 돈이 들지 않는다).
    필수는 샘플이 모두 '있음'으로 덮어야 한다 (11/18 사용자 규칙). 그런 후보가 있으면 필수 점수가 가장 높아 순위 첫째가 된다.
    없으면 그래도 1등을 내되 must_all 을 거짓으로, 빠진 필수 이름을 must_missing 에 적는다."""
    cells = judge(case, candidates)
    order = sorted(range(len(candidates)), key=lambda i: tier_scores(cells[i], case), reverse=True)
    names = {c["id"]: (c["name"], section_of(c, case), tier_of(c)) for c in case["competencies"]}
    best = order[0]
    missing = [c["name"] for c in case["competencies"]
               if tier_of(c) == TIERS[0] and cells[best].get(c["id"], {}).get("level") != "있음"]
    return {"sample": candidates[best], "must_all": not missing, "must_missing": missing,
            "runner_up": [candidates[i] for i in order[1:3]],
            "ranking": [{"title": candidates[i]["title"], **{k: candidates[i][k] for k in SHOWN if k in candidates[i]},
                         **dict(zip(TIERS, tier_scores(cells[i], case)))} for i in order],
            "coverage": [{"cid": cid, "name": names[cid][0], "section": names[cid][1], "priority": names[cid][2], **cell}
                         for cid, cell in sorted(cells[best].items())],
            "cells": cells, "order": order}
