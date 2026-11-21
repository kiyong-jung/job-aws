"""② 응용 프로젝트의 데모 저장본을 만든다: outputs/project/<예시>.local.json 의 adapted (m2_project/adapt.py 결과) → data/<예시>.adapt.json.
outputs/ 는 git 에 올리지 않으므로 화면이 쓰는 값만 옮겨 둔다. 프로젝트의 주소는 같은 파일의 순위 목록에서 찾는다. 모델 호출 없음.
  PYTHONPATH=. .venv/bin/python demo/design/build_adapt.py [예시 이름, 기본 naver_ml_intern]
"""
import json
import sys
from pathlib import Path

CASE = sys.argv[1] if len(sys.argv) > 1 else "naver_ml_intern"      # 예시 공고 이름 (demo/pipeline.py EXAMPLES)
SRC = Path(f"outputs/project/{CASE}.local.json")
OUT = Path(f"demo/data/{CASE}.adapt.json")
# 화면에서 부르는 짧은 이름 (발표 자료와 같은 이름). 보완 프로젝트가 바뀌면 여기서 멈춘다 (새 예시는 그 프로젝트의 이름을 더한다)
SHORT = {"duoan/mega-data-factory": "mega-data-factory", "MigoXLab/dingo": "dingo",
         '"Capturing, Reconstructing, and Simulating: The UrbanScene3D Dataset"': "UrbanScene3D",
         "Goku: Flow Based Video Generative Foundation Models": "Goku",
         "genkit-ai/genkit": "genkit", "open-hand/choerodon": "choerodon",
         "FareedKhan-dev/production-grade-agentic-system": "production-grade-agentic-system", "cloudcomponents/cdk-constructs": "cdk-constructs"}


def build(src):
    a = src["adapted"]
    where = {r["title"]: r for r in src["ranking"]}
    ref = lambda t: {"title": t, "short": SHORT[t], "kind": where[t]["kind"], "url": where[t]["url"]}
    return {
        "source": f"{SRC} (adapted)", "made": a["made"], "krw": a["checks"]["krw"],
        "base": ref(a["base"]), "complements": [ref(t) for t in a["complements"]],
        "title": a["project"]["title"], "goal": a["project"]["goal"],
        # do·out·quote·why: ③ 화면이 "1위에 없던 역량을 어떤 일로 채우나"를 근거 문장과 함께 보인다 (사용자 11/21)
        "packages": [{"id": p["id"], "name": p["name"], "hours": p["hours"], "core": p["core"], "order": p["order"], "do": p["do"], "out": p["out"],
                      "sources": [{"project": s["project"], "for": s["for"], "quote": s.get("quote", "")} for s in p["sources"]],
                      "added": [x["competency"] for x in p["added"]], "why": {x["competency"]: x["why"] for x in p["added"]}} for p in a["project"]["packages"]],
        "hours": a["hours"],
        "coverage": [{"id": c["id"], "name": c["name"], "tier": c["tier"], "packages": c["packages"], "expect": c["expect"], "note": c.get("note", "")} for c in a["coverage"]],
        "tier_counts": a["tier_counts"],
    }


if __name__ == "__main__":
    data = build(json.loads(SRC.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: 묶음 {len(data['packages'])}개, 역량 {len(data['coverage'])}개, 보완 {[c['short'] for c in data['complements']]}")
