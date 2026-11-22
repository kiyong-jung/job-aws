"""데모 서버. 표준 라이브러리만 쓴다.

GET  /                 화면 (static/index.html)
GET  /static/...       화면 파일
GET  /report/<예시>.<시간>.<쪽>.png|.pptx|.all.pdf   ⑥ 정리 리포트 슬라이드 (쪽 그림과 받을 pptx)
GET  /api/examples     예시 공고 목록 [{case, label, title, company, text, filename}] (빈 화면 단추 차례. 읽을 수 있는 것만)
GET  /api/mode         {live}
POST /api/run          {text | html | url, title?, speed?, stop?, step?, budget?} → text/event-stream (사건은 pipeline.py 참고)
                       step: "project" 면 역량 → 프로젝트 찾기(2단계), "materials" 면 교육자료 찾기(3단계),
                       "weeks" 면 12주 계획 짜기(4단계), "report" 면 정리 리포트(5단계). text 는 1단계 원문의 문장들
                       budget 은 공부 시간 안의 열쇠 ("84"·"168"·"252", 없으면 "84"). 4·5단계만 읽는다.
                       주차 계획 md 가 있는 예시(aws_fde, naver_ml_intern)의 "report" 는 한 주 공부 시간 ("7"·"14"·"28", 없으면 "14").
                       몸통은 JSON 객체 하나, 2MB 까지. 넘으면 413, 객체가 아니면 400.

예시와 같은 공고면 저장된 결과를 다시 튼다(돈이 들지 않는다). 다른 공고는 --live 일 때만 끝까지 돈다.
어느 예시인지는 요청마다 글(text)로 가린다 (pipeline.which): 2~5단계 요청도 1단계 원문을 보내니 고른 예시가 모든 단계로 이어진다.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from demo import fetch, pipeline

STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 2_000_000
MAX_SPEED = 8.0
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".webp": "image/webp", ".png": "image/png", ".txt": "text/plain; charset=utf-8",
         ".svg": "image/svg+xml", ".pdf": "application/pdf", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
POSTING = re.compile(r"/posting/([a-z0-9_]+)\.png")
PROOF = re.compile(r"/proof/([0-9a-f]{12})\.png")      # 근거 구절의 원문 캡처 (data/proof/<id>.png)      # ① 실제 공고 사이트 화면 (data/<예시>.posting.png)
REPORT = re.compile(r"/report/([a-z0-9_]+)\.(\d+)\.((?:\d+\.)?png|pptx|all\.pdf)")      # ⑥ 리포트 쪽 그림과 pptx (data/<예시>.report.<시간>.<쪽>.png·.pptx). 이름 꼴이 맞을 때만


# css 의 @font-face 한 덩어리와 그 글꼴 파일 주소 (css 파일 자리에서 본 상대 주소)
FONT_FACE = re.compile(r'@font-face\s*\{[^}]*?url\("?([^")]+)"?\)[^}]*\}')


def without_missing_fonts(css, at):
    """css 의 @font-face 가운데 글꼴 파일이 없는 것을 뺀다 (git 에 올리지 않는 HALUNA 처럼, 파일이 없는 사본).
    화면은 font-family 의 다음 글꼴(Pretendard)로 나오고, 없는 파일을 요청하지 않으니 콘솔에 404 가 찍히지 않는다. 화면 쪽 검사(HEAD 요청)는 없다."""
    return FONT_FACE.sub(lambda m: m.group(0) if (at.parent / m.group(1)).resolve().is_file() else "", css)


def events(req, live_mode, default_speed):
    """요청 하나 → 사건들. 주소는 fetch.py 로 한 번만 읽고, 막히면 까닭을 쉬운 말로 돌려준다."""
    try:      # 0 은 기다리지 않기. 너무 큰 값으로 스레드를 오래 붙잡지 못하게 위를 막는다
        speed = min(max(float(req["speed"]), 0.0), MAX_SPEED) if req.get("speed") is not None else default_speed
    except (TypeError, ValueError):
        speed = default_speed
    stop = req.get("stop")
    stop = int(stop) if isinstance(stop, (int, float)) or (isinstance(stop, str) and stop.isdigit()) else stop
    text, title, url = str(req.get("text") or ""), str(req.get("title") or ""), str(req.get("url") or "")
    if req.get("html"):
        title, text, _ = fetch.page_text(str(req["html"]))
    if url and not text:
        yield {"type": "stage", "key": "read", "label": "공고 주소를 여는 중"}
        try:
            got = fetch.fetch(url)
        except fetch.Blocked as e:
            yield {"type": "error", "reason": e.reason, "message": fetch.message(e)}
            return
        title, text = got["title"], got["text"]
    if len(text.strip()) < 40:
        yield {"type": "error", "reason": "short", "message": "내용이 조금 짧아요. 자격요건까지 붙여넣어 볼까요?"}
        return
    case = pipeline.which(text)      # 같은 예시 공고 (없으면 None)
    step = req.get("step")
    state = req.get("state") if isinstance(req.get("state"), dict) else None
    if live_mode and case is None and step and state and isinstance(state.get("case"), dict):      # 새 공고 라이브 (demo/live.py)
        from demo import live
        c, budget = state["case"], str(req.get("budget") or "84")
        need = {"project": (), "adapt": ("project",), "materials": (), "weeks": ("project", "adapt", "materials"), "report": ("adapt", "materials")}
        if step not in need or any(k not in state for k in need[step]):
            yield {"type": "error", "reason": "state", "message": "앞 단계 결과가 없어요. 처음부터 다시 해 볼까요?"}
            return
        yield from {"project": lambda: live.project(c), "adapt": lambda: live.adapt(c, state), "materials": lambda: live.materials(c),
                    "weeks": lambda: live.weeks(c, state, budget), "report": lambda: live.report(c, state, budget)}[step]()
        return
    if step in pipeline.STEPS:      # 2~5단계: 예시만 다시 튼다. 새 공고는 --live 여도 검색하지 않는다
        what, _ = pipeline.STEPS[step]
        if case is None:
            yield from pipeline.project_offline(what)
            return
        wait = pipeline.pending(case["case"]).get(step)      # 이 예시의 저장본이 아직 없는 단계
        if wait:
            yield {"type": "notice", "text": wait}
            return
        if step in ("project", "materials"):      # 2·3단계는 공부 시간을 읽지 않는다
            yield from getattr(pipeline, step)(case, speed)
            return
        if step == "report" and pipeline.plans_case(case["case"]):      # ⑥ 은 ④ 에서 고른 한 주 공부 시간의 계획 (없으면 기본 14)
            budget = pipeline.report_key_of(req.get("budget"), case["case"])
            if budget is None:
                yield {"type": "error", "reason": "budget", "message": f"한 주 공부 시간은 {'·'.join(pipeline.report_keys(case['case']))}시간 중에서 고를 수 있어요."}
                return
            yield from pipeline.report(case, speed, budget)
            return
        budget = pipeline.budget_of(req.get("budget"), case["case"])      # 없으면 "84". 저장본에 없는 값은 사건 하나로 끝낸다
        if budget is None:
            yield {"type": "error", "reason": "budget", "message": "공부 시간은 하루 1·2·3시간 중에서 고를 수 있어요."}
            return
        yield from getattr(pipeline, step)(case, speed, budget)
        return
    if case:
        yield from pipeline.replay(case, speed, stop)
    elif live_mode:
        yield from pipeline.live(text, title, url, speed)
    else:
        yield from pipeline.offline(text, title)


def example(name):
    """빈 화면 단추 하나: 단추 이름과, 누르면 파일 칩으로 붙일 공고 글."""
    case = pipeline.example_case(name)
    p = case["posting"]
    return {"case": name, "label": pipeline.EXAMPLES[name]["label"], "title": p["title"], "company": p["company"],
            "text": pipeline.posting_text(case), "filename": pipeline.EXAMPLES[name]["filename"]}


class Handler(BaseHTTPRequestHandler):
    settings = {"live": False, "speed": 1.0}

    def log_message(self, fmt, *args):
        pass

    def _body(self, code, body, kind):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._body(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/examples":
            return self._json([example(name) for name in pipeline.examples()])
        if path == "/api/mode":
            return self._json({"live": self.settings["live"]})
        if path in ("/", "/index.html"):
            f = STATIC / "index.html"
        elif m := POSTING.fullmatch(path):
            f = pipeline.DATA / f"{m[1]}.posting.png"
        elif m := PROOF.fullmatch(path):
            f = pipeline.DATA / "proof" / f"{m[1]}.png"
        elif m := REPORT.fullmatch(path):
            f = pipeline.DATA / f"{m[1]}.report.{m[2]}.{m[3]}"
        elif path.startswith("/static/"):
            f = (STATIC / path.removeprefix("/static/")).resolve()      # .. 이나 절대 경로로 static/ 밖을 가리키면 404
            if STATIC not in f.parents:
                return self.send_error(404)
        else:
            return self.send_error(404)
        if not f.is_file():
            return self.send_error(404)
        body = f.read_bytes()
        if f.suffix == ".css":
            body = without_missing_fonts(body.decode("utf-8"), f).encode("utf-8")
        self._body(200, body, TYPES.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        if self.path != "/api/run":
            return self.send_error(404)
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self.send_error(400)
        if not 0 <= size <= MAX_BODY:
            return self.send_error(413)
        try:
            req = json.loads(self.rfile.read(size) or b"{}")
        except (ValueError, RecursionError):      # 깨진 JSON, 잘못된 UTF-8, 너무 깊게 겹친 JSON
            return self.send_error(400)
        if not isinstance(req, dict):
            return self.send_error(400)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for ev in events(req, self.settings["live"], self.settings["speed"]):
                self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:      # 화면이 멈춰 보이지 않게, 까닭을 사건으로 보낸다
            msg = {"type": "error", "reason": "server", "message": "이번엔 끝까지 못 했어요. 다시 해 볼까요?",
                   "detail": f"{type(e).__name__}: {e}"}
            try:
                self.wfile.write(f"data: {json.dumps(msg, ensure_ascii=False)}\n\n".encode("utf-8"))
            except OSError:      # 그사이 화면이 떠났다
                pass


class Server(ThreadingHTTPServer):
    # 화면은 모듈·글꼴·css 스무 개쯤을 한꺼번에 받는다. 기다리는 줄(listen backlog)이 기본값 5 면 넘친 연결이 끊겨(ERR_CONNECTION_RESET)
    # 모듈 하나가 빠진 채 화면이 뜨지 않는 일이 가끔 생긴다 (shots.py 의 page-load timeout 이 이것이었다)
    request_queue_size = 128
    daemon_threads = True


def serve(host, port, live_mode, speed):
    Handler.settings = {"live": live_mode, "speed": speed}
    return Server((host, port), Handler)
