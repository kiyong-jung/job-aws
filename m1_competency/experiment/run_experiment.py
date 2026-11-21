"""역량 추출 실험: 공고 × 모델 × 방법 × 반복 횟수만큼 실행하고 outputs/에 CSV로 저장.

실행:  python run_experiment.py
처음엔 MODEL_KEYS 하나, N_RUNS = 1 로 작게 돌려 비용을 확인한다 (팀 규칙 8).
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.split import split_posting, numbered_text
from src.extract import competency_prompt, question_prompt, parse_json_list
from src.llm import call_model

load_dotenv(Path(__file__).resolve().parent / ".env")

# ===================== ✏️ 설정 =====================
POSTINGS = ["postings/naver_ml_intern.txt"]          # 여러 공고 가능
MODELS = {  # Bedrock 에서 쓸 수 있던 최신 버전 (5.5는 권한 없음, 2026-11-11 확인)
    "claude-sonnet": {"provider": "bedrock", "id": "global.anthropic.claude-sonnet-4-6"},
    "claude-haiku":  {"provider": "bedrock", "id": "global.anthropic.claude-haiku-4-5-20251001-v1:0"},
    "gpt":           {"provider": "openai",  "id": "여기에_GPT_모델명"},   # 모델명·키 받으면 채우기
}
MODEL_KEYS = ["claude-sonnet", "claude-haiku"]
METHODS = ["general"]          # "general", "ncs", "esco", "via_q"
N_RUNS = 3
TEMPERATURE = None             # None = 모델 기본값
# ==================================================

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def run_one(method, posting_name, sent, mk, run):
    """한 번 실행 → (역량 행 목록, 로그 한 줄)"""
    numbered = numbered_text(sent)
    valid = dict(zip(sent["id"], sent["sentence"]))
    calls, questions_json, n_q = [], "", None

    if method == "via_q":                           # 1단계: 면접 질문 만들기
        r1 = call_model(MODELS[mk], question_prompt(numbered), run, TEMPERATURE)
        qs, _ = parse_json_list(r1["text"])
        questions_json, n_q = json.dumps(qs, ensure_ascii=False), len(qs)
        calls.append(r1)

    r = call_model(MODELS[mk], competency_prompt(method, numbered, questions_json), run, TEMPERATURE)
    calls.append(r)
    items, had_block = parse_json_list(r["text"])

    rows = []
    for it in items:
        ev = str(it.get("evidence_id", "")).strip()
        rows.append({"posting": posting_name, "method": method, "model": mk, "run": run,
                     "name": it.get("name"), "type": it.get("type"),
                     "priority": it.get("priority"), "basis": it.get("basis"),
                     "evidence_id": ev, "evidence_valid": ev in valid,
                     "evidence_text": valid.get(ev, ""), "reason": it.get("reason", ""),
                     "standard_code": it.get("standard_code", ""),
                     "standard_name": it.get("standard_name", "")})
    log = {"posting": posting_name, "method": method, "model": mk, "run": run, "ok": True,
           "n_items": len(items), "n_questions": n_q,
           "invalid_evidence": sum(not x["evidence_valid"] for x in rows),
           "codeblock_violation": had_block,
           "seconds": sum(c["seconds"] for c in calls),
           "input_tokens": sum(c["input_tokens"] or 0 for c in calls),
           "output_tokens": sum(c["output_tokens"] or 0 for c in calls),
           "cached": all(c["cached"] for c in calls), "error": ""}
    return rows, log


def main():
    results, logs, sentences = [], [], []
    for p in POSTINGS:
        name = Path(p).stem
        sent = split_posting((ROOT / p).read_text(encoding="utf-8"))
        sentences.append(sent.assign(posting=name))
        for method in METHODS:
            for mk in MODEL_KEYS:
                for run in range(1, N_RUNS + 1):
                    tag = f"{name} | {method} | {mk} | {run}회"
                    try:
                        rows, log = run_one(method, name, sent, mk, run)
                        results += rows
                        logs.append(log)
                        print(f"✅ {tag}: {log['n_items']}개, 근거번호 오류 {log['invalid_evidence']}개"
                              f"{' (캐시)' if log['cached'] else ''}")
                    except Exception as e:
                        logs.append({"posting": name, "method": method, "model": mk, "run": run,
                                     "ok": False, "error": str(e)[:300]})
                        print(f"❌ {tag}: {e}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    pd.concat(sentences).to_csv(OUT / f"sentences_{stamp}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(results).to_csv(OUT / f"results_{stamp}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(logs).to_csv(OUT / f"log_{stamp}.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: outputs/results_{stamp}.csv  →  다음: python score.py outputs/results_{stamp}.csv")


if __name__ == "__main__":
    main()
