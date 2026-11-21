"""응용 단계: 보완 고르기와 코드 확인. 모델·네트워크 없이."""
import copy

import pytest

import m2_project as project
from m2_project import adapt

BASE, COMP = "base/x", "comp/y"
CASE = {"case": "t", "posting": {"title": "t"},
        "sentences": [{"id": "S1", "section": "자격요건", "text": "생성 모델 이해"},
                      {"id": "S2", "section": "우대사항", "text": "데이터셋 구축"},
                      {"id": "S3", "section": "팀메시지", "text": "피드백 협업"},
                      {"id": "S4", "section": "우대사항", "text": "렌더링 엔진(Blender, Unreal Engine 등) 경험"}],
        "competencies": [{"id": "C01", "name": "생성 모델", "type": "지식", "priority": "필수", "evidence_id": "S1"},
                         {"id": "C02", "name": "데이터셋", "type": "수행", "priority": "우대", "evidence_id": "S2"},
                         {"id": "C03", "name": "협업", "type": "협업·태도", "priority": "구분없음", "evidence_id": "S3"},
                         {"id": "C04", "name": "Blender", "type": "도구", "priority": "우대", "evidence_id": "S4"},
                         {"id": "C05", "name": "Unreal Engine", "type": "도구", "priority": "우대", "evidence_id": "S4"},
                         {"id": "C06", "name": "확산 모델 원리", "type": "지식", "priority": "구분없음", "evidence_id": "S1"}]}
PROJECTS = [{"role": "base", "c": {"title": BASE}, "text": "the base pipeline loads data from shards and filters images by quality",
             "cells": {"C01": {"level": "있음", "quote": "loads data from shards"}}},
            {"role": "complement", "c": {"title": COMP}, "text": "we render scenes in Blender with python scripts and build a dataset",
             "cells": {"C02": {"level": "있음", "quote": "build a dataset"}, "C04": {"level": "있음", "quote": "render scenes in Blender"}}}]


def package(i, comps, sources=(), added=(), hours=20, core=True):
    return {"id": f"W{i}", "name": "", "do": "", "out": "", "hours": hours, "core": core, "order": 1,
            "competencies": list(comps), "sources": [{"project": p, "quote": q, "for": list(f)} for p, q, f in sources],
            "added": [{"competency": c, "why": "입력에 없다"} for c in added]}


def good():
    base_src = (BASE, "loads data from shards and filters images", ["C01"])
    packs = [package(1, ["C01"], [base_src]),
             package(2, ["C02", "C04", "C05"], [(COMP, "render scenes in Blender with python scripts", ["C02", "C04"])],
                     added=["C05"]),
             package(3, ["C03"], added=["C03"])] + [package(i, [], [base_src]) for i in (4, 5, 6)]
    packs[1]["do"] = "Blender 와 Unreal Engine 으로 장면을 렌더링해 데이터셋을 만든다"     # 도구 역량은 묶음 글에 이름이 있어야 붙는다
    cov = [{"id": "C01", "expect": "있음", "note": ""},
           {"id": "C02", "expect": "있음", "note": ""},
           {"id": "C03", "expect": "일부", "note": "주간 검토 기록"},
           {"id": "C04", "expect": "있음", "note": ""},
           {"id": "C05", "expect": "일부", "note": "같은 장면을 내보내 렌더만"},
           {"id": "C06", "expect": "없음", "note": "지식이라 교육자료로"}]
    return {"title": "", "goal": "", "packages": packs, "coverage": cov, "decisions": [], "doubts": []}


def rules(got, budget=336):
    return {x["rule"] for x in adapt.check(got, CASE, PROJECTS, {**adapt.TEAM, "budget_hours": budget})
            if x["level"] == "fix"}


def test_alternative_tools_in_one_sentence_count_as_one_item():
    groups = adapt.items(CASE)
    assert ["C04", "C05"] in groups and ["C01"] in groups
    naver = adapt.items(project.build_input("naver_ml_intern"))
    assert ["C19", "C20", "C21", "C22"] in naver           # "Isaac Sim, Omniverse, Blender, Unreal Engine 등"
    assert ["C04"] in naver and ["C05"] in naver           # "연산 및 I/O 병목" 은 둘 다 요구한다 (유형 지식)


def cells(**levels):
    return {cid: {"level": lv, "quote": "q"} for cid, lv in levels.items()}


def test_complements_fill_gaps_by_tier_and_count_tool_alternatives_once():
    table = [cells(C01="있음"),                         # 0 바탕
             cells(C04="있음", C05="있음"),              # 1 도구 둘이지만 한 거리: 우대 1
             cells(C04="있음", C03="있음"),              # 2 우대 1 + 나머지 1
             cells(C02="일부"),                          # 3 우대 0.5
             cells(C03="일부")]                          # 4 나머지 0.5 뿐
    got = adapt.pick_complements(CASE, table, [0, 1, 2, 3, 4])
    assert [i for i, _ in got] == [2, 3]                 # 2 가 1 을 이긴다. 4 는 나머지 1.0 미만이라 멈춘다
    assert got[0][1] == (0, 1, 1) and got[1][1] == (0, 0.5, 0)


