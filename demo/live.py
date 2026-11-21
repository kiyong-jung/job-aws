"""새 공고 라이브 (사용자 11/21: 어떤 공고든 Vercel 에서 끝까지). 예시 공고는 pipeline.py 가 저장본을 다시 튼다.
서버는 상태를 두지 않는다: 단계마다 화면이 앞 단계 결과(state = {case, project, adapt, materials})를 보내고,
요청 하나는 Vercel 무료 한도(300초) 안에 끝나게 ②를 '찾기·판정'(project)과 '응용'(adapt) 두 요청으로 나눈다.
사건 꼴은 저장본을 다시 틀 때와 같다 (화면 코드 하나). 결과는 live_state 사건으로 화면에 넘겨 다음 단계 요청에 실린다.
모델 호출: m2 검색어·판정·응용, m3 검색어·판정 (Bedrock, 공고 한 건에 4,000~5,000원 어림). m4 생성기와 리포트는 모델 없음."""
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from demo import pipeline as P

HERE = Path(__file__).resolve().parent
GENERATOR = Path(os.environ.get("GENERATOR_DIR") or HERE.parent / "m4_weekly" / "generator")      # 라운드랩 커리큘럼 생성기 (m4)
WORKERS = 8      # Cohere 다시 고르기를 동시에 몇 개


def _stage(steps, key):
    s = next(x for x in steps if x["key"] == key)
    return {"type": "stage", "key": key, "label": s["label"]}


def _state(key, value):
    return {"type": "live_state", "key": key, "value": value}


def _rerank_all(case, bank, pool, local):
    """역량마다 pool 을 Cohere 점수 차례로 (local.comp_lists 와 같은 규칙, 역량들을 동시에 묻는다)."""
    sent = {s["id"]: s["text"] for s in case["sentences"]}
    comps = local.ranked_comps(case)
    docs = [bank[i]["title"] + " " + bank[i]["text"] for i in pool]

    def one(c):
        q = c["name"] + " — " + sent.get(c["evidence_id"].split(",")[0].strip(), "")
        s = local.rerank(q, docs)
        return c["id"], [pool[k] for k in sorted(range(len(pool)), key=lambda k: -s[k])]
    with ThreadPoolExecutor(WORKERS) as ex:
        return dict(ex.map(one, comps))


def project(case):
    """② 찾기·판정 → 1위 (응용은 다음 요청)."""
    from m2_project import local, pick
    from demo import search_db
    t0 = time.time()
    if search_db.path():      # Vercel: SQLite 전문 검색 (메모리 가볍다)
        bank = search_db.Bank()
        n = bank.counts()
        def rank(q):
            return search_db.rank(bank, q)
    else:                     # 컴퓨터: BM25 피클 (m2 와 같은 검색)
        bank, index = local.load_bank()
        n = {"paper": len(index["paper"][1]), "repo": len(index["repo"][1])}
        def rank(q):
            return local.rank(index, q)
    counts = {"papers": n.get("paper", 0), "repos": n.get("repo", 0), "pool": local.POOL, "shortlist": local.SHORTLIST, "judged": local.SHORTLIST, "k": 1}
    steps = P.project_steps(counts) + P.ADAPT_STEPS
    must = sum(P.tier_of(c) == P.TIERS[0] for c in case["competencies"])
    yield {"type": "steps", "items": steps, "db": {"papers": counts["papers"], "repos": counts["repos"], "total": counts["papers"] + counts["repos"]},
           "pool": local.POOL, "shortlist": local.SHORTLIST, "seconds": None, "tier": {"name": P.TIERS[0], "total": must},
           "fit": {"label": f"{P.TIERS[0]}를 가장 많이 다룬 후보", "n": 1}, "adapted": True, "names": None}
    yield _stage(steps, "search")
    with ThreadPoolExecutor(2) as ex:      # 대표 이름 검색어와 역량별 검색어 (모델 두 번, 동시에)
        f1, f2 = ex.submit(local.cached_queries, case), ex.submit(local.comp_queries, case)
        names, per = f1.result(), f2.result()
    yield _stage(steps, "scan")
    first = rank({"paper": [q["paper"] for q in per.values()] + names["paper_names"],
                  "repo": [q["repo"] for q in per.values()] + names["repo_names"]})
    pool = sorted(first, key=lambda i: -first[i])[:local.POOL]
    yield _stage(steps, "rerank")
    score = local.fuse(_rerank_all(case, bank, pool, local))
    top = sorted(score, key=lambda i: -score[i])[:local.SHORTLIST]
    cands = [{**bank[i], "search_score": round(score[i], 3)} for i in top]
    yield _stage(steps, "judge")
    starts = range(0, len(cands), 10)      # 10개 묶음을 한꺼번에 (Vercel 300초 안에 들도록)
    cells, n = [None] * len(cands), 0
    with ThreadPoolExecutor(len(starts)) as ex:
        jobs = {ex.submit(pick.judge, case, cands[s:s + 10]): s for s in starts}
        for f in as_completed(jobs):
            s = jobs[f]
            cells[s:s + 10] = f.result()
            n += 10
            yield {"type": "judged", "n": min(n, len(cands)), "ranks": [], "scores": []}
    yield {**_stage(steps, "pick"), "top": 0, "order": list(range(len(cands))), "full": 0, "note": ""}
    out = pick.pick_best(case, cands, cells)
    cells, order = out.pop("cells"), out.pop("order")
    data = {"counts": {**counts, "judged": len(cands)}, "coverage": out["coverage"], "sample": out["sample"], "ranking": out["ranking"][:5],
            "scores": [r[P.TIERS[0]] for r in out["ranking"]], "seconds": round(time.time() - t0, 1)}
    slim = [{k: c[k] for k in ("key", "kind", "title", "year", "venue", "url", "text", "stars", "code_url") if k in c} for c in cands]
    yield _state("project", {"data": data, "ranking": out["ranking"], "candidates": slim, "cells": cells, "order": order})
    yield from P.project(case, speed=0, data=data, live=True)


