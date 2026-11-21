"""① 찾기 (로컬): 공고 → 샘플 후보 목록. 웹 대신 로컬 DB 에서 찾는다.

DB = 논문 서고 data/papers/ (초록 있는 것만) + GitHub 저장소 목록 data/github_repos/ (별 200 이상).
1. 검색어: LLM 이 역량마다 논문 검색어 하나·저장소 검색어 하나를 낸다 (comp_queries). 대표 논문·저장소 이름은
   search.ask_queries 의 저장본(<공고>.search.json)에서 가져온다.
2. 넓게 모으기: 논문 검색어는 논문에서, 저장소 검색어는 저장소에서 BM25 로 찾고, 검색어마다 1/(순위+1) 을 더해 위 1000.
3. 다시 고르기: 역량마다 그 1000 개를 Cohere Rerank 3.5 (Bedrock) 로 "역량 이름 — 근거 문장" 에 맞는 차례로 다시 세운다 (rerank).
4. 합치기: 역량별 목록의 위 100 을 같은 1/(순위+1) 합으로 모아 위 SHORTLIST 개를 판정에 넘긴다.
그다음 pick.pick_best 로 판정하고, 단계 1 을 넉넉히 덮는 후보를 '딱 맞는' 후보로 낸다 (fit).
마지막으로 adapt.adapt 가 1등을 보완 2~3개로 응용한 프로젝트 하나를 만든다 (adapted).
"""
import hashlib
import json
import math
import pickle
import re
import time

import numpy as np
from rank_bm25 import BM25Okapi

from shared import config, llm
from shared.llm import STR, arr, obj

from . import adapt, library, repos, search
from .pick import BATCH, TIERS, judge, pick_best, tier_of

INDEX = config.OUTPUTS / "project" / "local_bm25.pkl"
DEPTH = 100          # 검색어 하나(또는 역량 하나)에서 순위를 셀 위쪽 개수
POOL = 1000          # 다시 고르기 전에 넓게 모으는 개수
SHORTLIST = 100      # 판정에 넘기는 개수. 연구에서 위 100 만 판정해도 예전 방식 200 보다 역량을 더 찾았다
RANKED = {"담당업무", "자격요건", "우대사항"}   # 다시 고르기를 하는 역량의 구역 (연구 RQ2b 에서 잰 범위)
COMP_SYSTEM = (search.PROMPT / "query_comp.txt").read_text("utf-8")
RERANKER, RERANK_REGION = "cohere.rerank-v3-5:0", "us-west-2"
TRIAL = BATCH        # 비용을 재는 첫 묶음 크기
SPEND_CAP = 10_000   # 전부 판정할 때 어림 비용 한도 (원). 넘으면 위 FALLBACK 개만
FALLBACK = 40
STOP = set("""a an and are as at be been but by can do does for from has have how in into is it its of on or our
over such than that the their then there these they this to under up via was we were what when which while who
will with within without you your using use used based new also can may more most not only other both each between
through via towards toward""".split())


def tokens(text):
    """소문자 영숫자 낱말, 영어 불용어와 한 글자는 뺀다."""
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 1 and w not in STOP]