def test_complements_fill_required_gaps_of_the_base_first():
    covers_required, more_preferred = cells(C01="있음"), cells(C02="있음", C04="있음")
    assert [i for i, _ in adapt.pick_complements(CASE, [cells(C01="있음"), covers_required, more_preferred], [0, 1, 2])] == [2]
    got = adapt.pick_complements(CASE, [{}, more_preferred, covers_required], [0, 1, 2])   # 바탕이 필수 C01 을 못 덮는다
    assert [i for i, _ in got] == [2, 1] and got[0][1] == (1, 0, 0)   # 필수 하나가 우대 둘보다 먼저


def test_complements_stop_at_three():
    table = [{}] + [cells(**{cid: "있음"}) for cid in ("C02", "C03", "C04", "C06")]
    assert len(adapt.pick_complements(CASE, table, list(range(5)))) == 3


def test_good_answer_passes_checks():
    assert rules(good()) == set()


def test_required_the_base_covers_must_come_from_the_base():
    g = good()
    g["packages"][0]["sources"] = [{"project": COMP, "quote": "render scenes in Blender with python scripts", "for": ["C01"]}]
    with_comp = copy.deepcopy(PROJECTS)
    with_comp[1]["cells"]["C01"] = {"level": "있음", "quote": "q"}
    assert "R7" in {x["rule"] for x in adapt.check(g, CASE, with_comp, adapt.TEAM) if x["level"] == "fix"}


def gap_projects(base_level):
    """바탕이 필수 C01 을 base_level 로만 덮고, 보완이 C01 을 있음으로 덮는 입력."""
    p = copy.deepcopy(PROJECTS)
    p[0]["cells"]["C01"]["level"] = base_level
    if base_level == "없음":
        del p[0]["cells"]["C01"]
    p[1]["cells"]["C01"] = {"level": "있음", "quote": "build a dataset"}
    return p


def base_cites_no_c01(g):
    for p in g["packages"]:
        for s in p["sources"]:
            if s["project"] == BASE:
                s["for"] = [c for c in s["for"] if c != "C01"]
    return g


def found(g, projects):
    return {(x["rule"], x["level"]) for x in adapt.check(g, CASE, projects, adapt.TEAM)}


def test_a_required_gap_of_the_base_is_a_warning_when_a_complement_fills_it():
    g = base_cites_no_c01(good())
    g["packages"][0]["sources"].append({"project": COMP, "quote": "we render scenes in Blender with python", "for": ["C01"]})
    assert found(g, gap_projects("없음")) == {("R0", "warn")}
    assert found(good(), gap_projects("일부")) == {("R0", "warn")}       # 바탕 일부 + 보완 없이도 핵심에서 덮으면 통과


def test_a_required_gap_no_input_covers_may_be_added_but_not_left_out():
    p = gap_projects("없음")
    del p[1]["cells"]["C01"]
    g = base_cites_no_c01(good())
    g["packages"][0]["added"] = [{"competency": "C01", "why": "아무 입력도 덮지 않는다"}]
    assert found(g, p) == {("R0", "warn")}
    cited = copy.deepcopy(good())                       # 바탕 칸이 없음인데 바탕을 출처로 대면 R3
    assert ("R3", "fix") in found(cited, p)
    g["packages"][0]["core"] = False                    # 핵심 밖으로 빼면 R7
    assert ("R7", "fix") in found(g, p)


def test_a_short_quote_that_is_in_the_text_says_it_is_short():
    g = good()
    g["packages"][0]["sources"][0]["quote"] = "loads data from shards"
    [msg] = [x["detail"] for x in adapt.check(g, CASE, PROJECTS, adapt.TEAM) if x["rule"] == "R1"]
    assert "4낱말" in msg and "그대로 없다" not in msg


def test_the_rewrite_gets_every_problem_with_warnings_marked_optional(monkeypatch):
    asked = []
    bad = good()
    bad["packages"][1]["sources"][0]["for"].append("C05")       # R3: 보완 칸 C05 는 없음
    bad["packages"][2]["core"] = False                          # R14 경고: 협업 C03 이 핵심 밖
    answers = iter([bad, good()])
    monkeypatch.setattr(adapt.llm, "ask_json", lambda user, *a, **k: (asked.append(user), next(answers))[1])
    candidates = [{"title": x["c"]["title"], "kind": "paper", "text": x["text"]} for x in PROJECTS]
    out = adapt.adapt(CASE, candidates, [x["cells"] for x in PROJECTS], [0, 1])
    problems = asked[1].split("<problems>")[1]
    assert "[R3] W2: C05" in problems and "for 에서 C05 를 빼라" in problems
    assert "[R14] (선택)" in problems
    assert out["checks"]["passed"] and out["checks"]["rewrote"] == 1
    assert {r["id"]: r["packages"] for r in out["coverage"]} == {"C01": ["W1"], "C02": ["W2"], "C03": ["W3"], "C04": ["W2"],
                                                                 "C05": ["W2"], "C06": []}   # 묶음 칸은 코드가 묶음에서 만든다