def adapt(case, state):
    """② 응용: 1위에 빌린 부분과 AI가 더한 일을 더한 프로젝트 하나 (모델 한두 번)."""
    from m2_project import adapt as m2a
    from demo.design import build_adapt
    pr = state["project"]
    yield {"type": "stage", "key": P.ADAPT_STEPS[0]["key"], "label": P.ADAPT_STEPS[0]["label"]}
    raw = m2a.adapt(case, pr["candidates"], pr["cells"], pr["order"], deadline=time.time() + 270)      # Vercel 은 300초에 끊는다
    adapted = build_adapt.build({"adapted": raw, "ranking": pr["ranking"]})
    yield _state("adapt", {"raw": raw, "demo": adapted})
    yield from P.adapt_part(case, pr["data"], adapted, speed=0, budgets=P.LIVE_BUDGETS)


def materials(case):
    """③ 교육자료: m3_materials.pick.run 과 같은 차례를 한 걸음씩 (화면에 지금 하는 일을 보인다)."""
    from m3_materials import pick as m3
    from m2_project import local
    from shared import llm
    from demo.design import build_m3
    labels = [("targets", "도구·지식 역량을 고르는 중"), ("search", "역량마다 교육자료 후보를 찾는 중"),
              ("judge", "후보마다 어느 역량을 가르치는지 보는 중"), ("pick", "핵심 자료와 보조 자료를 고르는 중")]
    steps = [{"key": k, "label": v, "done": v.replace("는 중", "었어요")} for k, v in labels]
    funnel = [{"n": len(m3.bank()[0]), "label": "교육자료 은행"}, {"n": m3.WIDE, "label": "BM25"}, {"n": m3.SHORT, "label": "Cohere Rerank"},
              {"n": m3.CORE[1] + m3.SUPPORT[1], "label": "AI 판정"}]
    yield {"type": "steps", "items": steps, "funnel": funnel}
    yield _stage(steps, "targets")
    comps = m3.targets(case)
    before = llm.USAGE["usd"]
    qs = m3.queries(case, comps)
    yield _stage(steps, "search")
    mats, units = m3.candidates(case, comps, qs)
    yield _stage(steps, "judge")
    cells = m3.judge(case, comps, mats)
    yield _stage(steps, "pick")
    picked, have = m3.choose(comps, cells)
    out = {"case": case["case"],
           "rules": {"types": list(m3.TYPES), "weight": {"필수": m3.MUST_WEIGHT, "우대·나머지": m3.OTHER_WEIGHT}, "core": list(m3.CORE),
                     "support": list(m3.SUPPORT), "wide": m3.WIDE, "rerank": local.RERANKER, "shortlist": m3.SHORT, "bank_rows": len(m3.bank()[0])},
           "targets": [{"cid": c["id"], "name": c["name"], "type": c["type"], "priority": m3.tier_of(c), "query": qs[c["id"]]} for c in comps],
           "picks": [{"role": role, "gain": g, "id": mats[i]["id"], "title": mats[i]["title"], "type": mats[i]["type"], "url": mats[i]["url"],
                      "covers": {cid: x["level"] for cid, x in cells[i].items() if x["level"] != "없음"}} for i, role, g in picked],
           "coverage": [{"cid": c["id"], "name": c["name"], "priority": m3.tier_of(c),
                         "level": next(k for k, v in m3.VALUE.items() if v == have[c["id"]])} for c in comps],
           "candidates": [{"id": m["id"], "title": m["title"], "cells": cells[i]} for i, m in enumerate(mats)],
           "cost_krw": round((llm.USAGE["usd"] - before + units * m3.RERANK_USD) * llm.KRW_PER_USD, 1), "rerank_units": units}
    keep = {p["id"] for p in out["picks"]}      # 화면에 실어 보낼 것은 고른 자료의 칸만 (요청 크기)
    yield _state("materials", {**out, "candidates": [c for c in out["candidates"] if c["id"] in keep]})
    yield from P.materials(case, speed=0, data=build_m3.build(out), live=True)


