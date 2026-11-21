"""② 프로젝트 찾기의 단계별 실제 후보 이름 → demo/data/<예시>.project.json 의 names (사용자 11/21: 각 단계의 프로젝트 이름, 논문·깃헙 색 다르게).
  PYTHONPATH=. .venv/bin/python demo/design/build_names.py <예시>
읽는 것: outputs/project/<예시>.rerank.json (낱말로 모은 1,000개와 역량마다 Cohere 점수), .local.json (다시 고른 100개의 순위).
논문 제목은 data/papers 의 jsonl 에서 주소(url·doi·arxiv)로 찾는다. 모델 호출 없음.
names.pool: 1,000개 가운데 보여 줄 이름 (다시 고른 100개에 남는 것 절반 + 떨어지는 것 절반, 각각 논문 반·저장소 반, 점수 차례). short 는 100개에 남는가.
names.top: 다시 고른 100개의 위 다섯 (순위 차례)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "project"
DATA = Path(__file__).resolve().parents[1] / "data"
SHOW = 28


def paper_titles(keys):
    want = {k.split(":", 1)[1]: k for k in keys if not k.startswith("gh:")}
    got = {}
    for f in (ROOT / "data" / "papers").rglob("*.jsonl"):
        if f.parent.name == "_raw":
            continue
        for line in f.open(encoding="utf-8"):
            p = json.loads(line)
            for field in ("url", "doi", "arxiv"):
                v = p.get(field)
                if v and v in want:
                    got[want[v]] = p["title"]
        if len(got) == len(want):
            break
    return got


def build(case):
    local = json.loads((OUT / f"{case}.local.json").read_text(encoding="utf-8"))
    ranking = local["ranking"]
    rank = {r["key"]: i for i, r in enumerate(ranking, 1)}
    kind = lambda k: "repo" if k.startswith("gh:") else "paper"
    rr = OUT / f"{case}.rerank.json"
    if rr.exists():      # 낱말로 모은 1,000개: 역량마다 Cohere 점수 → 가장 높은 점수로 줄 세운다
        best = {}
        for scores in json.loads(rr.read_text(encoding="utf-8")).values():
            for k, v in scores.items():
                best[k] = max(best.get(k, 0), v)
        order = sorted(best, key=best.get, reverse=True)
        def half(group, n):      # 논문 반, 저장소 반 (한쪽이 모자라면 다른 쪽으로 채운다), 점수 차례
            papers, repos = [k for k in group if kind(k) == "paper"], [k for k in group if kind(k) == "repo"]
            a = papers[:n // 2]; b = repos[:n - len(a)]
            return a + b + papers[len(a):len(a) + n - len(a) - len(b)]
        kept = half([k for k in order if k in rank], SHOW // 2)
        gone = half([k for k in order if k not in rank], SHOW - len(kept))
        keys = sorted(kept + gone, key=lambda k: -best[k])
    else:                # 1,000개 기록이 없는 공고: 다시 고른 100개 안에서만
        keys = [r["key"] for r in ranking[:SHOW]]
    titles = {r["key"]: r["title"] for r in ranking} | paper_titles([k for k in keys if k not in rank])
    for k in keys:
        titles.setdefault(k, k.split(":", 1)[1] if k.startswith("gh:") else k.rsplit("/", 1)[-1])
    names = {"pool": [{"title": titles[k], "kind": kind(k), "short": k in rank, "rank": rank.get(k)} for k in keys],
             "top": [{"title": r["title"], "kind": kind(r["key"]), "rank": i} for i, r in enumerate(ranking[:5], 1)],
             "pool_from_rerank": rr.exists()}
    f = DATA / f"{case}.project.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["names"] = names
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(case, "pool", len(names["pool"]), "(남음", sum(x["short"] for x in names["pool"]), ")", "논문", sum(x["kind"] == "paper" for x in names["pool"]),
          "| top", [x["title"][:30] for x in names["top"]])


if __name__ == "__main__":
    build(sys.argv[1])