def test_project_names_match_without_quote_marks():
    named = copy.deepcopy(PROJECTS)
    named[1]["c"]["title"] = '"comp/y"'
    g = good()
    g["packages"][1]["sources"][0]["project"] = "'comp/y'"
    assert rules(g) == set() and adapt.check(g, CASE, named, adapt.TEAM) == []


@pytest.mark.parametrize("break_it, rule", [
    (lambda g: g["packages"][0]["sources"][0].update(quote="loads the data from many shards quickly"), "R1"),
    (lambda g: g["packages"][0]["sources"][0].update(quote="loads data ... filters images"), "R1"),
    (lambda g: g["packages"][0]["sources"][0].update(project="other/z"), "R2"),
    (lambda g: g["packages"][1]["sources"][0]["for"].append("C05"), "R3"),
    (lambda g: g["packages"][2]["added"].clear(), "R4"),
    (lambda g: g["packages"][0].update(core=False), "R7"),
    (lambda g: g["packages"][0]["sources"][0].update(project=COMP, quote="render scenes in Blender with python scripts"), "R7"),
    (lambda g: g["packages"][1].update(competencies=["C02", "C05"]), "R8"),
    (lambda g: g["coverage"].pop(), "R8"),
    (lambda g: g["packages"][1].update(hours=90), "R5"),
    (lambda g: g["packages"].pop(), "R6"),
    (lambda g: [p.update(sources=[]) for p in g["packages"][3:]], "R9"),
    (lambda g: g["coverage"][5].update(note=" "), "R13"),
    (lambda g: (g["packages"][2].update(competencies=[], added=[]), g["coverage"][2].update(expect="없음", note="")), "R13"),
])
def test_checks_catch_each_fault(break_it, rule):
    g = copy.deepcopy(good())
    break_it(g)
    assert rule in rules(g)


def test_core_hours_over_budget_is_caught():
    assert "R5" in rules(good(), budget=100)


def test_doing_attitude_and_tools_must_be_covered_but_knowledge_may_be_left_out():
    g = good()
    assert adapt.targets(g, CASE) == {"must_cover": "4/4", "knowledge_touched": "1/2", "tools": {"C04": "있음", "C05": "일부"}}
    g["packages"][2]["core"] = False                      # 협업 C03 을 확장으로만 두면 핵심에서 덮지 않는다
    found = adapt.check(g, CASE, PROJECTS, adapt.TEAM)
    assert [x["level"] for x in found if x["rule"] == "R14"] == ["warn"]   # 덮기 목표는 경고만, 다시 쓰게 하지 않는다
    assert adapt.targets(g, CASE)["must_cover"] == "3/4"


def test_alternative_tools_left_out_is_only_a_warning():
    g = good()
    g["packages"][1].update(competencies=["C02", "C04"], added=[])
    g["coverage"][4].update(expect="없음")
    found = adapt.check(g, CASE, PROJECTS, adapt.TEAM)
    assert {(x["rule"], x["level"]) for x in found} == {("R10", "warn"), ("R14", "warn")}


def test_tool_competency_needs_its_name_in_the_package():
    from m2_project import adapt
    case = {"competencies": [{"id": "C1", "name": "React", "type": "도구"}, {"id": "C2", "name": "Go", "type": "도구"},
                             {"id": "C3", "name": "에이전트 툴링 활용", "type": "도구"}]}
    got = {"packages": [{"id": "W1", "name": "CI/CD 파이프라인", "do": "GitHub Actions 로 배포한다", "out": "", "competencies": ["C1", "C3"]},
                        {"id": "W2", "name": "API", "do": "Go 로 게이트웨이를 만든다. Google 인증", "out": "", "competencies": ["C2"]}],
           "coverage": [{"id": "C1", "expect": "있음", "note": ""}, {"id": "C2", "expect": "있음", "note": ""},
                        {"id": "C3", "expect": "있음", "note": ""}]}
    assert adapt.drop_unnamed_tools(got, case) == [("W1", "C1")]
    assert got["packages"][0]["competencies"] == ["C3"] and got["packages"][1]["competencies"] == ["C2"]
    assert [r["expect"] for r in got["coverage"]] == ["없음", "있음", "있음"]


def test_dropped_tool_leaves_no_source_line_behind():
    from m2_project import adapt
    case = {"competencies": [{"id": "C1", "name": "React", "type": "도구"}, {"id": "C2", "name": "배포", "type": "수행"}]}
    got = {"packages": [{"id": "W1", "name": "CI/CD", "do": "배포 자동화", "out": "", "competencies": ["C1", "C2"],
                         "sources": [{"project": "a", "quote": "q", "for": ["C1"]}, {"project": "b", "quote": "q", "for": ["C1", "C2"]}],
                         "added": [{"competency": "C1", "why": "x"}]}],
           "coverage": [{"id": "C1", "expect": "있음", "note": ""}, {"id": "C2", "expect": "있음", "note": ""}]}
    adapt.drop_unnamed_tools(got, case)
    pk = got["packages"][0]
    assert pk["sources"] == [{"project": "b", "quote": "q", "for": ["C2"]}] and pk["added"] == []
