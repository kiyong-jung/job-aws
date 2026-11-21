"""② 엄격·관대 정밀도·재현율 + ③ 오류 유형. 매칭 판단은 사람이 한다 (코드는 후보만 제안).

1회:  python score.py outputs/results_XXXX.csv
      → outputs/matching_XXXX.csv
        gold_id : 근거 문장이 같은 정답 후보 중 이름이 가장 비슷한 것을 미리 채움(제안). 틀리면 고치고, 해당 없으면 '-'
        match   : 사람이 채움 — 엄격(같은 역량) / 관대(같은 문장의 상위·일부) / 없음
                  이름이 정답과 똑같으면 '엄격'으로 미리 채움
        error   : (선택) 뭉갬 / 유형오류 / 기타. 누락·지어냄·쪼갬은 코드가 센다
2회:  같은 명령 → outputs/score_XXXX.csv
지표 (SkillSpan · Nguyen 외 2024 방식): 엄격·관대 각각 precision, recall, F1
  + 누락(정답 중 못 찾음) · 지어냄(원문에 없는 근거 번호) · 쪼갬(한 정답에 2개 이상 대응) · 재시험 일치도
"""
import sys
from itertools import combinations
from pathlib import Path
import pandas as pd
from src.textmatch import norm, dice

GOLD_DIR = Path(__file__).resolve().parent / "gold"


def load_gold(p):
    return pd.read_csv(GOLD_DIR / f"{p}_gold.csv", comment="#")


def make_matching(res, path):
    rows = []
    for posting, g in res.groupby("posting"):
        gold = load_gold(posting)
        names = dict(zip(gold.gold_id, gold.name))
        by_ev = {}
        for r in gold.itertuples():
            for ev in [r.evidence_id] + (str(r.also_evidence).split(";") if pd.notna(getattr(r, "also_evidence", None)) else []):
                by_ev.setdefault(ev.strip(), []).append(r.gold_id)
        for r in g.itertuples():
            cands = list(dict.fromkeys(by_ev.get(r.evidence_id, [])))
            best = max(cands, key=lambda c: dice(r.name, names[c]), default="")
            exact = best and norm(best and names[best]) == norm(r.name)
            rows.append({"posting": posting, "method": r.method, "model": r.model, "run": r.run,
                         "name": r.name, "evidence_id": r.evidence_id, "evidence_valid": r.evidence_valid,
                         "candidates": "; ".join(f"{c} {names[c]}" for c in cands),
                         "gold_id": best or "-", "match": "엄격" if exact else "", "error": ""})
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    left = sum(1 for x in rows if not x["match"])
    print(f"생성: {path.name} · 사람이 match 를 채울 줄 {left}개 (gold_id 제안도 확인)")


def jac(a, b):
    return len(a & b) / len(a | b) if (a | b) else 1.0


def compute(m, path):
    m["match"] = m["match"].fillna("").str.strip()
    if (m["match"] == "").any():
        print("⚠️ match 가 빈 줄이 있어요. 채운 뒤 다시 실행하세요."); return
    out = []
    for (posting, method, model), g in m.groupby(["posting", "method", "model"]):
        gold_n = len(load_gold(posting))
        rec = {"posting": posting, "method": method, "model": model, "runs": g.run.nunique(), "gold_n": gold_n,
               "outputs_per_run": round(len(g) / g.run.nunique(), 1)}
        for label, ok in (("strict", {"엄격"}), ("relaxed", {"엄격", "관대"})):
            P, R = [], []
            for _, x in g.groupby("run"):
                hit = x[x.match.isin(ok)]
                P.append(len(hit) / len(x)); R.append(hit.gold_id.nunique() / gold_n)
            p, r = sum(P) / len(P), sum(R) / len(R)
            rec |= {f"{label}_P": round(p, 3), f"{label}_R": round(r, 3), f"{label}_F1": round(2 * p * r / (p + r), 3) if p + r else 0}
        rel = g[g.match.isin({"엄격", "관대"})]
        rec["누락_per_run"] = round(gold_n - rel.groupby("run").gold_id.nunique().mean(), 1) if len(rel) else gold_n
        rec["지어냄"] = int((~g.evidence_valid.astype(bool)).sum())
        rec["쪼갬_per_run"] = round((rel.groupby(["run", "gold_id"]).size() - 1).clip(lower=0).groupby("run").sum().mean(), 1) if len(rel) else 0
        for e, n in g[g.error.fillna("") != ""].error.value_counts().items():
            rec[f"err_{e}"] = int(n)
        sets = {r: set(x[x.match.isin({"엄격", "관대"})].gold_id) for r, x in g.groupby("run")}
        pairs = list(combinations(sorted(sets), 2))
        rec["retest"] = round(sum(jac(sets[a], sets[b]) for a, b in pairs) / len(pairs), 3) if pairs else None
        out.append(rec)
    df = pd.DataFrame(out); df.to_csv(path, index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))


res_path = Path(sys.argv[1]); stamp = res_path.stem.replace("results_", "")
mp = res_path.parent / f"matching_{stamp}.csv"
if not mp.exists():
    make_matching(pd.read_csv(res_path), mp)
else:
    compute(pd.read_csv(mp), res_path.parent / f"score_{stamp}.csv")
