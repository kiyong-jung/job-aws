"""라운드랩 커리큘럼 생성기(github.com/gaori2952/Round_labcurriculum)의 입력 CSV 두 개를 공고마다 만든다.
  PYTHONPATH=. .venv/bin/python demo/design/make_team_csv.py <예시> <폴더>
→ <폴더>/프로젝트_뽑힌프로젝트.csv (원본 1 + 보조 3), <폴더>/교육자료_고른자료.csv (핵심 + 보조). 칸 이름은 출력 스키마 그대로, 여러 값은 '; '.
읽는 것: outputs/project/<예시>.local.json·.adapt.json, outputs/materials/<예시>.json, m3 교육자료 은행 (모델 호출 없음)."""
import csv
import json
import sys
from pathlib import Path

from m2_project import inputs
from m3_materials import pick

ROOT = Path(__file__).resolve().parents[2]
J = "; ".join


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build(case, out, local=None, adapt=None, mat=None, comps=None):
    """local·adapt·mat·comps 를 넘기면 그것을 쓴다 (새 공고: demo/live.py). 아니면 outputs/ 의 저장본과 예시 공고의 역량"""
    out.mkdir(parents=True, exist_ok=True)
    local = local or json.loads((ROOT / f"outputs/project/{case}.local.json").read_text(encoding="utf-8"))
    adapt = adapt or json.loads((ROOT / f"outputs/project/{case}.adapt.json").read_text(encoding="utf-8"))
    mat = mat or json.loads((ROOT / f"outputs/materials/{case}.json").read_text(encoding="utf-8"))
    name = {c["id"]: c["name"] for c in (comps or inputs.build_input(case)["competencies"])}
    rank = {r["title"]: (i, r) for i, r in enumerate(local["ranking"], 1)}
    gains = {g["title"]: g for g in adapt["complement_gains"]}
    packs = adapt["project"]["packages"]
    rows = []
    for role, t in [("원본", adapt["base"])] + [(f"보조 {i}", t) for i, t in enumerate(adapt["complements"], 1)]:
        i, r = rank[t]
        g = gains.get(t, {})
        used = [(p["id"], c) for p in packs for s in p["sources"] if s["project"] == t for c in s["for"]]
        rows.append([role, t, "깃헙" if r["kind"] == "repo" else "논문", r["url"],
                     f"GitHub ★{r['stars']}" if r["kind"] == "repo" else r.get("venue", ""), i, r["필수"], r["우대"], r["나머지"],
                     g.get("필수", ""), g.get("우대", ""), g.get("나머지", ""),
                     J(dict.fromkeys(f"{c} {name[c]}" for _, c in used)), J(dict.fromkeys(pid for pid, _ in used))])
    write(out / "프로젝트_뽑힌프로젝트.csv", ["role", "title", "kind", "url", "venue", "rank", "필수", "우대", "나머지",
                                           "gain_필수", "gain_우대", "gain_나머지", "borrowed", "packages"], rows)
    bank = {r["id"]: r for r in pick.bank()[0]}
    cells = {c["id"]: c["cells"] for c in mat["candidates"]}
    rows = []
    for p in mat["picks"]:
        b = bank.get(p["id"], {})
        rows.append([p["role"], p["gain"], p["id"], b.get("bank", ""), p["type"], p["title"], p["url"], b.get("topic", ""), b.get("summary", ""),
                     b.get("source", ""), J(f"{c} {name[c]}: {lv}" for c, lv in p["covers"].items()),
                     J(f"{c}: {(cells.get(p['id'], {}).get(c) or {}).get('quote', '')}" for c in p["covers"])])
    write(out / "교육자료_고른자료.csv", ["role", "gain", "id", "bank", "type", "title", "url", "topic", "summary", "source", "covers", "quote"], rows)
    print(case, "→", out, f"프로젝트 {len(adapt['complements']) + 1}줄 · 교육자료 {len(mat['picks'])}줄")


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]))
