"""프로젝트 샘플 찾기: 모델·네트워크 없이 확인할 수 있는 동작."""
import time
from unittest import mock

import m2_project as project
from m2_project import pick, search


def test_build_input_gives_posting_sentences_and_competencies():
    case = project.build_input("naver_ml_intern")
    assert len(case["sentences"]) == 29 and len(case["competencies"]) == 29
    assert "월드 모델" in search.posting_text(case)


def test_aws_case_reads_its_own_xlsx_run():
    case = project.build_input("aws_fde")
    assert case["posting"]["source"] == "지원/aws 공고.xlsx" and case["posting"]["run"]["run"] == 1
    assert len(case["sentences"]) == 64 and len(case["competencies"]) == 58
    assert sum(pick.tier_of(c) == "필수" for c in case["competencies"]) == 8
    assert "Forward Deployed Engineer II" in search.posting_text(case)


def test_quote_missing_from_text_drops_one_level():
    text = "We filter videos with optical flow and aesthetic scores, then train a model."
    assert pick.settle("있음", "filter videos with optical flow", text) == ("있음", False)
    assert pick.settle("있음", "made-up quote", text) == ("일부", True)
    assert pick.settle("일부", "", text) == ("없음", True)
    assert pick.settle("없음", "", text) == ("없음", False)


def test_search_ranks_results_found_by_several_searches_first(tmp_path):
    case = project.build_input("naver_ml_intern")
    answer = {k: {str(i): f"{k} {i}" for i in range(1, n + 1)} for k, n in search.COUNTS.items()}
    pages = [["https://arxiv.org/abs/2401.00002", "https://arxiv.org/pdf/2402.19479v2"], ["https://arxiv.org/html/2402.19479"]]
    pages += [[]] * sum(search.COUNTS.values())
    paper = lambda aid: {"key": f"arxiv:{aid}", "kind": "paper", "title": aid, "year": "2024", "venue": "", "url": "", "text": ""}  # noqa: E731
    with mock.patch.object(search.llm, "ask_json", return_value=answer), \
         mock.patch.object(search, "web", side_effect=pages), \
         mock.patch.object(search, "arxiv_details", lambda ids: {i: paper(i) for i in ids}), \
         mock.patch.object(search.config, "OUTPUTS", tmp_path):
        out = search.find_candidates(case)
    assert [c["title"] for c in out["candidates"]] == ["2402.19479", "2401.00002"]


def test_key_of_reads_arxiv_and_github_urls():
    assert search.key_of("https://ar5iv.labs.arxiv.org/html/2305.03610") == "arxiv:2305.03610"
    assert search.key_of("https://github.com/Snap-Research/Panda-70M/tree/main") == "gh:snap-research/panda-70m"
    assert search.key_of("https://example.com/x") is None


def test_pick_puts_one_more_must_before_all_preferred():
    case = project.build_input("naver_ml_intern")
    must = next(c for c in case["competencies"] if pick.tier_of(c) == "필수")
    pref = [c["id"] for c in case["competencies"] if pick.tier_of(c) == "우대"]
    cands = [{"kind": "paper", "title": "A", "text": "we do preferred things a b c"},
             {"kind": "paper", "title": "B", "text": "we do the duty thing"}]
    answer = {"items": [{"n": 1, "coverage": [{"cid": c, "level": "있음", "quote": "preferred things"} for c in pref]},
                        {"n": 2, "coverage": [{"cid": must["id"], "level": "있음", "quote": "the duty thing"}]}]}
    with mock.patch.object(pick.llm, "ask_json", return_value=answer):
        out = pick.pick_best(case, cands)
    assert out["sample"]["title"] == "B"   # 필수 하나가 우대 전부보다 앞선다
    assert [(x["cid"], x["level"], x["priority"]) for x in out["coverage"]] == [(must["id"], "있음", "필수")]
    assert out["must_all"] is False and must["name"] not in out["must_missing"]


def test_brave_stops_when_month_budget_is_used(tmp_path):
    log = tmp_path / "brave.tsv"
    log.write_text(time.strftime("%Y-%m") + "-01T00:00:00\tq\n")
    with mock.patch.object(search, "BRAVE_LOG", log), mock.patch.object(search, "BRAVE_MONTHLY", 1), \
         mock.patch.object(search, "get", side_effect=AssertionError("부르면 안 된다")):
        try:
            search.brave("x")
        except RuntimeError as e:
            assert "다 썼다" in str(e)
        else:
            raise AssertionError("멈추지 않았다")


def test_local_rank_puts_bank_items_matching_several_queries_first():
    from m2_project import local
    bank = [{"kind": "paper", "title": "Video dataset curation", "text": "filter video clips by quality"},
            {"kind": "paper", "title": "Protein folding", "text": "predict protein structure"},
            {"kind": "paper", "title": "Image captioning", "text": "caption images with a vision language model"},
            {"kind": "repo", "title": "org/video-filter", "text": "video quality filter"},
            {"kind": "repo", "title": "org/web-server", "text": "fast http server"},
            {"kind": "repo", "title": "org/db", "text": "key value store"}]
    score = local.rank(local.build(bank), {"paper": ["video dataset filtering", "video quality"], "repo": ["video filter"]})
    assert max(score, key=score.get) == 0 and 1 not in score and score[3] == 1   # 저장소 검색어는 저장소에서만 센다


def test_local_fit_keeps_candidates_covering_every_must_or_ties_for_best():
    from m2_project import local
    case = project.build_input("naver_ml_intern")
    need = sum(local.tier_of(c) == "필수" for c in case["competencies"])
    assert [r["title"] for r in local.fit([{"title": "A", "필수": need}, {"title": "B", "필수": need - 0.5}], case)] == ["A"]
    assert [r["title"] for r in local.fit([{"title": "A", "필수": 3}, {"title": "B", "필수": 3}, {"title": "C", "필수": 2}], case)] == ["A", "B"]
