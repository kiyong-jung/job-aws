"""demo/ (공고 → 역량 화면) 시험. 돈이 드는 호출과 바깥 네트워크는 쓰지 않는다."""
import http.client
import io
import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from demo import fetch, pipeline, server

PUBLIC_IP = "93.184.215.14"
NAVER = "naver_ml_intern"      # 저장본이 모두 있는 예시 공고 (아래 시험 대부분이 이것으로 돈다)


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """이름 풀기를 바깥에 묻지 않는다. 'internal' 이 들어간 이름만 사설 주소로, 나머지는 공인 주소로 푼다."""
    def getaddrinfo(host, port, *a, **k):
        try:
            ip = str(fetch.ipaddress.ip_address(host))      # 숫자 주소는 그대로
        except ValueError:
            ip = "10.0.0.5" if "internal" in host else "127.0.0.1" if host == "localhost" else PUBLIC_IP
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
    monkeypatch.setattr(fetch.socket, "getaddrinfo", getaddrinfo)


@pytest.fixture
def live_server():
    srv = server.serve("127.0.0.1", 0, False, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _post(port, body, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.putrequest("POST", "/api/run")
    for k, v in {"Content-Type": "application/json", **(headers or {})}.items():
        conn.putheader(k, v)
    own_length = "Content-Length" not in (headers or {})      # 머리줄을 꾸밀 때는 몸통을 보내지 않는다
    if own_length:
        conn.putheader("Content-Length", str(len(body)))
    conn.endheaders()
    if own_length and body:
        conn.send(body)
    res = conn.getresponse()
    out = res.status, res.read()
    conn.close()
    return out


def test_highlights_and_rows_share_numbers():
    case = pipeline.example_case(NAVER)
    marks, rows = pipeline.plan(case["sentences"], case["competencies"])
    number = {m["sid"]: m["n"] for m in marks}
    order = [s["id"] for s in case["sentences"]]
    # 번호는 공고 순서대로 1부터, 형광펜 하나에 줄이 하나 이상, 줄마다 근거 문장의 번호를 단다
    assert [m["n"] for m in marks] == list(range(1, len(marks) + 1))
    assert [m["sid"] for m in marks] == sorted(number, key=order.index)
    assert len(rows) == len(case["competencies"])
    for r in rows:
        assert r["badges"] == [number[s] for s in r["sids"]]
    assert {n for r in rows for n in r["badges"]} == set(number.values())
    assert [r["badges"][0] for r in rows] == sorted(r["badges"][0] for r in rows)


def test_row_with_two_evidence_sentences_gets_two_badges():
    sentences = [{"id": f"S0{i}", "section": "자격요건", "text": f"문장 {i}."} for i in range(1, 5)]
    comps = [{"id": "C1", "name": "가", "type": "지식", "priority": "필수", "evidence_id": "S03, S02"},
             {"id": "C2", "name": "나", "type": "도구", "priority": "우대", "evidence_id": "S04"},
             {"id": "C3", "name": "다", "type": "수행", "priority": "필수", "evidence_id": "S99"}]   # 공고에 없는 근거
    marks, rows = pipeline.plan(sentences, comps)
    assert marks == [{"sid": "S02", "n": 1}, {"sid": "S03", "n": 2}, {"sid": "S04", "n": 3}]
    assert [(r["id"], r["badges"]) for r in rows] == [("C1", [1, 2]), ("C2", [3])]


def test_pasted_example_replays_saved_result():
    case = pipeline.example_case(NAVER)
    text = pipeline.posting_text(case)
    assert pipeline.matches(text, case)
    assert pipeline.matches(" ".join(text.split()), case)          # 줄바꿈이 사라진 붙여넣기도 같은 공고
    assert not pipeline.matches("데이터 엔지니어를 찾습니다.\n자격요건\n- SQL 활용 경험", case)
    events = list(server.events({"text": text, "speed": 0}, live_mode=False, default_speed=0))
    kinds = [e["type"] for e in events]
    assert kinds.count("highlight") == len(pipeline.plan(case["sentences"], case["competencies"])[0])
    assert kinds.count("row") == len(case["competencies"])
    assert kinds[-1] == "done" and "posting" in kinds
    assert [e["key"] for e in events if e["type"] == "stage"] == ["read", "split", "find", "sort"]
    posting = next(e for e in events if e["type"] == "posting")
    assert posting["replay"] is True      # 화면이 "미리 돌려 둔 결과를 다시 보여 드려요" 라고 적는다
    assert posting["adapted"] == bool(pipeline.adapt_case(NAVER))      # ③ 쪽 이름("응용")을 처음부터 알 수 있게
    assert "delta" not in kinds      # 대화 칸이 없다: 화면 글은 바닥 줄 불렛 둘뿐 (사용자 11/19)


@pytest.mark.parametrize("name", [NAVER, "aws_fde"])
def test_highlights_are_painted_a_few_at_a_time_within_one_and_a_half_seconds(name, monkeypatch):
    """사용자 11/19: 형광펜은 몇 줄씩 함께, 1.5초 안에 다 칠한다. 마지막 묶음이 오는 때 + 칠하기 전환(--t-paint 300ms) ≤ 1.5초"""
    slept = []
    monkeypatch.setattr(pipeline.time, "sleep", slept.append)
    case = pipeline.example_case(name)
    events = list(pipeline.replay(case, speed=1.0))
    assert sum(e["type"] == "highlight" for e in events) > pipeline.WAVES      # 한 번에 여러 줄
    assert slept.count(pipeline.PACE["wave"]) == pipeline.WAVES - 1      # 묶음 넷, 묶음 사이 잠 셋
    assert pipeline.PACE["wave"] * (pipeline.WAVES - 1) + 0.3 <= 1.5


def test_new_posting_offline_shows_text_without_developer_words():
    text = "데이터 엔지니어\n자격요건\n- SQL 로 데이터를 다룰 수 있는 분\n- 파이프라인 운영 경험이 있는 분"
    events = list(server.events({"text": text}, live_mode=False, default_speed=0))
    assert events[-1]["type"] == "notice" and "예시 공고만" in events[-1]["text"]
    assert not any(w in events[-1]["text"] for w in ("--live", "서버", "비용"))      # 화면에 개발자 말을 내지 않는다
    assert any(e["type"] == "posting" for e in events)
    assert not any(e["type"] == "highlight" for e in events)


def test_live_mode_wires_split_and_extract(tmp_path, monkeypatch):
    from m1_competency import competencies
    from shared import schema
    monkeypatch.setattr(schema, "DIR", tmp_path)          # 공고 줄 표를 빈 임시 폴더에서 읽는다

    def no_llm(*a, **k):
        raise AssertionError("머리줄이 있는 공고는 모델 없이 나눠야 한다")
    monkeypatch.setattr(competencies, "_refine_llm", no_llm)
    text = "데이터 엔지니어\n자격요건\n- SQL 로 데이터를 다룰 수 있는 분\n우대사항\n- Airflow 사용 경험"
    seen = {}

    def fake_extract(posting):
        from m1_competency import collect
        lines = collect.lines(posting)
        seen["lines"] = lines
        return [{"cid": "X-C01", "name": "SQL 데이터 처리", "type": "수행", "priority": "필수", "basis": "명시",
                 "evidence_id": lines[0]["line_id"], "reason": ""},
                {"cid": "X-C02", "name": "Airflow", "type": "도구", "priority": "우대", "basis": "명시",
                 "evidence_id": lines[1]["line_id"], "reason": ""}]

    events = list(pipeline.live(text, "데이터 엔지니어", speed=0, extract=fake_extract))
    posting = next(e for e in events if e["type"] == "posting")
    assert [s["name"] for s in posting["sections"]] == ["자격요건", "우대사항"] and not posting.get("replay")      # 실제로 돌린 결과
    rows = [e["row"] for e in events if e["type"] == "row"]
    assert [(r["id"], r["badges"]) for r in rows] == [("X-C01", [1]), ("X-C02", [2])]
    assert events[-2] == {"type": "done", "rows": 2, "marks": 2, "required": 1, "preferred": 1}
    handoff = events[-1]      # 다음 단계(demo/live.py)가 쓸 공고 한 건: 화면이 들고 있다가 단계 요청에 싣는다
    assert handoff["type"] == "live_state" and handoff["key"] == "case"
    assert [c["id"] for c in handoff["value"]["competencies"]] == ["X-C01", "X-C02"] and len(handoff["value"]["sentences"]) >= 2


def test_fetch_stops_at_robots_disallow(monkeypatch):
    asked = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        asked.append(url)
        if url.endswith("/robots.txt"):
            return io.BytesIO(b"User-agent: *\nDisallow: /jobs/\n")
        raise AssertionError("robots 가 막은 쪽을 열면 안 된다")

    monkeypatch.setattr(fetch._OPENER, "open", fake_urlopen)
    with pytest.raises(fetch.Blocked) as e:
        fetch.fetch("https://jobs.example.com/jobs/123")
    assert e.value.reason == "robots"
    assert asked == ["https://jobs.example.com/robots.txt"]
    events = list(server.events({"url": "https://jobs.example.com/jobs/123"}, live_mode=False, default_speed=0))
    assert events[-1]["type"] == "error" and "붙여넣어" in events[-1]["message"]


def test_robots_server_error_counts_as_blocked(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)

    monkeypatch.setattr(fetch._OPENER, "open", fake_urlopen)
    with pytest.raises(fetch.Blocked) as e:
        fetch.fetch("https://jobs.example.com/jobs/1")
    assert e.value.reason == "robots_unknown"


def test_fetch_refuses_private_and_loopback_hosts(monkeypatch):
    def no_network(req, timeout=None):
        raise AssertionError("내부 주소로는 아무 요청도 나가면 안 된다")
    monkeypatch.setattr(fetch._OPENER, "open", no_network)
    for url in ("https://127.0.0.1/jobs/1", "https://localhost/jobs/1", "https://169.254.169.254/latest/meta-data",
                "https://jobs.internal.example/1", "https://[::1]/x"):
        with pytest.raises(fetch.Blocked) as e:
            fetch.fetch(url)
        assert e.value.reason == "private", url
    with pytest.raises(fetch.Blocked) as e:
        fetch.fetch("http://jobs.example.com/1")      # https 만 받는다
    assert e.value.reason == "address"
    events = list(server.events({"url": "https://127.0.0.1/"}, live_mode=False, default_speed=0))
    assert events[-1]["type"] == "error" and events[-1]["reason"] == "private"


def test_fetch_checks_every_redirect_hop():
    handler = fetch._CheckRedirect()
    req = urllib.request.Request("https://jobs.example.com/1")
    with pytest.raises(fetch.Blocked) as e:
        handler.redirect_request(req, None, 302, "Found", {}, "https://10.1.2.3/admin")
    assert e.value.reason == "private"
    with pytest.raises(fetch.Blocked):
        handler.redirect_request(req, None, 302, "Found", {}, "http://jobs.example.com/plain")
    assert handler.redirect_request(req, None, 302, "Found", {}, "https://jobs.example.com/2").full_url == "https://jobs.example.com/2"


def test_server_refuses_oversized_body(live_server):
    status, _ = _post(live_server, b"", {"Content-Length": str(server.MAX_BODY + 1)})
    assert status == 413
    status, _ = _post(live_server, b"{}", {"Content-Length": "-5"})
    assert status == 413
    status, _ = _post(live_server, b"{}", {"Content-Length": "abc"})
    assert status == 400


def test_server_refuses_json_that_is_not_an_object(live_server):
    for body in (b"[1, 2]", b'"text"', b"42", b"null", b"{broken"):
        status, _ = _post(live_server, body)
        assert status == 400, body
    status, data = _post(live_server, json.dumps({"text": "짧음"}).encode())
    assert status == 200 and b'"reason": "short"' in data


def test_static_paths_stay_inside_static(live_server):
    def get(path):
        conn = http.client.HTTPConnection("127.0.0.1", live_server, timeout=10)
        conn.request("GET", path)
        res = conn.getresponse()
        res.read()
        conn.close()
        return res.status
    assert get("/") == 200 and get("/static/css/tokens.css") == 200
    for path in ("/static/../server.py", "/static/../../tests/test_demo.py", "/static//etc/passwd",
                 "/static/%2e%2e/server.py", "/server.py", "/../demo/server.py"):
        assert get(path) == 404, path


def test_page_is_landing_and_dashboard_without_chat(live_server):
    """사용자 11/19: 대화 칸 없이 시작 화면(공고 넣기)과 대시보드(쪽 더미)만. 쪽마다 그림 칸과 바닥 줄 하나"""
    conn = http.client.HTTPConnection("127.0.0.1", live_server, timeout=10)
    conn.request("GET", "/")
    page = conn.getresponse().read().decode()
    conn.close()
    assert 'id="thread"' not in page and 'id="chat"' not in page and 'id="views"' not in page and "chat.css" not in page
    landing = page[page.index('<section class="landing"'):page.index("</section>", page.index('<section class="landing"'))]
    assert 'id="composer"' in landing and 'id="starters"' in landing
    keys = ("posting", "search", "materials", "weeks", "report")      # ② 는 최종 응용 하나 (1위·응용 쪽을 따로 두지 않는다)
    assert [page.count(f'data-view="{k}"') for k in keys] == [1] * 5 and 'data-view="sample"' not in page
    assert [page.count(f'id="foot-{k}"') for k in keys] == [1] * 5
    brand = page[page.index('<div class="brand">'):page.index("</div>", page.index('<div class="brand">'))]
    assert 'id="new-chat"' in brand and 'aria-label="JOB AWS 새 공고"' in brand and "<button" in brand


def test_project_step_replays_saved_search_with_real_numbers():
    """숫자는 모두 저장본에서 읽는다 (후보 수, 묶음 수, 만점, 덮기 셈을 박아 두지 않는다)."""
    case = pipeline.example_case(NAVER)
    data = pipeline.project_case(NAVER)
    c, scores, cov = data["counts"], data["scores"], data["coverage"]
    n = len(scores)
    events = list(server.events({"step": "project", "text": pipeline.posting_text(case)}, live_mode=False, default_speed=0))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "steps" and kinds[-1] == "done"
    steps = events[0]["items"]
    adapted = pipeline.adapt_case(NAVER)      # 응용 프로젝트 (m2_project/adapt.py 결과)가 저장본에 있으면 두 단계가 더 붙는다
    keys = ["search", "scan", "rerank", "judge", "pick"] + (["borrow", "merge"] if adapted else [])
    assert [e["key"] for e in events if e["type"] == "stage"] == [s["key"] for s in steps] == keys
    # 패널 그림의 숫자는 저장본 그대로: DB 크기, 낱말로 모은 후보, 다시 고른 후보, 판정 묶음(5개씩)과 그 점수
    assert events[0]["db"] == {"papers": c["papers"], "repos": c["repos"], "total": c["papers"] + c["repos"]} and events[0]["pool"] == c["pool"]
    assert events[0]["shortlist"] == n == c["judged"] == c["shortlist"]
    assert events[0]["seconds"] == data["seconds"]      # 실제로 걸린 시간이 저장본에 없으면 None (화면이 지어내지 않는다)
    judged = [e for e in events if e["type"] == "judged"]
    assert len(judged) == -(-n // pipeline.BATCH) and all(len(e["scores"]) <= pipeline.BATCH for e in judged)
    assert [e["n"] for e in judged] == [min(i + pipeline.BATCH, n) for i in range(0, n, pipeline.BATCH)]
    # 묶음은 순위와 상관없는 정해 둔 차례로 온다: 순위 번호를 한 번씩, 점수는 그 순위의 저장본 점수, 1위는 앞 묶음에 없다
    ranks = [r for e in judged for r in e["ranks"]]
    assert sorted(ranks) == list(range(n))
    assert all(e["scores"] == [scores[r] for r in e["ranks"]] for e in judged)
    assert ranks.index(0) >= n // 4
    for size in (100, 200, 37):      # 후보 수가 달라도 순열이고 1위는 한가운데
        order = pipeline.judge_order(size)
        assert sorted(order) == list(range(size)) and order.index(0) == size // 2 + 1
    stages = {e["key"]: i for i, e in enumerate(events) if e["type"] == "stage"}
    assert all(stages["judge"] < events.index(e) < stages["pick"] for e in judged)      # 견주는 단계 안에서
    pick = next(e for e in events if e["type"] == "stage" and e["key"] == "pick")
    first = pipeline.TIERS[0]
    assert scores[pick["top"]] == max(scores) == data["ranking"][0][first]
    # 최종 순위는 서버가 싣는다 (저장본의 차례 = 필수 → 우대 → 나머지 순위). 필수를 다 다룬 후보 수도 저장본에서 센다
    assert pick["order"] == list(range(n)) and pick["full"] == sum(x == max(scores) for x in scores if x == sum(pipeline.tier_of(c) == first for c in cov))
    rank = [[r[t] for t in pipeline.TIERS] for r in data["ranking"]]
    assert rank == sorted(rank, reverse=True)
    shown = " ".join(s["label"] + s["done"] for s in steps)
    for k, unit in ((c["papers"], "편"), (c["repos"], "개"), (c["pool"], "개"), (c["shortlist"], "개")):
        assert f"{k:,}{unit}" in shown
    assert steps[4]["done"] == "필수를 가장 많이 다루는 1위를 골랐어요"      # 기준을 넘긴 게 아니라 1등을 골랐다. "점수 1위" 라고 하지 않는다 (순위는 필수 먼저)
    assert "점수 1위" not in shown and events[0]["adapted"] == bool(adapted)
    assert all(s["label"].endswith("중") and s["done"].endswith("요") for s in steps)
    assert "DB" in steps[0]["label"] and "DB" in steps[0]["done"]      # 하는 중과 끝난 말이 같은 일
    found = next(e for e in events if e["type"] == "project")
    assert found["sample"]["title"] == data["sample"]["title"] == found["ranking"][0]["title"]
    # 단계는 역량의 필수·우대 표시로 가른다 (둘 다 아니면 나머지). 만점은 저장본에서 센 수
    totals = [sum(pipeline.tier_of(x) == t for x in cov) for t in pipeline.TIERS]
    assert [t["name"] for t in found["tiers"]] == list(pipeline.TIERS) == ["필수", "우대", "나머지"]
    assert [t["total"] for t in found["tiers"]] == totals and sum(totals) == len(cov)
    assert found["ranking"][0]["scores"] == [data["ranking"][0][t] for t in pipeline.TIERS]      # 화면 맨 위 한 줄 "N점 중 M점" 의 숫자
    assert found["judged"] == c["judged"]
    # 샘플 글: 저장소는 판정이 읽은 소개 글(README)에서 근거 구절이 든 곳만 보인다 (저장본의 readme_shown: 다듬은 글에서 잘라 낸 조각들).
    # 근거 구절이 있는 역량은 모두 구절로 잡힌다
    sample = data["sample"]
    body = sample.get("readme_shown") or (pipeline.tidy(sample["readme"]) if sample.get("readme") else sample["text"])
    shown_text = "".join(p["text"] for p in found["sample"]["parts"])
    assert shown_text == pipeline.unbreak(body) and found["sample"]["cut"] == bool(sample.get("readme_shown"))
    if sample.get("readme_shown"):      # 잘라 낸 조각은 모두 다듬은 소개 글에 그대로 있고, 훨씬 짧다
        whole = pipeline.tidy(sample["readme"])
        pieces = [x for para in sample["readme_shown"].split("\n\n") for x in para.split(" … ")]
        assert all(piece.strip("… ") in whole for piece in pieces) and len(sample["readme_shown"]) < len(whole) / 2
        # 제목·배지·표 머리가 풀린 낱말은 뺐다 (근거 구절 앞에 붙어 있던 것)
        assert not any(x in sample["readme_shown"] for x in ("Star History", "= Rust Accelerated", "Loader Description Features"))
    assert {x for p in found["sample"]["parts"] for x in p.get("cids", [])} == {x["cid"] for x in cov if x["quote"]}
    assert not pipeline.EMOJI.search(shown_text) and "Install & run:" not in shown_text
    assert "delta" not in kinds      # 대화 칸이 없다 (사용자 11/19): 화면 글은 바닥 줄 불렛 둘
    assert [r["decided"] for r in found["ranking"]] == [0] + [next(k for k in range(3) if rank[i][k] != rank[i - 1][k]) for i in range(1, len(rank))]
    assert kinds.index("project") < kinds.index("cover")      # 화면은 샘플(구절)을 덮기 표 줄보다 먼저 그린다
    # 덮기 표: 역량마다 한 줄, 역량 표와 같은 순서·같은 문장 번호 (화면이 같은 형광펜과 짝짓는다)
    _, rows = pipeline.plan(case["sentences"], case["competencies"])
    cover = [e["row"] for e in events if e["type"] == "cover"]
    assert [(r["id"], r["badges"]) for r in cover] == [(r["id"], r["badges"]) for r in rows]
    levels = {k: sum(x["level"] == k for x in cov) for k in ("있음", "일부", "없음")}
    assert events[-1]["levels"] == levels == data["levels"]
    assert all(r["tier"] == pipeline.tier_of(x) for r, x in zip(sorted(cover, key=lambda r: r["id"]), sorted(cov, key=lambda x: x["cid"])))
    if not adapted:
        return
    # 응용 프로젝트: cover 뒤에 adapt 한 번, 바뀌는 칸마다 fill 한 번. 셈은 있음 1, 일부 0.5 (발표 자료와 같다)
    assert kinds.index("cover") < kinds.index("adapt") < kinds.index("fill") and kinds.count("adapt") == 1
    plan_ = next(e for e in events if e["type"] == "adapt")
    assert plan_["base"]["title"] == data["sample"]["title"] == adapted["base"]["title"] and (plan_["title"], plan_["goal"]) == (adapted["title"], adapted["goal"])
    assert [x["short"] for x in plan_["parts"]] == ["dingo", "UrbanScene3D", "Goku"] and all(x["url"].startswith("https://") for x in plan_["parts"])
    assert [(x["name"], x["hours"], x["core"]) for x in plan_["packages"]] == [(q["name"], q["hours"], q["core"]) for q in adapted["packages"]]
    assert plan_["packages"][0]["from"] == ["바탕", "Goku", "AI가 더함"] and plan_["packages"][-1] == {**plan_["packages"][-1], "core": False, "from": ["바탕"]}
    assert (plan_["hours"]["core"], plan_["hours"]["total"], plan_["hours"]["budget"]) == (288, 304, 336) == (sum(q["hours"] for q in adapted["packages"] if q["core"]), sum(q["hours"] for q in adapted["packages"]), 336)
    # 처음 수는 1위 판정 (있음 9 + 일부 3 → 10.5), 끝 수는 응용 뒤 덮기 표 (있음 26 + 일부 1 → 26.5)
    fills = [e for e in events if e["type"] == "fill"]
    level = {x["cid"]: x["level"] for x in cov}
    after = {x["id"]: x["expect"] for x in adapted["coverage"]}
    assert plan_["before"] == events[-1]["before"] == 10.5 and events[-1]["after"] == fills[-1]["count"] == 26.5
    assert [e["id"] for e in fills] == [k for k in after if after[k] != level[k]] and all(e["level"] == after[e["id"]] for e in fills)
    assert all(e["by"] in ("base", "new", 1, 2, 3) for e in fills) and [x["fills"] for x in plan_["parts"]] == [sum(e["by"] == n for e in fills) for n in (1, 2, 3)]
    assert plan_["added"] == sum(e["by"] == "new" for e in fills) and {e["id"] for e in fills if e["by"] == "new"} >= {"C21", "C24", "C25", "C26"}
    # 프로젝트로 다 못 배우는 역량 셋 (교육자료에서 습득)
    assert [(x["name"], x["level"]) for x in plan_["uncovered"]] == [("Isaac Sim", "없음"), ("Omniverse", "없음"), ("Unreal Engine", "일부")]
    assert plan_["status"] == "AI가 미리 만든 결과를 다시 보여 드려요"
    assert (events[-1]["before"], events[-1]["after"]) == (10.5, 26.5)
    # 덮기 띠의 칸 자리: 역량 표 차례 그대로, 묶음은 필수 | 우대 | 나머지 (화면이 빈 칸을 먼저 깔고 cover 사건마다 그 칸만 칠한다)
    slots = found["cells"]
    covers = [e["row"] for e in events if e["type"] == "cover"]
    assert [(x["id"], x["tier"]) for x in slots] == [(r["id"], r["tier"]) for r in covers] and len(slots) == len(cov)
    # 화면 글에 번호와 반말, '샘플'이 없다
    shown = " ".join(e["label"] for e in fills) + " ".join(x["text"] for e in events if e["type"] == "facts" for x in e["items"])
    assert not __import__("re").search(r"\b[SCWL]\d{2}\b|\(m\d\)|다\.|음\.|샘플", shown)
    assert "프로젝트로 다 못 배우는 역량은 Isaac Sim, Omniverse, Unreal Engine 3개예요. 교육자료에서 습득해요." in shown


def test_demo_adapt_copy_matches_outputs():
    """데모 저장본(data/*.adapt.json)은 outputs/project/*.local.json 의 adapted 에서 화면 값만 옮긴 것이다 (design/build_adapt.py)."""
    src = pipeline.Path(pipeline.__file__).resolve().parents[1] / "outputs" / "project" / f"{NAVER}.local.json"
    if not src.exists():
        pytest.skip("outputs/ 가 없는 곳 (데모는 제 저장본만 쓴다)")
    full, copy = json.loads(src.read_text(encoding="utf-8")), pipeline.adapt_case(NAVER)
    a = full["adapted"]
    assert (copy["title"], copy["goal"]) == (a["project"]["title"], a["project"]["goal"])
    assert copy["base"]["title"] == a["base"] and [c["title"] for c in copy["complements"]] == a["complements"]
    url = {r["title"]: r["url"] for r in full["ranking"]}
    assert all(c["url"] == url[c["title"]] for c in [copy["base"], *copy["complements"]])
    assert [(q["id"], q["name"], q["hours"], q["core"], q["order"], [(x["project"], x["for"]) for x in q["sources"]], q["added"]) for q in copy["packages"]] == \
        [(q["id"], q["name"], q["hours"], q["core"], q["order"], [(x["project"], x["for"]) for x in q["sources"]], [x["competency"] for x in q["added"]]) for q in a["project"]["packages"]]
    assert [(c["id"], c["name"], c["tier"], c["packages"], c["expect"]) for c in copy["coverage"]] == [(c["id"], c["name"], c["tier"], c["packages"], c["expect"]) for c in a["coverage"]]
    assert copy["hours"] == a["hours"] and copy["tier_counts"] == a["tier_counts"] and copy["krw"] == a["checks"]["krw"]


def test_text_cleaning_is_for_display_only():
    # PDF 줄바꿈 고치기는 글에 따로 나오는 낱말일 때만 (모르는 것은 그대로), 구절은 고치기 전 글에서 찾는다
    assert pipeline.unbreak("high- quality and state- of-the-art") == "high- quality and state- of-the-art"
    assert pipeline.unbreak("high- quality", "a high-quality set") == "high-quality"
    assert pipeline.unbreak("we train mod- els. Our models which") == "we train models. Our models which"
    assert pipeline.quote_parts("we train mod- els here", [{"cid": "C1", "quote": "train mod- els"}])[1] == {"text": "train mod- els", "cids": ["C1"]}
    # 저장소 소개 글: 그림 문자, 코드 블록이 남긴 머리말, 강조·인용 표시를 빼고 목록에서 줄을 바꾼다. 낱말은 그대로
    raw = "Tool 🚀 Quick Start - Ask Copilot Install & run: Or compose in Python: ✨ Why? 1. Fast - 200+ ops > *⭐ Star the repo.* Done in 2.8h"
    out = pipeline.tidy(raw)
    assert out == "Tool Quick Start\n- Ask Copilot Why?\n\n1. Fast\n- 200+ ops\n\nStar the repo. Done in 2.8h"
    assert pipeline.quote_parts(out, [{"cid": "C1", "quote": "200+ ops"}])[1]["cids"] == ["C1"]


KEYS = pipeline.budget_keys(NAVER)
TEXT = lambda: pipeline.posting_text(pipeline.example_case(NAVER))


def run_step(step, key=None, **extra):
    req = {"step": step, "text": TEXT(), **extra}
    if key is not None:
        req["budget"] = key
    return list(server.events(req, live_mode=False, default_speed=0))


def test_budget_keys_come_from_the_saved_data_and_project_done_sends_them():
    assert KEYS == ["84", "168", "252"]
    done = run_step("project")[-1]
    assert done["type"] == "done" and done["budgets"] == [{"key": k, "hours": int(k), "per_day": int(k) // 84} for k in KEYS]


def test_materials_step_replays_m3_picks_without_hours():
    data = pipeline.m3_case(NAVER)
    events = run_step("materials")
    kinds = [e["type"] for e in events]
    assert kinds[0] == "steps" and kinds[-1] == "done" and "error" not in kinds
    assert run_step("materials", "252") == events and run_step("materials", "아무거나") == events      # 공부 시간은 읽지 않는다
    assert [e["key"] for e in events if e["type"] == "stage"] == [x["key"] for x in events[0]["items"]] == ["targets", "search", "judge", "pick"]
    targets = [e["row"] for e in events if e["type"] == "target"]
    assert [t["cid"] for t in targets] == [t["cid"] for t in data["targets"]] and {t["type"] for t in targets} == {"도구", "지식"}
    picks = [e for e in events if e["type"] == "pick"]
    assert [p["row"]["title"] for p in picks] == [p["title"] for p in data["picks"]]
    roles = [p["row"]["role"] for p in picks]
    assert 1 <= roles.count("핵심") <= 2 and 3 <= roles.count("보조") <= 4 and roles == sorted(roles, key=["핵심", "보조"].index)
    assert all(p["row"]["url"].startswith("http") for p in picks)
    done = events[-1]
    assert {k: v["level"] for k, v in done["levels"].items()} == {k: v["level"] for k, v in picks[-1]["levels"].items()} == {t["cid"]: t["level"] for t in data["targets"]}
    covered = sum(t["level"] != "없음" for t in data["targets"])
    assert (done["n"], done["targets"], done["covered"]) == (len(data["picks"]), len(data["targets"]), covered)
    part = sum(t["level"] == "일부" for t in data["targets"])      # 일부만 다루면 0.5 로 센다 (슬라이드와 같은 셈)
    assert done["line"] == (f"도구·지식 역량 {len(data['targets'])}개 중 {covered - part}개를 자료로 다뤄요" + (f", {part}개는 일부만" if part else ""))      # 무엇을 몇 개 (0.5 셈 없이)
    assert done["missing"] == [t["name"] for t in data["targets"] if t["level"] == "없음"] and all(m in done["left"] for m in done["missing"])
    assert "1,000점" in done["rule"] and "핵심 1~2개" in done["rule"] and "보조 3~4개" in done["rule"]
    assert not any("budget_key" in e or "hours" in e for e in events)


def test_demo_m3_copy_matches_outputs():
    src = pipeline.Path(pipeline.__file__).resolve().parents[1] / "outputs" / "materials" / f"{NAVER}.json"
    if not src.exists():
        pytest.skip("outputs/ 가 없는 곳 (데모는 제 저장본만 쓴다)")
    full, copy = json.loads(src.read_text(encoding="utf-8")), pipeline.m3_case(NAVER)
    level = {c["cid"]: c["level"] for c in full["coverage"]}
    assert [(t["cid"], t["name"], t["type"], t["priority"], t["level"]) for t in copy["targets"]] == \
        [(t["cid"], t["name"], t["type"], t["priority"], level[t["cid"]]) for t in full["targets"]]
    assert [(p["role"], p["title"], p["type"], p["url"], {c["cid"]: c["level"] for c in p["covers"]}) for p in copy["picks"]] == \
        [(p["role"], p["title"], p["type"], p["url"], p["covers"]) for p in full["picks"]]
    assert copy["candidates"] == len(full["candidates"]) and copy["cost_krw"] == full["cost_krw"]


def assert_no_exam_in_ranges(events):
    """사건 안의 모든 "N~M주차" 글이 시험 주(7·8·15·16)를 일하는 주처럼 걸치지 않는다"""
    exams = set(pipeline.exam_weeks(pipeline.weeks_case(NAVER)))
    spans = [(int(a), int(b)) for a, b in __import__("re").findall(r"(\d+)~(\d+)주차", json.dumps(events, ensure_ascii=False))]
    assert spans and not [x for x in spans if exams & set(range(x[0], x[1] + 1))], spans


def test_weeks_text_splits_at_exams_and_stops_on_exam_only_ranges():
    exams = pipeline.exam_weeks(pipeline.weeks_case(NAVER))
    assert exams == [7, 8, 15, 16]
    assert pipeline.weeks_text({"from": 6, "to": 11}, exams) == "6주차, 9~11주차"
    assert pipeline.weeks_text({"from": 1, "to": 9}, exams) == "1~6주차, 9주차"
    assert pipeline.weeks_text({"from": 5, "to": 5}, exams) == "5주차"
    with pytest.raises(ValueError):      # 시험 주뿐인 범위는 빈 글이 아니라 멈춤 (저장본이 틀렸다)
        pipeline.weeks_text({"from": 7, "to": 8}, exams)
    with pytest.raises(TypeError):      # 시험 주는 늘 저장본에서 넘긴다 (두 번째 진실을 두지 않는다)
        pipeline.weeks_text({"from": 1, "to": 2})


def test_no_budget_param_means_84_and_bad_values_end_with_one_error():
    assert run_step("weeks") == run_step("weeks", "84") == run_step("weeks", 84)      # 없으면 "84" (정수 84 도 같은 열쇠)
    assert run_step("report") == run_step("report", "14") == run_step("report", 14)      # ⑥ 은 ④ 의 한 주 공부 시간 (없으면 14)
    for bad in ("100", "", 1e9, ["84"], {"a": 1}, True):
        got = list(server.events({"step": "weeks", "text": TEXT(), "budget": bad}, live_mode=False, default_speed=0))
        assert [e["type"] for e in got] == ["error"] and got[0]["reason"] == "budget" and "하루 1·2·3시간" in got[0]["message"]
    got = list(server.events({"step": "project", "text": TEXT(), "budget": "100"}, live_mode=False, default_speed=0))      # 2단계는 안을 읽지 않는다
    assert got[0]["type"] == "steps"


def test_same_budget_twice_and_with_another_in_between_gives_same_events():
    first = run_step("weeks", "168")
    run_step("weeks", "252")
    assert run_step("weeks", "168") == first
    assert run_step("weeks", "84") == run_step("weeks", "84")


def test_project_links_are_web_only():
    assert pipeline.web("https://a.org/x") == "https://a.org/x" and pipeline.web("http://a.org") == "http://a.org"
    assert pipeline.web("javascript:alert(1)") == "" and pipeline.web("") == "" and pipeline.web(None) == ""


def test_project_step_for_new_posting_never_searches_even_live(monkeypatch):
    def no_search(*a, **k):
        raise AssertionError("새 공고의 프로젝트 찾기는 돈이 드는 검색을 하지 않는다")
    monkeypatch.setattr(pipeline, "project", no_search)
    monkeypatch.setattr(pipeline, "live", no_search)
    text = "데이터 엔지니어\n자격요건\n- SQL 로 데이터를 다룰 수 있는 분\n- 파이프라인 운영 경험이 있는 분"
    monkeypatch.setattr(pipeline, "materials", no_search)
    monkeypatch.setattr(pipeline, "weeks", no_search)
    monkeypatch.setattr(pipeline, "report", no_search)
    for step in ("project", "materials", "weeks", "report"):      # 뒤 단계도 예시 공고만 다시 튼다
        events = list(server.events({"step": step, "text": text}, live_mode=True, default_speed=0))
        assert [e["type"] for e in events] == ["notice"] and "예시 공고" in events[0]["text"]
        assert not any(w in events[0]["text"] for w in ("--live", "서버", "비용", "DB"))


def test_demo_project_copy_matches_outputs():
    src = pipeline.Path(pipeline.__file__).resolve().parents[1] / pipeline.project_case(NAVER)["source"]
    if not src.exists():
        pytest.skip("outputs/ 가 없는 곳 (데모는 제 저장본만 쓴다)")
    full, copy = json.loads(src.read_text(encoding="utf-8")), pipeline.project_case(NAVER)
    assert copy["counts"] == full["counts"] and copy["coverage"] == full["coverage"]
    assert copy["sample"]["title"] == full["sample"]["title"] and copy["sample"]["text"] == full["sample"]["text"]
    assert copy["scores"] == [r[pipeline.TIERS[0]] for r in full["ranking"]]
    assert copy["seconds"] in (None, full["seconds"])      # 저장해 둔 판정을 다시 쓴 실행이면 실제 시간이 없어 싣지 않는다
    assert all(q["quote"] in copy["sample"]["readme"] for q in copy["coverage"] if q["quote"])
    assert [r["title"] for r in copy["ranking"]] == [r["title"] for r in full["ranking"][:len(copy["ranking"])]]


@pytest.mark.parametrize("name,key", [(n, k) for n in (NAVER, "aws_fde") for k in ("14", "28")])      # 두 예시 모두 ④ 의 한 주 공부 시간 계획마다 (네이버는 11/22 부터)
def test_report_step_shows_interview_slides_for_the_chosen_budget(name, key, live_server):
    """⑥ 은 발표 자료 모양의 면접 대비 슬라이드 (design/build_report_deck.py): 표지, 질문 다섯, 프로젝트 밖에서 채울 역량. 받기는 pptx"""
    case = pipeline.example_case(name)
    events = list(server.events({"step": "report", "text": pipeline.posting_text(case), "budget": key}, live_mode=False, default_speed=0))
    assert events[0]["type"] == "steps" and events[-1]["type"] == "done"
    done = events[-1]
    facts = json.loads((pipeline.DATA / f"{name}.report.{key}.json").read_text("utf-8"))
    assert done["slides"] == [f"/report/{name}.{key}.{k}.png" for k in range(1, facts["slides"] + 1)] and facts["slides"] == 7
    assert done["pptx"] == f"/report/{name}.{key}.pptx"
    assert len(done["bullets"]) == 2 and f"면접 질문 {facts['questions']}개" in done["bullets"][0]
    assert all(len(b) <= 60 for b in done["bullets"])      # 한 줄씩 (1440 화면 바닥 줄)
    # 프로젝트 밖에서 채울 역량은 ③ 화면과 같은 저장본 (응용 프로젝트 덮기 표에서 '있음'이 아닌 것)
    adapt = json.loads((pipeline.DATA / f"{name}.adapt.json").read_text("utf-8"))
    assert facts["uncovered"] == [c["name"] for c in adapt["coverage"] if c["expect"] != "있음"]
    for url, kind, magic in ((done["slides"][0], "image/png", b"\x89PNG"), (done["pptx"], "application/vnd.openxmlformats-officedocument.presentationml.presentation", b"PK")):
        conn = http.client.HTTPConnection("127.0.0.1", live_server, timeout=10)
        conn.request("GET", url)
        r = conn.getresponse()
        assert r.status == 200 and r.getheader("Content-Type") == kind and r.read(2) == magic[:2]
        conn.close()


def test_report_files_are_served_only_by_name(live_server):
    for bad in ("/report/../pipeline.py", "/report/aws_fde.84.json", "/report/aws_fde.report.84.png", "/report/x.84.1.png", "/report/aws_fde.84.png"):
        conn = http.client.HTTPConnection("127.0.0.1", live_server, timeout=10)
        conn.request("GET", bad)
        assert conn.getresponse().status == 404, bad
        conn.close()


def test_report_slides_differ_between_budgets():
    for name, keys in ((NAVER, ["14", "28"]), ("aws_fde", ["14", "28"])):
        covers = {k: (pipeline.DATA / f"{name}.report.{k}.1.png").read_bytes() for k in keys}
        assert len(set(covers.values())) == len(keys)      # 표지의 공부 시간 줄이 안마다 다르다


@pytest.mark.parametrize("key", KEYS)
def test_exam_weeks_are_empty_and_plan_weeks_shift_to_semester_weeks(key):
    data, wb = pipeline.weeks_case(NAVER), pipeline.weeks_case(NAVER)["budgets"][key]
    for rows in (data["weeks"], wb["weeks"]):
        assert [w["week"] for w in rows] == list(range(1, 17))
        exam = [w for w in rows if w["kind"] == "exam"]
        assert [(w["week"], w["label"]) for w in exam] == [(7, "중간고사"), (8, "중간고사"), (15, "기말고사"), (16, "기말고사")]
        assert all(w["study"] == [] and w["study_hours"] == 0 and w["project_hours_team"] == 0 and w["hours_per_person"] == 0 and not w["over_cap"] for w in exam)
        work = [w for w in rows if w["kind"] == "work"]
        assert [w["week"] for w in work] == [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]      # 계획 n주차: n<=6 그대로, n>=7 은 n+2
        assert [w["plan_week"] for w in work] == list(range(1, 13))
    # 시간은 그대로: 공부 합은 3단계와 같고 프로젝트 팀 시간은 세 안이 같다
    assert wb["totals"]["study_hours"] == pipeline.materials_case(NAVER)["budgets"][key]["total_hours"]
    assert sum(w["project_hours_team"] for w in wb["weeks"]) == pytest.approx(data["totals"]["project_hours_team"], abs=0.2)
    assert wb["totals"]["over_cap_weeks"] == [w["week"] for w in wb["weeks"] if w["over_cap"]]
    assert all(p["weeks"][0] not in (7, 8, 15, 16) and p["weeks"][1] <= 14 for p in data["packages"] if p["weeks"])      # 묶음은 시험 주에서 시작하지 않는다
    # 정리 리포트의 "N주차"도 학기 주차: 줄의 주 범위가 묶음의 주(학기 주차)와 겹치고 시험 주에서 시작하지 않는다
    rep = pipeline.report_case(NAVER)["rows"]
    pk = {p["id"]: p["weeks"] for p in data["packages"]}
    assert all(p["weeks"] == pk[p["id"]] for r in rep for p in r["packages"])
    assert all(r["week"]["from"] not in (7, 8, 15, 16) and r["week"]["to"] <= 14 for r in rep)
    assert [(r["sentence_no"], r["week"]["from"], r["week"]["to"]) for r in rep if r["sentence_no"] in (1, 2, 6)] == [(1, 6, 11), (2, 12, 14), (6, 9, 13)]


def test_highlighter_yellow_is_defined_only_in_tokens():
    """노란 형광펜 색은 tokens.css 에만 있다 (다른 css·js 는 var(--hl…) 로만 쓴다). 리포트 줄도 1단계와 같은 토큰을 받는다."""
    root = pipeline.Path(pipeline.__file__).with_name("static")
    tokens = (root / "css" / "tokens.css").read_text(encoding="utf-8")
    yellows = [m.lower() for m in __import__("re").findall(r"--hl[\w-]*:\s*(#[0-9a-fA-F]{3,8})", tokens)]
    assert len(yellows) == 3
    for f in [*root.glob("css/*.css"), *root.glob("js/*.js"), root / "index.html"]:
        if f.name == "tokens.css":
            continue
        text = f.read_text(encoding="utf-8").lower()
        assert not [y for y in yellows if y in text], f"{f.name} 에 형광펜 색 값이 있다"


def test_css_drops_font_face_whose_file_is_missing(tmp_path):
    """git 에 없는 글꼴(HALUNA)은 파일이 없으면 @font-face 째 빠진다: 화면은 다음 글꼴로 나오고 없는 파일을 요청하지 않는다 (콘솔 404 없음)."""
    (tmp_path / "css").mkdir()
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "Here.woff2").write_bytes(b"x")
    css = ('@font-face {\n  font-family: "Here";\n  src: url("../fonts/Here.woff2") format("woff2");\n}\n'
           '@font-face {\n  font-family: "Gone";\n  src: url("../fonts/Gone.woff2") format("woff2");\n  unicode-range: U+0030-0039;\n}\n:root { --x: 1; }\n')
    out = server.without_missing_fonts(css, tmp_path / "css" / "tokens.css")
    assert '"Here"' in out and "Gone" not in out and ":root { --x: 1; }" in out
    tokens = server.STATIC / "css" / "tokens.css"
    assert server.without_missing_fonts(tokens.read_text(encoding="utf-8"), tokens).count("@font-face") == 1 + (server.STATIC / "fonts" / "HALUNA-Regular.woff2").is_file()


# ── 예시 공고 여럿 (AWS 먼저, 네이버클라우드 두 번째) ──
@pytest.fixture
def fresh_examples():
    """examples() 는 한 번 읽고 기억한다: 바꾼 목록으로 다시 읽고, 끝나면 진짜 목록으로 되돌린다."""
    pipeline.examples.cache_clear()
    yield
    pipeline.examples.cache_clear()


def test_examples_come_in_order_and_each_text_replays_its_own_case(live_server):
    from m2_project import CASES
    conn = http.client.HTTPConnection("127.0.0.1", live_server, timeout=10)
    conn.request("GET", "/api/examples")
    got = json.loads(conn.getresponse().read())
    conn.close()
    want = [n for n in pipeline.EXAMPLES if n in CASES]
    assert [x["case"] for x in got] == want and list(pipeline.EXAMPLES)[:2] == ["aws_fde", NAVER]      # AWS 먼저
    assert NAVER in want and all(x["label"].endswith("공고로 해 보기") and x["filename"].endswith(".txt") for x in got)
    for x in got:      # 고른 예시는 글로 가린다: 붙인 글을 보내면 그 예시를 다시 튼다
        posting = next(e for e in server.events({"text": x["text"], "speed": 0}, live_mode=False, default_speed=0) if e["type"] == "posting")
        assert posting["case"] == x["case"] and posting["replay"] is True and posting["pending"] == pipeline.pending(x["case"])
    assert pipeline.pending(NAVER) == {}      # 네이버는 모든 단계의 저장본이 있다


def test_example_missing_or_broken_in_m2_project_is_left_out(monkeypatch, fresh_examples):
    import m2_project
    monkeypatch.setattr(pipeline, "EXAMPLES", {"not_yet": {"label": "가", "filename": "가.txt"}, "broken": {"label": "나", "filename": "나.txt"},
                                               **pipeline.EXAMPLES})
    monkeypatch.setitem(m2_project.CASES, "broken", {"from": "stage", "posting": "no_such_posting", "url": ""})      # 읽다가 멈추는 것
    names = pipeline.examples()
    assert "not_yet" not in names and "broken" not in names and NAVER in names


def test_step_without_saved_file_says_pending_instead_of_breaking(tmp_path, monkeypatch):
    """저장본(data/<예시>.<종류>.json)이 빠진 단계는 '준비 중' 한 줄로 끝나고, 있는 단계는 그대로 돈다."""
    for f in pipeline.DATA.glob(f"{NAVER}.*.json"):
        if f.name.split(".")[1] not in ("m3", "materials"):      # 3단계(교육자료)와 4·5단계가 읽는 공부 시간 저장본을 뺀다
            (tmp_path / f.name).write_bytes(f.read_bytes())
    monkeypatch.setattr(pipeline, "DATA", tmp_path)
    wait = pipeline.pending(NAVER)
    assert wait == {k: f"이 공고의 {pipeline.STEPS[k][0]}는 아직 준비 중이에요." for k in ("materials", "weeks", "report")}
    posting = next(e for e in server.events({"text": TEXT(), "speed": 0}, live_mode=False, default_speed=0) if e["type"] == "posting")
    assert posting["pending"] == wait      # 화면은 그 단계의 단추 대신 이 글을 적는다
    done = run_step("project")[-1]
    assert done["type"] == "done" and done["budgets"] == []      # 2단계는 돈다. 공부 시간 안 목록은 비어 있다
    for step in wait:
        assert run_step(step, "84") == [{"type": "notice", "text": wait[step]}]


@pytest.mark.parametrize("name", [NAVER])
@pytest.mark.parametrize("key", KEYS)
def test_weeks_step_shows_round_lab_curriculum_in_one_event(name, key, monkeypatch):
    """⑤ 는 주차 계획 md 가 없는 예시면 라운드랩 커리큘럼 생성기 결과 (사용자 11/21). 하루 1·2·3시간 = 주당 7·14·21시간. 12주를 사건 하나로 보내 화면이 한 번에 그린다.
    네이버는 11/22 부터 계획 md 가 있어 그 파일을 안 보이게 하고 본다 (생성기 결과 파일은 그대로 둔다)"""
    monkeypatch.setattr(pipeline, "plans_case", lambda _: [])
    case = pipeline.example_case(name)
    events = list(server.events({"step": "weeks", "text": pipeline.posting_text(case), "budget": key}, live_mode=False, default_speed=0))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "steps" and kinds[-1] == "done" and not {"placed", "work", "exam"} & set(kinds)
    hours = 7 * pipeline.materials_case(name)["budgets"][key]["per_day"]
    saved = json.loads((pipeline.DATA / f"{name}.curriculum.{hours}.json").read_text("utf-8"))
    plan = events[0]["plan"]
    assert [w["week"] for w in plan] == list(range(1, 13)) and events[0]["cap"] == hours
    assert [round(w["learning"] + w["project"], 4) for w in plan] == [round(w["used_minutes"] / 60, 4) for w in saved["weeks"]]
    assert all(w["learning"] + w["project"] <= w["cap"] + 1e-9 for w in plan)      # 주마다 한도 안
    assert {a["kind"] for w in plan for a in w["activities"]} <= {"learning", "project"}
    done = events[-1]
    assert (done["learning"], done["project"]) == (saved["summary"]["learning_hours"], saved["summary"]["implementation_hours"])


def test_weeks_step_shows_7_14_28_hour_plans_with_14_as_default():
    """예시에 주차 계획 md(data/<예시>.plan.<상한>.json)가 있으면 단추 시간(주 7·14·28시간)마다 한 안을 보낸다 (사용자 11/21 밤).
    기본은 14시간이고 (사용자 11/22), 하루 1·2·3시간 선택과 상관없다. 7시간은 보류 파일(blocked)이라 주 칸 없이 본문 글. 15시간 판은 단추 없이 직접 입력 칸으로만 연다.
    안마다 분량 한 줄(line)은 계획 파일의 숫자·이름으로 쓰고, 보류한 시간은 빈 줄 (까닭은 보류 글, 최소 시간은 바닥 줄이 한 번씩)"""
    case = pipeline.example_case("aws_fde")
    saved = {d["constraints"]["hours_per_week"]: d for d in pipeline.plans_case("aws_fde")}
    runs = [[{k: v for k, v in e.items() if k != "budget_key"} for e in server.events(
        {"step": "weeks", "text": pipeline.posting_text(case), "budget": k}, live_mode=False, default_speed=0)] for k in KEYS]
    assert all(r == runs[0] for r in runs)
    steps, done = runs[0][0], runs[0][-1]
    base = saved[pipeline.DEFAULT_WEEK_HOURS]
    assert (pipeline.DATA / "aws_fde.plan.15.json").is_file() and sorted(saved) == [14, 15, 28]      # 15 는 단추 없이 직접 입력 칸으로만
    assert steps["default"] == "14" and steps["cap"] == 14 and steps["held"] == base["held"] and [h["id"] for h in base["held"]] == ["W9", "W10"]
    assert [(p["key"], p["label"], p["source"]) for p in steps["plans"]] == [("7", "주 7시간", "blocked"), ("14", "주 14시간", "md"), ("15", "주 15시간", "md"), ("28", "주 28시간", "md")]
    assert [p["key"] for p in steps["plans"] if p["preset"]] == ["7", "14", "28"]      # 단추는 셋, 15 는 직접 입력
    for p in steps["plans"]:
        if p["source"] == "blocked":
            assert p["plan"] == [] and p["summary"]["blocked"] and p["summary"]["min_text"] == "11시간 40분"
            assert p["blocked"]["lines"][0] == "12주 84시간으로는 핵심 작업 묶음과 꼭 볼 자료에 필요한 139시간(만들기 128시간 + 배우기 11시간)에 못 미쳐요."
            assert p["line"] == "" and not any("11시간 40분" in x for x in p["blocked"]["lines"])
            continue
        d = saved[p["cap"]]
        assert [round(w["learning"] + w["project"], 4) for w in p["plan"]] == [round(w["used_minutes"] / 60, 4) for w in d["weeks"]]
        assert all(w["learning"] + w["project"] <= w["cap"] + 1e-9 for w in p["plan"])
        assert {a["id"] for w in p["plan"] for a in w["activities"] if a["kind"] == "project"} == set(d["assigned"])
        assert p["summary"]["deliverables"] == len(d["assigned"]) and p["held"] == d["held"]
        assert all(1 <= len(w["method_steps"]) <= 3 and 1 <= len(w["goal_steps"]) <= 3 for w in p["plan"])      # 토글은 개조식 세 줄까지
    assert [h["id"] for h in saved[14]["held"]] == ["W9", "W10"] and saved[28]["held"] == []
    block = pipeline.blocked_case("aws_fde")
    assert [(b["hours_per_week"], b["available_minutes"], b["needed_minutes"], b["min_per_week_minutes"]) for b in block] == [(7, 84 * 60, 139 * 60, 700)]
    lines = {p["key"]: p["line"] for p in steps["plans"]}
    assert lines["28"] == "주 28시간이면 작업 묶음 10개가 모두 12주 안에 들어가요"
    assert lines["14"] == ("주 14시간이면 작업 묶음 2개는 12주 계획 밖으로 미뤄요 ("
                           + ", ".join(f"{h['id']} {h['name']}" for h in saved[14]["held"]) + ")")
    assert "scale" not in steps
    assert (done["cap"], done["project"], done["deliverables"]) == (14, base["summary"]["implementation_hours"], len(base["assigned"]))


def test_naver_hand_plans_follow_the_aws_rules():
    """네이버 12주 계획 (손으로 짬, design/naver_plan_hand.md): AWS 와 같은 단추(주 7·14·28시간, 기본 14)와 규칙.
    작업은 응용 W1~W7, 한 사람 시간 = 팀 시간 ÷ 2 (AWS 계획의 셈), 주마다 상한 안, ③ 에서 고른 자료 6개는 두 계획 모두 '기존 배정',
    자료 주소는 모두 팀 자료 은행 또는 ③·응용 저장본에 있는 것 (지어낸 주소가 없다). 7시간은 핵심 작업만으로도 넘쳐 보류"""
    case = pipeline.example_case(NAVER)
    steps = next(server.events({"step": "weeks", "text": pipeline.posting_text(case)}, live_mode=False, default_speed=0))
    assert steps["default"] == "14" and [(p["key"], p["label"], p["source"]) for p in steps["plans"]] == [("7", "주 7시간", "blocked"), ("14", "주 14시간", "md"), ("28", "주 28시간", "md")]
    adapt = pipeline.saved(NAVER, "adapt")
    team = {p["id"]: p["hours"] for p in adapt["packages"]}
    picks = {p["url"] for p in pipeline.m3_case(NAVER)["picks"]}
    from m3_materials import pick
    known = {r["url"] for r in pick.bank()[0]} | picks | {x["url"] for x in [adapt["base"], *adapt["complements"]]}
    for d in pipeline.plans_case(NAVER):
        cap = d["constraints"]["hours_per_week"] * 60
        built = {}
        for w in d["weeks"]:
            assert w["used_minutes"] <= cap and w["used_minutes"] == sum(a["minutes"] for a in w["activities"])
            kinds = [a["kind"] for a in w["activities"]]
            assert kinds == sorted(kinds, key=lambda k: k != "learning")      # 배우기가 먼저, 만들기가 뒤
            for a in w["activities"]:
                assert a["minutes"] % 5 == 0
                if a["kind"] == "project":
                    built[a["id"]] = built.get(a["id"], 0) + a["minutes"]
                else:
                    assert a["url"] in known and a["covers"] and a["why"][0].startswith("배정 근거 · "), a["title"]
        assert built == {k: h * 60 // 2 for k, h in team.items()} and d["assigned"] == list(team) and d["held"] == []
        learning = [a for w in d["weeks"] for a in w["activities"] if a["kind"] == "learning"]
        assert {a["url"] for a in learning if "기존 배정" in a["why"][0]} == picks and len(picks) == 6
    lines = {p["key"]: p["line"] for p in steps["plans"]}
    assert lines["14"] == "주 14시간이면 작업 묶음 7개가 모두 12주 안에 들어가요" == lines["28"].replace("28", "14")
    block = pipeline.blocked_case(NAVER)
    core = sum(h * 60 // 2 for k, h in team.items() if next(p for p in adapt["packages"] if p["id"] == k)["core"])
    assert [(b["hours_per_week"], b["available_minutes"], b["needed_build_minutes"], b["min_per_week_minutes"]) for b in block] == [(7, 84 * 60, core, 770)]
    assert core > 84 * 60      # 핵심 작업만으로도 84시간을 넘는다
    assert pipeline.saved(NAVER, "short") and set(pipeline.saved(NAVER, "short")) == set(team)      # 간트차트 짧은 이름도 W1~W7


def test_weekly_plans_name_weeks_by_semester_6_exam_2_6_exam_2():
    """사용자 11/22: 12주 계획은 학기 16주에서 중간·기말 시험 2주씩을 뺀 것 (6 + 2 + 6 + 2).
    ④ 칸 이름·끝나는 주·⑥ 의 주는 학기 주 (계획 7주 → 학기 9주), 시험 띠는 저장본 team.exams 와 같다"""
    for name in ("aws_fde", NAVER):
        team = pipeline.weeks_case(name)["team"]
        assert team["semester_weeks"] == pipeline.SEMESTER_WEEKS
        assert [(list(e["weeks"]), e["label"]) for e in pipeline.SEMESTER_EXAMS] == [(e["weeks"], e["label"]) for e in team["exams"]]
    assert [pipeline.sem_week(k) for k in range(1, 13)] == [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]
    for name in ("aws_fde", NAVER):
        semester_weeks_follow_the_plan(name)


def semester_weeks_follow_the_plan(name):
    case = pipeline.example_case(name)
    steps = next(server.events({"step": "weeks", "text": pipeline.posting_text(case)}, live_mode=False, default_speed=0))
    for p in steps["plans"]:
        if p["source"] == "blocked":
            continue
        d = {x["constraints"]["hours_per_week"]: x for x in pipeline.plans_case(name)}[p["cap"]]
        assert [w["sem"] for w in p["plan"]] == [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]
        assert p["exams"] == [{"from": 7, "to": 8, "label": "중간고사"}, {"from": 15, "to": 16, "label": "기말고사"}]
        assert p["semester"] == "한 학기 16주 = 6주 + 중간고사 2주 + 6주 + 기말고사 2주"
        ends = [(a["ends"], x["ends_week"]) for w, dw in zip(p["plan"], d["weeks"]) for a, x in zip(w["activities"], dw["activities"]) if x.get("ends_week")]
        assert ends and all(a == pipeline.sem_week(b) for a, b in ends)
        if not (pipeline.DATA / f"{name}.report.{p['key']}.json").is_file():      # 리포트 없는 시간 (aws 15)
            continue
        facts = json.loads((pipeline.DATA / f"{name}.report.{p['key']}.json").read_text("utf-8"))
        assert all(k not in (7, 8, 15, 16) and k <= 14 for r in facts["rows"] for pk in r["packages"] for k in pk["weeks"])


@pytest.mark.parametrize("name", ["aws_fde", NAVER])
def test_report_follows_the_chosen_weekly_plan(name):
    """⑥ 은 ④ 에서 고른 한 주 공부 시간의 계획으로 (사용자 11/21): 37줄 모두, 줄의 작업마다 ⑥ 의 주 = 그 계획에서 그 작업이 놓인 주.
    미룬 작업은 주 없이 미룬 일. 공부 자료는 그 계획 파일의 교육자료. 7시간(보류)은 리포트 대신 본문 글, 하루 공부 시간 열쇠는 받지 않는다"""
    case = pipeline.example_case(name)
    report = pipeline.report_case(name)
    for d in pipeline.plans_case(name):
        key = f"{d['constraints']['hours_per_week']:g}"
        if not (pipeline.DATA / f"{name}.report.{key}.json").is_file():      # 리포트 없는 시간 (aws 15): 아래 test_hours_without_a_report_say_so
            continue
        facts = json.loads((pipeline.DATA / f"{name}.report.{key}.json").read_text("utf-8"))
        at = {}
        for w in d["weeks"]:
            for x in w["activities"]:
                if x["kind"] == "project":
                    at.setdefault(x["id"], set()).add(pipeline.sem_week(w["week"]))      # ⑥ 의 주는 ④ 칸과 같은 학기 주
        held = {h["id"] for h in d["held"]}
        learning = {(pipeline.sem_week(w["week"]), x["title"]) for w in d["weeks"] for x in w["activities"] if x["kind"] == "learning"}
        assert facts["plan"]["hours"] == d["constraints"]["hours_per_week"] and facts["plan"]["held"] == [h["id"] for h in d["held"]]
        assert [r["n"] for r in facts["rows"]] == [r["sentence_no"] for r in report["rows"]]      # 줄 모두 (AWS 37, 네이버 19)
        for r, src in zip(facts["rows"], report["rows"]):
            assert [p["id"] for p in r["packages"]] == [p["id"] for p in src.get("plan_packages", src["packages"])]      # 네이버는 계획 번호로 이은 작업
            for p in r["packages"]:
                assert (p["held"], set(p["weeks"])) == ((True, set()) if p["id"] in held else (False, at[p["id"]])), (key, r["n"], p)
            assert r["study"] is None or (r["study"]["week"], r["study"]["title"]) in learning, (key, r["n"])
        assert set(facts["shown"]) <= {r["n"] for r in facts["rows"]} and len(facts["shown"]) == facts["questions"]
        events = list(server.events({"step": "report", "text": pipeline.posting_text(case), "budget": key}, live_mode=False, default_speed=0))
        assert events[-1]["basis"].startswith(f"한 주 {key}시간 계획 기준") and all(e["budget_key"] == key for e in events)
    blocked = list(server.events({"step": "report", "text": pipeline.posting_text(case), "budget": "7"}, live_mode=False, default_speed=0))
    assert blocked[-1]["type"] == "done" and blocked[-1]["slides"] == [] and blocked[-1]["pptx"] is None and "보류" in blocked[-1]["note"]
    default = list(server.events({"step": "report", "text": pipeline.posting_text(case)}, live_mode=False, default_speed=0))
    assert default[-1]["budget_key"] == "14"
    for bad in ("84", "16", True, ["28"]):
        got = list(server.events({"step": "report", "text": pipeline.posting_text(case), "budget": bad}, live_mode=False, default_speed=0))
        assert [e["type"] for e in got] == ["error"] and f"{'·'.join(pipeline.report_keys(name))}시간" in got[0]["message"]


def test_plan_steps_keep_md_words_and_split_at_clause_endings():
    """개조식 줄은 md 문장을 연결 어미에서 나누고 끝 어미만 '~기' 로 바꾼다. 세 조각을 넘으면 이웃을 원문 그대로 붙인다"""
    from demo.design.build_curriculum_md import ending, steps
    assert ending("ADR 양식을 잡고") == "ADR 양식을 잡기" and ending("점검한 뒤") == "점검하기" and ending("대응시킨 뒤") == "대응시키기"
    assert ending("양식을 잡은 다음") == "양식을 잡기" and ending("계획을 수립한다.") == "계획을 수립하기" and ending("방법을 적용하며") == "방법을 적용하기"
    got = steps("가를 정하고, 나를 점검한 뒤, 다를 정리해 근거로 삼고, 라를 확인한 뒤 마를 등록한다.")
    assert got == ["가를 정하고, 나를 점검하기", "다를 정리해 근거로 삼기", "라를 확인한 뒤 마를 등록하기"]      # 가장 짧게 붙는 이웃 둘을 쉼표째 붙인다
    assert steps("A를 완성한다. 아울러 B를 시작한다.") == ["A를 완성하기", "B를 시작하기"]



def test_gantt_plan_view_attaches_every_learning_item_to_a_package_and_lists_packages():
    """④ 간트차트: 교육자료마다 받쳐 주는 작업(for)이 있고, 작업 묶음 표(packages)는 번호 차례, 미룬 것은 held"""
    for name in ("aws_fde", NAVER):
        gantt_rows_ok(name)
    steps = next(e for e in pipeline.weeks(pipeline.example_case("aws_fde"), speed=0) if e["type"] == "steps")
    two = {a["id"]: a["for"] for w in steps["plans"][1]["plan"] for a in w["activities"] if a["kind"] == "learning"}
    assert two["L0201"] == "W2" and two["L0303"] == "W3"      # 겹치는 역량 + 그 주의 작업


def gantt_rows_ok(name):
    steps = next(e for e in pipeline.weeks(pipeline.example_case(name), speed=0) if e["type"] == "steps")
    for v in steps["plans"]:
        if v["source"] != "md":
            continue
        ids = [k["id"] for k in v["packages"]]
        assert ids == sorted(ids, key=lambda x: int(x[1:])) and {k["id"] for k in v["packages"] if k["held"]} == {h["id"] for h in v["held"]}
        learning = [a for w in v["plan"] for a in w["activities"] if a["kind"] == "learning"]
        assert learning and all(a["for"] in ids and a["why"] and a["levels"] for a in learning)
        assert all(w["reason"] for w in v["plan"])


def test_report_event_offers_full_pdf_only_when_the_file_exists():
    """⑥ PDF 받기: 질문 전체 PDF 파일이 있는 계획만 주소를 싣는다 (없으면 None), 서버는 application/pdf 로 준다"""
    aws = pipeline.report_page("aws_fde", "14")
    assert aws["pdf"] == "/report/aws_fde.14.all.pdf" and aws["pdf_filename"].endswith("_전체.pdf")
    assert server.REPORT.fullmatch(aws["pdf"]) and server.TYPES[".pdf"] == "application/pdf"
    if not (pipeline.DATA / f"{NAVER}.report.84.all.pdf").is_file():
        assert pipeline.report_page(NAVER, "84")["pdf"] is None


def weeks_steps(name):
    case = pipeline.example_case(name)
    return next(server.events({"step": "weeks", "text": pipeline.posting_text(case)}, live_mode=False, default_speed=0))


def test_custom_hours_15_opens_the_saved_aws_plan():
    """④ 직접 입력: 15 는 AWS 에 저장된 계획 (plan.15.json) 이라 단추처럼 그 계획을 보인다. 열쇠 목록은 파일에서 읽는다"""
    steps = weeks_steps("aws_fde")
    assert pipeline.saved_hours("aws_fde") == [7, 14, 15, 28]
    assert pipeline.pick_hours("aws_fde", "15") == {"key": "15"} and pipeline.pick_hours("aws_fde", 15) == {"key": "15"}
    plan = next(p for p in steps["plans"] if p["key"] == "15")
    saved = json.loads((pipeline.DATA / "aws_fde.plan.15.json").read_text("utf-8"))
    assert plan["source"] == "md" and plan["cap"] == 15 and plan["preset"] is False and plan["held"] == saved["held"]
    assert steps["custom"]["miss"] == "데모에는 주 7·14·15·28시간 계획만 저장되어 있어요. 다른 시간은 생성기를 다시 돌려야 해요."


def test_custom_hours_15_for_naver_says_only_saved_hours_exist():
    steps = weeks_steps(NAVER)
    assert pipeline.pick_hours(NAVER, "15") == {"message": "데모에는 주 7·14·28시간 계획만 저장되어 있어요. 다른 시간은 생성기를 다시 돌려야 해요."}
    assert steps["custom"]["miss"] == pipeline.pick_hours(NAVER, "15")["message"]
    assert "15" not in [p["key"] for p in steps["plans"]]
    assert pipeline.pick_hours("aws_fde", "20")["message"].startswith("데모에는 주 7·14·15·28시간")


@pytest.mark.parametrize("raw", ["abc", "14.5", "", " ", "-3", "0", "41", "1e1", None, True, 14.5, ["14"]])
def test_custom_hours_rejects_non_integers_and_out_of_range(raw):
    got = pipeline.pick_hours("aws_fde", raw)
    assert got == {"message": "한 주 공부 시간은 1~40 사이의 정수로 넣어 주세요."}
    assert pipeline.custom_texts("aws_fde")["bad"] == got["message"]


def test_hours_without_a_report_say_so():
    """⑤ : 주 15시간 리포트는 저장본이 없다. 7시간(보류)처럼 리포트 대신 본문 글 (새 리포트는 만들지 않는다)"""
    case = pipeline.example_case("aws_fde")
    assert "15" in pipeline.report_keys("aws_fde") and pipeline.report_page("aws_fde", "15") is None
    got = list(server.events({"step": "report", "text": pipeline.posting_text(case), "budget": "15"}, live_mode=False, default_speed=0))
    assert [e["type"] for e in got][-1] == "done" and all(e["budget_key"] == "15" for e in got)
    assert got[-1]["slides"] == [] and got[-1]["pptx"] is None
    assert got[-1]["note"] == "주 15시간 리포트는 데모에 없어요. ④에서 주 14·28시간을 고르면 리포트가 나와요."
    assert "14·28" in got[-1]["note"] and "15" not in got[-1]["note"].split("④")[1]
