"""③ 교육자료 찾기의 데모 저장본을 만든다: outputs/materials/<예시>.json (m3_materials/pick.py 결과) → data/<예시>.m3.json.
outputs/ 는 git 에 올리지 않으므로 화면이 쓰는 값만 옮겨 둔다. 모델 호출 없음.
  PYTHONPATH=. .venv/bin/python demo/design/build_m3.py [예시 이름, 기본 naver_ml_intern]
"""
import json
import sys
from pathlib import Path

CASE = sys.argv[1] if len(sys.argv) > 1 else "naver_ml_intern"      # 예시 공고 이름 (demo/pipeline.py EXAMPLES)
SRC = Path(f"outputs/materials/{CASE}.json")
OUT = Path(f"demo/data/{CASE}.m3.json")


def build(src):
    cells = {c["id"]: c["cells"] for c in src["candidates"]}
    level = {c["cid"]: c["level"] for c in src["coverage"]}
    r = src["rules"]
    return {
        "case": src["case"],
        "rules": {"must": r["weight"]["필수"], "other": r["weight"]["우대·나머지"], "core": r["core"], "support": r["support"], "types": r["types"],
                  "bank_rows": r["bank_rows"], "wide": r["wide"], "shortlist": r["shortlist"]},      # ④ 숫자 흐름 (은행 → BM25 → Rerank)
        "candidates": len(src["candidates"]),
        "cost_krw": src["cost_krw"],
        "targets": [{"cid": t["cid"], "name": t["name"], "type": t["type"], "priority": t["priority"], "level": level[t["cid"]]} for t in src["targets"]],
        "picks": [{"role": p["role"], "title": p["title"], "type": p["type"], "url": p["url"],
                   "covers": [{"cid": cid, "level": lv, "quote": (cells.get(p["id"], {}).get(cid) or {}).get("quote", "")} for cid, lv in p["covers"].items()]}
                  for p in src["picks"]],      # quote: 그 자료가 그 역량을 다룬다는 근거 구절 (판정이 자료 글에서 그대로 옮긴 것)
    }


if __name__ == "__main__":
    data = build(json.loads(SRC.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: 대상 역량 {len(data['targets'])}개, 자료 {len(data['picks'])}개")
