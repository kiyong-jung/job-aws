"""python -m m2_project <공고 이름> [--local]  → 가장 좋은 샘플 하나와 역량별 덮기 표를 찍는다.
--local 이면 웹 대신 로컬 DB(논문 서고 + 저장소 목록)에서 찾는다.
공고 이름은 inputs.CASES 의 열쇠 (예: naver_ml_intern).
"""
import collections
import sys

from . import CASES, find_best


def main(argv):
    if not argv or argv[0] not in CASES:
        print(__doc__ + "\n있는 공고: " + ", ".join(CASES))
        return
    out = find_best(argv[0], source="local" if "--local" in argv else "web")
    if "counts" in out:
        n = out["counts"]
        print(f'DB 검색: 논문 {n["papers"]:,}개·저장소 {n["repos"]:,}개 → 넓게 {n["pool"]:,}개 → 다시 골라 {n["shortlist"]}개 → 판정 {n["judged"]}개 → 딱 맞는 {n["k"]}개'
              f' ({out["cost"]["spent_krw"]:,.0f}원, {out["seconds"]:.0f}초)\n')
    s = out["sample"]
    print(f'샘플: {s["title"]} ({s["year"]}, {s["venue"]})\n{s["url"]}')
    print("필수 모두 있음" if out["must_all"] else f'필수를 다 덮는 후보가 없다. 빠진 필수: {", ".join(out["must_missing"])}')
    print()
    print("순위 (단계별 덮는 정도, 앞 단계부터 견줌):")
    for r in out["ranking"][:5]:
        print("  ", {k: v for k, v in r.items() if k != "title"}, r["title"][:60])
    print("덮기:", dict(collections.Counter(c["level"] for c in out["coverage"])))
    for c in out["coverage"]:
        print(f'  {c["cid"]} {c["section"]:4s} {c["level"]:2s} {c["name"]}')
    print("\n다음 후보:", [r["title"] for r in out["runner_up"]])
    if "adapted" in out:
        a, c = out["adapted"], out["adapted"]["checks"]
        print(f'\n응용: {a["project"]["title"]}\n  보완: {a["complements"]}\n  핵심 {a["hours"]["core"]}/{a["hours"]["budget"]}시간,'
              f' 묶음 {len(a["project"]["packages"])}개, 꼭 덮을 역량 {c["must_cover"]}, 지식 {c["knowledge_touched"]},'
              f' 확인 {"통과" if c["passed"] else "걸림 " + str(sorted({x["rule"] for x in c["issues"] if x["level"] == "fix"}))}')


if __name__ == "__main__":
    main(sys.argv[1:])