def read_rows(path):
    """jsonl 한 파일. 모으는 중이라 마지막 줄이 덜 써졌으면 건너뛴다."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def read_papers(files):
    """논문 조각 → 후보 (초록 있는 것만, 제목이 같으면 하나만)."""
    seen = {}
    for path in files:
        for r in read_rows(path):
            t = library.norm(r.get("title") or "")
            if not r.get("abstract") or not t or t in seen:
                continue
            key = f'arxiv:{r["arxiv"]}' if r.get("arxiv") else f'doi:{r["doi"]}' if r.get("doi") else f"url:{r['url']}"
            seen[t] = {"key": key, "kind": "paper", "title": r["title"], "year": str(r["year"]), "venue": r["venue"],
                       "url": r["url"], "text": r["abstract"], "code_url": r.get("code_url") or ""}
    return list(seen.values())


def read_repos(files):
    """저장소 조각 → 후보. 글 = 이름 + 설명 + 주제."""
    merged = {r["full_name"]: r for path in files for r in read_rows(path)}
    return [{"key": f"gh:{n.lower()}", "kind": "repo", "title": n, "year": (r.get("pushed_at") or "")[:4],
             "venue": f'GitHub ★{r["stars"]}', "url": r["url"], "stars": r["stars"],
             "text": " ".join([n.replace("/", " "), r.get("description") or "", " ".join(r.get("topics") or [])])}
            for n, r in merged.items()]


def build(bank):
    """후보 목록 → {kind: (BM25Okapi, 그 kind 후보의 bank 자리 목록)}."""
    index = {}
    for kind in ("paper", "repo"):
        at = [i for i, b in enumerate(bank) if b["kind"] == kind]
        if at:
            index[kind] = (BM25Okapi([tokens(bank[i]["title"] + " " + bank[i]["text"]) for i in at]), at)
    return index


def load_bank():
    """DB 전체 → (bank, index). 파일 이름·크기·수정 시각이 같으면 outputs/project/local_bm25.pkl 의 저장본을 쓴다."""
    paper_files, repo_files = library.all_shards(), repos.shard_files()
    stamp = hashlib.sha1(json.dumps([(str(p), p.stat().st_size, p.stat().st_mtime_ns)
                                     for p in paper_files + repo_files]).encode()).hexdigest()
    if INDEX.exists():
        saved = pickle.loads(INDEX.read_bytes())
        if saved["stamp"] == stamp:
            return saved["bank"], saved["index"]
    bank = read_papers(paper_files) + read_repos(repo_files)
    index = build(bank)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps({"stamp": stamp, "bank": bank, "index": index}, protocol=pickle.HIGHEST_PROTOCOL))
    tmp.replace(INDEX)
    return bank, index


def rank(index, queries):
    """{kind: [검색어]} → {bank 자리: 점수}. 점수 = 검색어마다 1/(순위+1) 의 합 (search.py 와 같다).
    BM25 값은 검색어 길이와 글 길이(초록 대 저장소 설명)에 따라 크기가 달라 그대로 더하면 긴 검색어가 이기므로 순위만 쓴다."""
    score = {}
    for kind, qs in queries.items():
        if kind not in index:
            continue
        bm25, at = index[kind]
        for q in qs:
            s = bm25.get_scores(tokens(q))
            top = np.argsort(-s, kind="stable")[:DEPTH]
            for r, i in enumerate(j for j in top if s[j] > 0):
                score[at[i]] = score.get(at[i], 0) + 1 / (r + 1)
    return score


def cached_queries(case):
    """저장해 둔 검색어(<공고>.search.json)가 있으면 그것, 없으면 search.ask_queries (LLM 한 번)."""
    path = config.OUTPUTS / "project" / f'{case["case"]}.search.json'
    got = json.loads(path.read_text("utf-8")) if path.exists() else search.ask_queries(case)
    return {k: got[k] for k in search.COUNTS}


def ranked_comps(case):
    return [c for c in case["competencies"] if search.section_of(c, case) in RANKED]


def comp_queries(case):
    """역량 id → {paper, repo} 영어 검색어. LLM 한 번, <공고>.comp_queries.json 에 두고 다시 쓴다.
    역량이 많으면 id 로 묶은 스키마가 BizRouter 에서 'grammar is too large' 로 막혀, 그때만 목록 스키마로 묻는다."""
    path = config.OUTPUTS / "project" / f'{case["case"]}.comp_queries.json'
    if path.exists():
        return json.loads(path.read_text("utf-8"))
    ids = [c["id"] for c in ranked_comps(case)]
    try:
        got = llm.ask_json(search.posting_text(case), COMP_SYSTEM, obj({i: obj({"paper": STR, "repo": STR}) for i in ids}),
                           model=search.MODEL, max_tokens=4000)
    except RuntimeError as e:
        if "grammar is too large" not in str(e):
            raise
        rows = llm.ask_json(search.posting_text(case), COMP_SYSTEM,
                            obj({"entries": arr(obj({"id": {"type": "string", "enum": ids}, "paper": STR, "repo": STR}))}),
                            model=search.MODEL, max_tokens=4000)["entries"]
        got = {r["id"]: r for r in rows}
    out = {i: {"paper": got[i]["paper"], "repo": got[i]["repo"]} for i in ids if i in got}
    if set(out) != set(ids) or any(not q["paper"].strip() or not q["repo"].strip() for q in out.values()):
        raise RuntimeError(f'{case["case"]}: 역량별 검색어가 빠졌다 {sorted(set(ids) - set(out))}')
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    return out


def rerank(query, docs):
    """Cohere Rerank 3.5 (Bedrock us-west-2, AWS_PROFILE) → 문서마다 점수 (docs 차례). 한 번에 1000개까지."""
    import boto3
    rt = boto3.Session(profile_name=config.get("AWS_PROFILE")).client("bedrock-agent-runtime", region_name=RERANK_REGION)
    r = rt.rerank(
        queries=[{"type": "TEXT", "textQuery": {"text": query}}],
        sources=[{"type": "INLINE", "inlineDocumentSource": {"type": "TEXT", "textDocument": {"text": d}}} for d in docs],
        rerankingConfiguration={"type": "BEDROCK_RERANKING_MODEL", "bedrockRerankingConfiguration": {
            "numberOfResults": len(docs),
            "modelConfiguration": {"modelArn": f"arn:aws:bedrock:{RERANK_REGION}::foundation-model/{RERANKER}"}}})
    score = [0.0] * len(docs)
    for x in r["results"]:
        score[x["index"]] = x["relevanceScore"]
    return score


def comp_lists(case, bank, pool):
    """역량마다 pool(bank 자리, 순위 합 차례)을 Cohere 점수 큰 차례로 다시 세운 목록. 점수는 <공고>.rerank.json 에 열쇠로 두고,
    없는 문서만 Bedrock 에 묻는다. 같은 점수면 순위 합 차례를 지킨다 (안정 정렬)."""
    path = config.OUTPUTS / "project" / f'{case["case"]}.rerank.json'
    saved = json.loads(path.read_text("utf-8")) if path.exists() else {}
    sent = {s["id"]: s["text"] for s in case["sentences"]}
    lists = {}
    for c in ranked_comps(case):
        have = saved.setdefault(c["id"], {})
        todo = [i for i in pool if bank[i]["key"] not in have]
        if todo:
            query = c["name"] + " — " + sent.get(c["evidence_id"].split(",")[0].strip(), "")
            got = rerank(query, [bank[i]["title"] + " " + bank[i]["text"] for i in todo])
            have.update({bank[i]["key"]: s for i, s in zip(todo, got)})
            path.write_text(json.dumps(saved, ensure_ascii=False), "utf-8")
        lists[c["id"]] = sorted(pool, key=lambda i: -have[bank[i]["key"]])
    return lists


def fuse(lists):
    """역량별 목록마다 위 DEPTH 개에 1/(순위+1) 을 더한 점수 → {bank 자리: 점수}."""
    score = {}
    for l in lists.values():
        for r, i in enumerate(l[:DEPTH]):
            score[i] = score.get(i, 0) + 1 / (r + 1)
    return score


def find_candidates_local(case, shortlist=SHORTLIST):
    """공고 → {queries, candidates (위 shortlist 개), counts {papers, repos, pool, shortlist}}."""
    bank, index = load_bank()
    names, per = cached_queries(case), comp_queries(case)
    first = rank(index, {"paper": [q["paper"] for q in per.values()] + names["paper_names"],
                         "repo": [q["repo"] for q in per.values()] + names["repo_names"]})
    pool = sorted(first, key=lambda i: -first[i])[:POOL]
    score = fuse(comp_lists(case, bank, pool))
    top = sorted(score, key=lambda i: -score[i])[:shortlist]
    counts = {"papers": len(index["paper"][1]) if "paper" in index else 0,
              "repos": len(index["repo"][1]) if "repo" in index else 0, "pool": len(pool), "shortlist": len(top)}
    return {"queries": {"per_competency": per, "paper_names": names["paper_names"], "repo_names": names["repo_names"]},
            "counts": counts, "candidates": [{**bank[i], "search_score": round(score[i], 3)} for i in top]}


def fit(ranking, case):
    """딱 맞는 후보: 필수 역량을 모두 덮는 후보 (있음 1 + 일부 0.5 가 필수 수와 같음). 하나도 없으면 필수 최고 점수와 같은 후보들."""
    need = sum(tier_of(c) == TIERS[0] for c in case["competencies"])
    best = max((r[TIERS[0]] for r in ranking), default=0)
    return [r for r in ranking if r[TIERS[0]] >= need] or [r for r in ranking if r[TIERS[0]] == best]


def judge_local(case, candidates):
    """첫 TRIAL 개를 판정해 원화를 재고 전부의 비용을 어림한다. SPEND_CAP 이하면 전부, 넘으면 위 FALLBACK 개만 pick_best.
    첫 묶음은 저장본(outputs/cache)에 남아 pick_best 에서 다시 돈을 쓰지 않는다."""
    before = llm.USAGE.get("krw", 0.0)
    judge(case, candidates[:TRIAL])
    trial = llm.USAGE.get("krw", 0.0) - before
    projected = trial * math.ceil(len(candidates) / TRIAL)
    n = len(candidates) if projected <= SPEND_CAP else FALLBACK
    out = pick_best(case, candidates[:n])
    return out, {"trial_krw": round(trial, 1), "projected_krw": round(projected, 1), "judged": n,
                 "spent_krw": round(llm.USAGE.get("krw", 0.0) - before, 1)}


def find_best_local(case, shortlist=SHORTLIST):
    """공고 → find_best 와 같은 모양에 counts·fit·adapted·cost·seconds 를 더한 것. 후보 전부의 칸(cells)은 결과 파일에 싣지 않는다."""
    t0 = time.time()
    found = find_candidates_local(case, shortlist)
    picked, cost = judge_local(case, found["candidates"])
    cells, order = picked.pop("cells"), picked.pop("order")
    before = llm.USAGE.get("krw", 0.0)
    adapted = adapt.adapt(case, found["candidates"][:cost["judged"]], cells, order)
    cost = {**cost, "adapt_krw": round(llm.USAGE.get("krw", 0.0) - before, 1)}
    k = fit(picked["ranking"], case)
    counts = {**found["counts"], "judged": cost["judged"], "k": len(k)}
    return {"counts": counts, "queries": found["queries"], **picked, "fit": k, "adapted": adapted, "cost": cost,
            "seconds": round(time.time() - t0, 1)}
