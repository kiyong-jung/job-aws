"""m1_competency: 공고 수집기 파서와 공고 줄. 네트워크 없이 작은 HTML·JSON 조각을 web.polite_get 자리에 끼워 넣는다."""
import json

import pytest

from m1_competency import collect
from shared import schema, web

def fake_get(pages):
    def get(url, data=None, headers=None):
        if url not in pages:
            raise AssertionError(f"예상 밖의 주소 {url}")
        return pages[url] if isinstance(pages[url], str) else json.dumps(pages[url])
    return get



def test_html_text_keeps_headers_and_list_lines():
    text = web.html_text(
        "<p><strong>자격요건</strong></p><ul><li><p>Python 3년</p></li><li>R&amp;D 경험</li></ul><h3>우대사항</h3>PyTorch<br>끝")
    assert text.splitlines() == ["자격요건", "- Python 3년", "- R&D 경험", "우대사항", "PyTorch", "끝"]



def test_html_text_unescapes_greenhouse_double_escaped_content():
    assert web.html_text("&lt;p&gt;우리는&lt;/p&gt;&lt;ul&gt;&lt;li&gt;모델&lt;/li&gt;&lt;/ul&gt;") == "우리는\n- 모델"



def test_is_ai_role():
    assert collect.is_ai_role("Machine Learning Engineer", "")
    assert collect.is_ai_role("LLM연구 인턴", "")
    assert collect.is_ai_role("데이터 엔지니어", "")
    assert not collect.is_ai_role("AI 서비스 마케팅 매니저", "")
    assert not collect.is_ai_role("서버 개발자", "광고 서버를 만든다")
    assert collect.is_ai_role("서버 개발자", "머신러닝 추천 모델을 서빙한다. PyTorch, 딥러닝, MLOps 경험")



def test_dedup_by_url_and_body():
    a = {"url": "u1", "text": "같은 본문, 같은 글!"}
    rows = [a, {"url": "u1", "text": "다른 글"}, {"url": "u2", "text": "같은 본문 같은 글"}, {"url": "u3", "text": "새 글"}]
    assert [p["url"] for p in collect.dedup(rows)] == ["u1", "u3"]



def test_greenhouse_and_location_filter(monkeypatch):
    jobs = {"jobs": [
        {"title": "ML Engineer", "absolute_url": "https://x.io/1", "location": {"name": "Seoul, South Korea"},
         "updated_at": "2026-11-01T01:00:00-05:00",
         "content": "&lt;p&gt;" + "머신러닝 모델을 만든다. " * 12 + "&lt;/p&gt;"},
        {"title": "ML Engineer", "absolute_url": "https://x.io/2", "location": {"name": "Tokyo, Japan"},
         "updated_at": "2026-11-01", "content": "<p>" + "x " * 100 + "</p>"},
    ]}
    monkeypatch.setattr(web, "polite_get",
                        fake_get({"https://boards-api.greenhouse.io/v1/boards/x/jobs?content=true": jobs}))
    posts, st = collect.collect_company({"company": "X", "method": "api", "ats": "greenhouse", "token": "x"},
                                        "2026-11-14T00:00")
    assert (st["found"], st["kept"]) == (2, 1)
    p = posts[0]
    assert p["id"] == schema.stable_id("K",
                                       "https://x.io/1") and p["updated"] == "2026-11-01" and p["source"] == "api:x.io"
    assert schema.validate("postings", p) == []



def test_greeting_reads_sitemap_and_next_data(monkeypatch):
    def page(status, title, detail):
        q = {"queryKey": ["career", "getOpeningById"],
             "state": {"data": {"data": {"openingsInfo": {"status": status, "title": title, "detail": detail,
                                                          "openDate": "2026-05-18T23:21:00Z"}}}}}
        data = {"props": {"pageProps": {"dehydratedState": {"queries": [{"queryKey": ["a", "b"],
                                                                         "state": {"data": None}}, q]}}}}
        return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
    base = "https://acme.career.greetinghr.com"
    monkeypatch.setattr(web, "polite_get", fake_get({
        f"{base}/sitemap.xml": "<loc>https://acme.career.greetinghr.com/o/1</loc><loc>https://acme.career.greetinghr.com/o/2</loc><loc>https://acme.career.greetinghr.com/o/1</loc>",
        f"{base}/o/1": page("OPEN", "AI Research Engineer", "<p>" + "딥러닝 연구 " * 30 + "</p>"),
        f"{base}/o/2": page("CLOSED", "AI Researcher", "<p>마감</p>"),
    }))
    got = list(collect.from_greeting({"token": "acme"}))
    assert [g["url"] for g in got] == [f"{base}/o/1"] and got[0]["updated"] == "2026-05-18"



def test_image_and_thin_bodies_are_skipped_and_counted(monkeypatch):
    jobs = {"jobs": [
        {"title": "AI Engineer", "absolute_url": "https://x.io/img", "location": {"name": "Seoul"}, "updated_at": "",
         "content": '<img src="a.png">'},
        {"title": "AI Engineer", "absolute_url": "https://x.io/thin", "location": {"name": "Seoul"}, "updated_at": "",
         "content": "<p>짧다</p>"},
    ]}
    monkeypatch.setattr(web, "polite_get",
                        fake_get({"https://boards-api.greenhouse.io/v1/boards/x/jobs?content=true": jobs}))
    posts, st = collect.collect_company({"company": "X", "method": "api", "ats": "greenhouse", "token": "x"}, "t")
    assert posts == [] and (st["image"], st["thin"]) == (1, 1)