def _curriculum(case, state, hours):
    from demo.design.make_team_csv import build as make_csv
    with tempfile.TemporaryDirectory() as tmp:
        team, out = Path(tmp) / "team", Path(tmp) / "out"
        make_csv(case["case"], team, local={"ranking": state["project"]["ranking"]}, adapt=state["adapt"]["raw"],
                 mat=state["materials"], comps=case["competencies"])
        r = subprocess.run([sys.executable, "-E", "-s", "curriculum_generator.py", "--hours-per-week", str(hours), "--team-folder", str(team),
                            "--output-dir", str(out)], cwd=GENERATOR, capture_output=True, text=True)
        if r.returncode not in (0, 3):      # 3 = needs_review (팀 CSV 로 만든 결과의 정상 상태)
            raise RuntimeError(f"12주 계획 생성기 실패 ({r.returncode}): {r.stderr[-300:]}")
        return json.loads((out / "curriculum.json").read_text(encoding="utf-8"))


def weeks(case, state, budget="84"):
    """④ 12주 계획: 라운드랩 커리큘럼 생성기 (모델 없음)."""
    per_day = {b["key"]: b["per_day"] for b in P.LIVE_BUDGETS}.get(str(budget), 1)
    d = _curriculum(case, state, 7 * per_day)
    yield from P.weeks(case, 0, str(budget), curriculum=d)


def report(case, state, budget="84"):
    """⑤ 정리 리포트 (새 공고): 필수·우대 역량마다 공고 문장 → 프로젝트에서 하는 일 → 교육자료 → 공개 면접 질문 은행의 가까운 질문.
    슬라이드 대신 쪽 안의 표 (모델 없음). 질문은 질문 은행의 낱말 검색 위 하나"""
    from shared import schema
    steps = [{"key": "pick", "label": "역량마다 면접 질문을 고르는 중", "done": "면접 질문을 골랐어요"}]
    yield {"type": "steps", "items": steps, "per_day": {b["key"]: b["per_day"] for b in P.LIVE_BUDGETS}.get(str(budget), 1), "budget_key": str(budget)}
    yield {"type": "stage", "key": "pick", "label": steps[0]["label"], "budget_key": str(budget)}
    adapted = state["adapt"]["demo"]
    jobs = {p["id"]: p["name"] for p in adapted["packages"]}
    where = {c["id"]: [jobs[k] for k in c["packages"] if k in jobs] for c in adapted["coverage"]}
    mats = {}
    for p in state["materials"]["picks"]:
        for cid in p["covers"]:
            mats.setdefault(cid, p["title"])
    qi = schema.index("questions")
    rows = []
    for c in case["competencies"]:
        tier = P.tier_of(c)
        if tier not in P.TIERS[:2]:
            continue
        said = P.said(case, c["id"])
        hit = qi.search(f'{c["name"]} {said}', k=1)
        rows.append({"tier": tier, "name": c["name"], "posting": said, "posting_ko": P.ko(said), "job": ", ".join(where.get(c["id"], [])) or "교육자료에서 배움",
                     "material": mats.get(c["id"], ""), "question": hit[0]["text"] if hit else "", "asked": ", ".join(hit[0].get("asked_at") or []) if hit else ""})
    yield {"type": "done", "rows": rows, "slides": [], "bullets": [f"필수·우대 역량 {len(rows)}개마다 면접 질문 하나", "질문은 공개 면접 질문 은행에서 낱말이 가장 가까운 것"],
           "budget_key": str(budget)}
