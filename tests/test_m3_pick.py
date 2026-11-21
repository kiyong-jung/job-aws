"""교육자료 고르기: 모델 없이 확인할 수 있는 규칙."""
import m2_project as project
from m3_materials import pick

COMPS = [{"id": "M1", "priority": "필수"}, {"id": "M2", "priority": "필수"},
         {"id": "P1", "priority": "우대"}, {"id": "O1", "priority": "구분없음"}, {"id": "O2", "priority": "구분없음"}]


def cells(**levels):
    return {cid: {"level": lv} for cid, lv in levels.items()}


def test_targets_are_only_tool_and_knowledge_competencies():
    got = pick.targets(project.build_input("naver_ml_intern"))
    assert {c["type"] for c in got} == {"도구", "지식"}
    assert [c["id"] for c in got] == ["C01", "C02", "C04", "C05", "C06", "C19", "C20", "C21", "C22", "C23"]


def test_one_must_competency_beats_all_others():
    many_others = cells(P1="있음", O1="있음", O2="있음")
    one_must = cells(M1="일부")
    picked, _ = pick.choose(COMPS, [many_others, one_must])
    assert picked[0][:2] == (1, "핵심")


def test_second_core_only_when_it_adds_a_must():
    both = [cells(M1="있음"), cells(M2="있음"), cells(P1="있음")]
    assert [r for _, r, _ in pick.choose(COMPS, both)[0]][:2] == ["핵심", "핵심"]
    one = [cells(M1="있음", M2="있음"), cells(P1="있음"), cells(O1="있음")]
    assert [r for _, r, _ in pick.choose(COMPS, one)[0]][:2] == ["핵심", "보조"]


def test_counts_stay_within_limits_even_when_coverage_is_incomplete():
    mats = [cells(M1="일부")] * 3 + [cells(O1="일부")] * 10 + [cells(O2="있음")] * 10
    picked, have = pick.choose(COMPS + [{"id": f"X{i}", "priority": "구분없음"} for i in range(9)], mats)
    roles = [r for _, r, _ in picked]
    assert 1 <= roles.count("핵심") <= 2 and 3 <= roles.count("보조") <= 4
    assert have["M2"] == 0


def test_at_least_three_support_materials_even_with_nothing_left_to_cover():
    mats = [cells(M1="있음", M2="있음", P1="있음", O1="있음", O2="있음")] + [cells()] * 5
    roles = [r for _, r, _ in pick.choose(COMPS, mats)[0]]
    assert roles == ["핵심", "보조", "보조", "보조"]


# 핵심 둘(0, 1) 뒤에 M3 를 일부→있음으로 올리는 2번(+500)과 아직 아무것도 못 덮은 P1·O1·O2·O3 를 덮는 자료 넷이 남는다.
COMPS7 = [{"id": "M1", "priority": "필수"}, {"id": "M2", "priority": "필수"}, {"id": "M3", "priority": "필수"},
          {"id": "P1", "priority": "우대"}, {"id": "O1", "priority": "구분없음"}, {"id": "O2", "priority": "구분없음"},
          {"id": "O3", "priority": "구분없음"}]
MATS7 = [cells(M1="있음", M2="일부", M3="일부"), cells(M2="있음"), cells(M3="있음"),
         cells(P1="일부"), cells(O1="있음"), cells(O2="있음"), cells(O3="있음")]


def test_support_covers_every_coverable_competency_before_upgrading_one():
    picked, have = pick.choose(COMPS7, MATS7)
    assert {cid for cid, v in have.items() if v > 0} == {c["id"] for c in COMPS7}
    assert [r for _, r, _ in picked] == ["핵심", "핵심", "보조", "보조", "보조", "보조"]
    assert 2 not in [i for i, _, _ in picked] and have["M3"] == 0.5


def test_core_choice_ignores_the_new_coverage_rule():
    assert [i for i, r, _ in pick.choose(COMPS7, MATS7)[0] if r == "핵심"] == [0, 1]


def test_bank_merge_keeps_one_per_url_or_same_title_site_summary():
    row = lambda i, url, title="T", summary="s", bank="팀": {"id": i, "bank": bank, "source": "x", "title": title,
                                                             "url": url, "summary": summary}
    kept = pick.merge([row("a", "https://www.ex.com/p/"), row("b", "http://ex.com/p", title="Other", bank="진욱"),
                       row("c", "https://ex.com/q", bank="진욱"), row("d", "https://ex.com/r", summary="other lang")])
    assert [r["id"] for r in kept] == ["a", "d"]


def test_hangul_quote_is_checked_in_place():
    text = "확산 모델의 원리를 수식으로 설명한다 · diffusion"
    assert pick.settle("있음", "원리를 수식으로", text) == ("있음", False)
    assert pick.settle("있음", "없는 구절", text) == ("일부", True)


def test_bank_keeps_only_study_materials():
    """팀 논문·저장소, 에이전트 제품 목록 줄, 진욱의 노트북 없는 폴더 README 는 고를 수 없다. 보강 자료는 남는다."""
    rows, _ = pick.bank()
    assert not [r for r in rows if r["bank"] == "팀" and (r["type"] in ("논문", "저장소")
                                                           or r["source"] in ("ai-agents-list", "ai-agents-2026"))]
    assert not [r for r in rows if r["bank"] == "진욱" and r["type"] == "실습 노트북" and "/tree/" in r["url"]]
    ids = {r["id"] for r in rows}
    # 11/19 AWS 공고에서 뽑혔던 개인 저장소 Llm·AXME·Modus 와 Vite 틀 README
    assert not ids & {"Mf4c1e487db", "Me9c55aed8a", "Md1d0c28ab8", "Ede8144d7b7"}
    kept = {(r["bank"], r["type"]) for r in rows}
    assert {("팀", "학회 튜토리얼"), ("팀", "기술 블로그"), ("진욱", "실습 노트북"), ("진욱", "강의 레슨"),
            ("추가", "저장소")} <= kept
    assert any(r["bank"] == "진욱" and r["type"] == "강의 레슨" and "/tree/" in r["url"] for r in rows)


def test_bank_holds_collected_learning_materials_over_ten_thousand():
    """collect_more.py 가 모은 줄(LRN)은 허용 라이선스이고 노트북 없는 폴더가 아니며, 합친 은행은 1만을 넘는다."""
    rows, _ = pick.bank()
    new = [r for r in rows if r["id"].startswith("LRN")]
    assert len(rows) >= 10_300 and len(new) >= 1_500
    raw = pick.read_csv(pick.ADDITIONS[1])
    assert {r["license"] for r in raw} <= {"MIT", "MIT-0", "Apache-2.0", "BSD-3-Clause", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0"}
    assert not [r for r in raw if r["type"] == "실습 노트북" and "/tree/" in r["url"]]


def test_setup_only_pages_are_not_learning_materials():
    row = lambda title: {"bank": "추가", "type": "실습 노트북", "title": title, "url": "https://x/y.ipynb", "source": "s"}
    assert not pick.teaches(row("Launch Demo Application"))
    assert not pick.teaches(row("migrate: Setup"))
    assert not pick.teaches(row("Prerequisites"))
    assert pick.teaches(row("Evaluate your ADK agent using Vertex AI Gen AI Evaluation service"))
    assert pick.teaches(row("Setting up retrieval evaluation with Ragas metrics"))