def test_kakao_builds_body_from_sections(monkeypatch):
    job = {"realId": "S-1", "companyName": "카카오", "jobOfferTitle": "LLM Research Engineer",
           "regDate": "2026-11-06T16:30:22",
           "introduction": "◆ 조직소개<br/>" + "연구 " * 40, "workContentDesc": "-", "qualification": "- 석사 이상<br/>- Python",
           "jobOfferProcessDesc": ""}
    monkeypatch.setattr(web, "polite_get",
                        fake_get({
                            "https://careers.kakao.com/public/api/job-list?skillSet=&part=TECHNOLOGY&company=ALL&keyword=&employeeType=&page=1":
                                {"jobList": [job], "totalPage": 1}}))
    (p,) = list(collect.from_kakao({}))
    assert p["url"] == "https://careers.kakao.com/jobs/S-1" and p["company"] == "카카오" and p["updated"] == "2026-11-06"
    assert "자격요건\n- 석사 이상\n- Python" in web.html_text(p["html"]) and "업무내용" not in p["html"]



def test_robots_block_is_a_failure_not_a_crash(monkeypatch):
    def blocked(url, data=None, headers=None):
        raise web.Skipped("robots.txt 가 막음: " + url)
    monkeypatch.setattr(web, "polite_get", blocked)
    posts, st = collect.collect_company({"company": "X", "method": "api", "ats": "greenhouse", "token": "x"}, "t")
    assert posts == [] and st["failures"][0].startswith("robots")



def test_robots_fetch_failure_is_reported_as_unverified_not_as_blocked(monkeypatch):
    import ssl
    sent = []

    def urlopen(req, timeout=0):
        sent.append(req.full_url)
        raise ssl.SSLCertVerificationError("certificate verify failed")
    monkeypatch.setattr(web.urllib.request, "urlopen", urlopen)
    web._robots.clear()
    with pytest.raises(web.Skipped) as e:
        web.polite_get("https://career.example.com/jobs/1")
    assert "확인하지 못" in str(e.value) and "막음" not in str(e.value)
    assert sent == ["https://career.example.com/robots.txt"]



def test_robots_rules_are_obeyed(monkeypatch):
    class R:
        def __init__(self, body):
            self.body = body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return self.body
    monkeypatch.setattr(web.urllib.request, "urlopen", lambda req, timeout=0: R("User-agent: *\nDisallow: /w1/\n"))
    web._robots.clear()
    assert web.allowed("https://career.example.com/jobs/1")
    assert not web.allowed("https://career.example.com/w1/recruits")
    with pytest.raises(web.Skipped):
        web.polite_get("https://career.example.com/w1/recruits")



def test_robots_server_error_blocks_the_site_and_a_missing_file_allows_it(monkeypatch):
    import io
    import urllib.error
    sent = []

    def urlopen(req, timeout=0):
        sent.append(req.full_url)
        code = 503 if "down." in req.full_url else 404
        raise urllib.error.HTTPError(req.full_url, code, "x", {}, io.BytesIO(b""))
    monkeypatch.setattr(web.urllib.request, "urlopen", urlopen)
    web._robots.clear()
    with pytest.raises(web.Skipped) as e:
        web.polite_get("https://down.example.com/jobs/1")
    assert "확인하지 못" in str(e.value) and sent == ["https://down.example.com/robots.txt"]
    assert web.allowed("https://gone.example.com/jobs/1")      # 4xx 는 규칙이 없는 것 (RFC 9309)



def test_hand_fixed_posting_line_wins_over_rules(tmp_db):
    p = collect.from_text("테스트", "[자격 요건]\n- Python 실무 경험이 있는 분\n[우대 사항]\n- AWS 운영 경험 우대")
    assert p["id"] == collect.from_text("다른 제목", p["text"])["id"]
    collect.save_posting(p)
    first = schema.read("posting_lines")
    assert [(x["tier"], x["method"]) for x in first] == [("필수", "규칙"), ("우대", "규칙")]
    schema.write("posting_lines", [{**first[1], "tier": "필수", "importance": "상", "method": "사람"}])
    collect.save_posting(p)
    assert [x["tier"] for x in collect.lines(p)] == ["필수", "필수"]


def test_fetch_replaces_only_the_fetched_batch_and_keeps_the_file_order(tmp_path, monkeypatch):
    old = [("kr_a", "A1"), ("kr_b", "B1"), ("kr_b", "B2"), ("others_ai", "O1")]
    (tmp_path / "postings.jsonl").write_text("".join(json.dumps({"batch": b, "id": i}) + "\n" for b, i in old),
                                             encoding="utf-8")
    (tmp_path / "companies.json").write_text(json.dumps([{"key": "b", "batch": "b"}]), encoding="utf-8")
    monkeypatch.setattr(collect, "POSTINGS", tmp_path / "postings.jsonl")
    monkeypatch.setattr(collect.config, "COMPETENCY_DATA", tmp_path)
    stats = {"company": "b", "method": "api", "found": 1, "kept": 1, "final": 0, "thin": 0, "image": 0, "failures": []}
    monkeypatch.setattr(collect, "collect_company", lambda c, now: ([{"id": "B3", "url": "u", "text": "본문"}], stats))
    collect.fetch()
    assert [(p["batch"], p["id"]) for p in collect.snapshots()] == [("kr_a", "A1"), ("kr_b", "B3"), ("others_ai", "O1")]
