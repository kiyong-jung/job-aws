"""④ 보조 실험: 역량 목록만으로 공고를 다시 쓰고, 원본 문장이 되살아났는지 0/1/2로 채점.
AI 채점은 보조다 — 사람이 같은 쌍을 출처를 가리고 다시 채점해 일치율을 함께 보고한다 (팀 규칙 1·4).

  python repro.py outputs/results_XXXX.csv            # 재현 + AI 채점 → outputs/repro_XXXX_*.csv
  python repro.py --human outputs/repro_XXXX_human.csv  # human_score 를 채운 뒤 일치율
조건: human(gold 정답) · ncs(NCS 결과의 standard_name) · general(일반 방식 결과) — 각각 1회차, REPRO_MODEL 기준
"""
import json, re, sys
from itertools import combinations
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from src.llm import call_model
from src.split import split_posting
from src.textmatch import cohen_kappa

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
REPRO = {"provider": "bedrock", "id": "global.anthropic.claude-sonnet-4-6"}                 # 쓰는 모델
JUDGE = {"provider": "bedrock", "id": "global.anthropic.claude-haiku-4-5-20251001-v1:0"}    # 채점 모델 (다르게)
REPRO_MODEL_KEY = "claude-sonnet"
RUNS = 2
TARGET = ["담당업무", "자격요건", "우대사항", "기술질문", "팀메시지"]
P = lambda n: (ROOT / "prompts" / n).read_text(encoding="utf-8")


def obj(text):
    t = re.sub(r"```(?:json)?", "", text); return json.loads(t[t.find("{"): t.rfind("}") + 1])


def lists(res, posting):
    r = res[(res.posting == posting) & (res.run == 1)]
    pick = lambda m: r[(r.method == m) & (r.model == REPRO_MODEL_KEY)] if ((r.method == m) & (r.model == REPRO_MODEL_KEY)).any() else r[r.method == m]
    out = {"human": pd.read_csv(ROOT / "gold" / f"{posting}_gold.csv", comment="#").name.tolist()}
    if (r.method == "ncs").any():
        out["ncs"] = [n for n in pick("ncs").standard_name.astype(str).str.strip().unique() if n and n not in ("없음", "nan")]
    if (r.method == "general").any():
        out["general"] = pick("general").name.astype(str).tolist()
    return out


def run(res_path):
    res = pd.read_csv(res_path); stamp = res_path.stem.replace("results_", "")
    rows, logs = [], []
    for posting in res.posting.unique():
        sent = split_posting((ROOT / "postings" / f"{posting}.txt").read_text(encoding="utf-8"))
        tgt = sent[sent.section.isin(TARGET)]
        orig = "\n".join(f"[{r.id}] {r.sentence}" for r in tgt.itertuples())
        for cond, comps in lists(res, posting).items():
            for run_i in range(1, RUNS + 1):
                rep = call_model(REPRO, P("repro.txt").format(competencies="\n".join(f"- {c}" for c in comps)), run_i)["text"]
                j = obj(call_model(JUDGE, P("judge.txt").format(original=orig, reproduced=rep), run_i)["text"])
                got = {str(x.get("id")): x for x in j.get("scores", [])}
                for r in tgt.itertuples():
                    x = got.get(r.id, {})
                    rows.append({"posting": posting, "condition": cond, "run": run_i, "id": r.id, "original": r.sentence,
                                 "ai_score": str(x.get("score", "누락")).upper(), "matched": x.get("matched", ""), "reproduced": rep})
                logs.append({"posting": posting, "condition": cond, "run": run_i, "unsupported": len(j.get("unsupported", []))})
                print(f"✅ {posting} | {cond} | {run_i}회")
    R = pd.DataFrame(rows); L = pd.DataFrame(logs)
    summ = []
    for (posting, cond), g in R.groupby(["posting", "condition"]):
        v = g[g.ai_score.isin(["0", "1", "2"])]
        sets = {r: set(x[x.ai_score == "2"].id) for r, x in v.groupby("run")}
        pr = list(combinations(sorted(sets), 2))
        summ.append({"posting": posting, "condition": cond,
                     "strict_recall": round((v.ai_score == "2").mean(), 3), "lenient_recall": round(v.ai_score.isin(["1", "2"]).mean(), 3),
                     "unsupported": L[(L.posting == posting) & (L.condition == cond)].unsupported.mean(),
                     "retest": round(sum(len(sets[a] & sets[b]) / max(1, len(sets[a] | sets[b])) for a, b in pr) / len(pr), 3) if pr else None})
    S = pd.DataFrame(summ); print(S.to_string(index=False))
    base = res_path.parent / f"repro_{stamp}"
    R.to_csv(f"{base}_scores.csv", index=False, encoding="utf-8-sig"); S.to_csv(f"{base}_summary.csv", index=False, encoding="utf-8-sig")
    conds = sorted(R.condition.unique()); blind = {c: f"X{i+1}" for i, c in enumerate(conds)}
    H = R[R.ai_score != "NA"].sample(n=min(40, len(R)), random_state=0)
    H.assign(condition=H.condition.map(blind), human_score="")[["condition", "run", "id", "original", "reproduced", "human_score", "ai_score"]] \
        .to_csv(f"{base}_human.csv", index=False, encoding="utf-8-sig")
    print(f"사람 판정 양식: {base}_human.csv (ai_score 열을 가리고 human_score 에 0/1/2/NA)")


if sys.argv[1] == "--human":
    h = pd.read_csv(sys.argv[2]).dropna(subset=["human_score"])
    a = h.human_score.astype(str).str.upper().str.replace(".0", "", regex=False).tolist(); b = h.ai_score.astype(str).str.upper().tolist()
    print(f"{len(h)}쌍 · 완전 일치 {sum(x == y for x, y in zip(a, b)) / len(a):.0%} · Cohen's κ {cohen_kappa(a, b):.2f}")
else:
    run(Path(sys.argv[1]))
