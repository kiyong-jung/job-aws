"""공고 → 가장 좋은 샘플 프로젝트 하나. 두 걸음이다.

① 찾기: LLM 이 검색어를 만들고 후보를 모은다. source="web" 은 웹 검색 (search.py),
   source="local" 은 로컬 DB 에서 역량별 검색어 + BM25 위 1000 → 역량마다 Cohere 로 다시 골라 위 100 (local.py)
② pick_best: LLM 이 후보마다 역량별 덮기를 판정하고, 코드가 필수 → 우대 → 나머지 순으로 견줘 하나를 고른다 (pick.py)
③ 응용 (local 만): 1등을 보완 2~3개의 부분으로 학생 팀 프로젝트 하나로 바꾼다 (adapt.py)
"""
import json

from shared import config

from .inputs import CASES, build_input
from .local import find_best_local, find_candidates_local
from .pick import pick_best
from .search import find_candidates


def find_best(case_id, source="web"):
    """공고 이름 → {case, posting, sample, runner_up, ranking, coverage, queries}.
    web: outputs/project/<공고>.best.json. local: 여기에 counts·fit·cost 를 더해 <공고>.local.json."""
    case = build_input(case_id)
    if source == "local":
        out = {"case": case_id, "posting": case["posting"], **find_best_local(case)}
        name = f"{case_id}.local.json"
    else:
        found = find_candidates(case)
        picked = pick_best(case, found["candidates"])
        del picked["cells"], picked["order"]
        out = {"case": case_id, "posting": case["posting"], "queries": {k: found[k] for k in ("paper_queries", "repo_queries", "paper_names", "repo_names")}, **picked}
        name = f"{case_id}.best.json"
    path = config.OUTPUTS / "project" / name
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    return out


__all__ = ["CASES", "build_input", "find_best", "find_candidates", "find_candidates_local", "pick_best"]
