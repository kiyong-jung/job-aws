"""대시보드 화면을 실제 조작으로 찍고 검사한다 (Chrome 원격 조종, 실제 시간). 서버가 먼저 떠 있어야 한다.

  cd code && PYTHONPATH=. ../기용/.venv/bin/python -m demo --port 8770 &
  cd code && ../기용/.venv/bin/python demo/shots.py [--case aws_fde] [--base http://127.0.0.1:8770/] [--out 폴더]

1440×900 하나로 본다 (DESIGN_RULES U5-1). 흐름(바닥 줄 단추를 눌러 넘긴다): 시작 화면 → 예시 공고 → ① 공고 읽기 → ② 프로젝트 찾기 → ③ 응용 → ④ 교육자료
→ (하루 1시간) ⑤ 12주 계획 → ⑥ 정리 리포트(슬라이드 여러 장) → 공부 시간 바꾸기 → 새 공고(시작 화면).
쪽마다 검사 (사용자 11/19): 대화 칸이 없다, 바닥 줄 불렛은 둘 이하이고 한 줄씩, 쪽 그림 안에 문장 글(.chart-fact 등)이 없다,
형광펜은 첫 칠부터 1.5초 안에 다 칠한다, ② 의 낱말로 모은 후보 점(파랑)은 1,000 ÷ 100 = 10개.
넘침·스크립트 오류·13px 아래 글이 하나라도 있으면 0 이 아닌 값으로 끝난다. 결과는 --out 폴더의 *.png. 검사가 어긋나면 그 화면을 fail.png 로.
venv 에 이미 있는 websockets 만 쓴다.
"""
import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ap = argparse.ArgumentParser()
ap.add_argument("--case", default="aws_fde", help="찍을 예시 공고")
ap.add_argument("--base", default="http://127.0.0.1:8770/", help="찍을 서버 주소")
ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "shots"), help="사진을 둘 폴더")
ap.add_argument("--scale", type=float, default=1, help="화면 배율 (발표 슬라이드에 넣을 사진은 2)")
ARGS = ap.parse_args()
CASE, BASE, OUT, SCALE = ARGS.case, ARGS.base.rstrip("/") + "/", Path(ARGS.out), ARGS.scale
EXAMPLE = f'[data-example="{CASE}"]'
DATA = Path(__file__).resolve().parent / "data"
PROJECT = json.loads((DATA / f"{CASE}.project.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.pipeline import DEFAULT_WEEK_HOURS, blocked_case, plans_case  # noqa: E402

PLANS = plans_case(CASE)      # ④ 단추에 있는 주차 계획 md (주 14·28시간). 15시간 판은 파일만 있고 단추에 없다
BLOCKED = blocked_case(CASE)      # 계획을 보류한 시간 (주 7시간): 주 칸 없이 본문 글
BUTTONS = sorted([f"{d['constraints']['hours_per_week']:g}" for d in PLANS] + [f"{b['hours_per_week']:g}" for b in BLOCKED], key=float)
PLAN = next((d for d in PLANS if d["constraints"]["hours_per_week"] == DEFAULT_WEEK_HOURS), PLANS[-1] if PLANS else None)      # 기본 주 14시간: ⑤ 는 하루 공부 시간과 상관없다
REPORT_FACTS = lambda key: json.loads((DATA / f"{CASE}.report.{key}.json").read_text(encoding="utf-8"))

# 화면에 보이는 글 줄 가운데 글자 크기 < 13px, 또는 --muted 색인 것 (짝 보기에서 다른 줄을 흐리게 하는 [data-focus] 안, 화면 읽기용 글은 뺀다)
SMALL_TEXT = """(() => { const probe = document.createElement('i'); probe.style.color = 'var(--muted)'; document.body.append(probe);
  const muted = getComputedStyle(probe).color; probe.remove(); const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (r.width <= 1 || r.height <= 1 || cs.visibility === 'hidden' || el.closest('.sr-only, [hidden], [inert][hidden]')) continue;
    if (el.tagName === 'TEXTAREA' || el.tagName === 'SCRIPT') continue;
    const fs = parseFloat(cs.fontSize);
    if (fs < 13) bad.push(`${fs}px ${el.className || el.tagName} '${el.textContent.trim().slice(0, 24)}'`);
    else if (cs.color === muted && !el.closest('[data-focus]')) bad.push(`muted ${el.className || el.tagName} '${el.textContent.trim().slice(0, 24)}'`);
  }
  return bad; })()"""



class Page:
    def __init__(self, ws):
        self.ws, self.n, self.errors = ws, 0, []
        self.failed = []      # 실패한 요청 (끊긴 것, 400 이상). 페이지가 안 열릴 때 까닭을 찍는다
        self.shots, self.problems = 0, []      # 찍은 사진 수, 넘침·스크립트 오류
        self.console = []     # Log.enable 을 켠 동안의 콘솔 오류·경고 (글꼴 없는 사본에서 본다)

    async def send(self, method, **params):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("method") == "Runtime.exceptionThrown":      # 화면 스크립트 오류는 사진 줄 끝에 적는다
                d = msg["params"]["exceptionDetails"]
                self.errors.append(d.get("exception", {}).get("description") or f"{d.get('text', '?')} ({d.get('url', '')}:{d.get('lineNumber', '')})")
            elif msg.get("method") == "Network.loadingFailed" and not msg["params"].get("canceled"):
                self.failed.append(f"{msg['params'].get('errorText', '?')} ({msg['params'].get('type', '')})")
            elif msg.get("method") == "Log.entryAdded" and msg["params"]["entry"]["level"] in ("error", "warning"):
                self.console.append(msg["params"]["entry"]["text"])
            elif msg.get("method") == "Network.responseReceived" and msg["params"]["response"]["status"] >= 400:
                self.failed.append(f"{msg['params']['response']['status']} {msg['params']['response']['url']}")
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    async def js(self, expr):
        r = await self.send("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    async def until(self, expr, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            if await self.js(f"!!({expr})"):
                return
            await asyncio.sleep(0.05)
        raise TimeoutError(expr)

    async def mouse(self, selector, click=True):
        box = await self.js(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); "
                            "e.scrollIntoView({block: 'center'}); const r = e.getClientRects()[0]; "
                            "return [r.left + Math.min(r.width / 2, 40), r.top + r.height / 2]; })()")
        x, y = box
        await self.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        if click:
            for kind in ("mousePressed", "mouseReleased"):
                await self.send("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)

    async def shot(self, name):
        # 움직이는 도중에 찍지 않는다: 끝이 있는 움직임이 다 끝날 때까지 기다린다 (도는 표시처럼 끝없는 것은 빼고)
        try:
            await self.until("document.getAnimations().filter((a) => a.playState === 'running' && a.effect?.getComputedTiming().iterations !== Infinity).length === 0", timeout=3)
        except TimeoutError:
            print(f"  움직임이 3초 안에 끝나지 않았다 ({name})")
        await asyncio.sleep(0.05)
        data = (await self.send("Page.captureScreenshot", format="png"))["data"]
        path = OUT / f"{name}.png"
        path.write_bytes(base64.b64decode(data))
        wide, tall = await self.js("[document.documentElement.scrollWidth - innerWidth, document.documentElement.scrollHeight - innerHeight]")
        print(path, f"  가로 넘침 {wide}px" if wide > 0 else "", f"  세로 넘침 {tall}px" if tall > 0 else "",
              f"  스크립트 오류 {self.errors}" if self.errors else "", flush=True)
        self.shots += 1
        small = await self.js(SMALL_TEXT)
        if small:      # U4-1: 화면에 보이는 글 중 13px 아래, 또는 흐린 회색(--muted)은 없다 (예외: 단계 길의 아직 안 그린 쪽 이름, 입력창 안내 글은 글 줄이 아니다)
            print(f"  작은·흐린 글 {len(small)}개: {small[:4]}", flush=True)
            self.problems.append(f"{name}: 13px 아래 또는 흐린 회색 글 {len(small)}개 {small[:4]}")
        if wide > 0 or tall > 0 or self.errors:      # 넘침과 스크립트 오류는 끝에 모아 실패로 센다
            self.problems.append(f"{name}: 가로 넘침 {wide}px, 세로 넘침 {tall}px, 스크립트 오류 {list(self.errors)}")
        self.errors.clear()

    async def open(self, w, h):
        await self.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=SCALE, mobile=w < 600)
        await self.send("Page.navigate", url="about:blank")
        await self.until("location.href === 'about:blank'")
        self.failed.clear()
        await self.send("Page.navigate", url=BASE)
        try:
            await self.until("location.href.startsWith('http')")
            await self.until(f"document.readyState === 'complete' && document.fonts.status === 'loaded' && !!document.querySelector('#send svg') && !!document.querySelector('{EXAMPLE}')")
        except TimeoutError as e:      # 페이지가 안 열렸다: 어디서 멈췄는지 찍는다 (서버가 꺼졌나, 모듈이 깨졌나, 글꼴을 못 받았나)
            state = await self.js("[location.href, document.readyState, document.fonts.status, !!document.querySelector('#send svg'), document.scripts.length]")
            raise TimeoutError(f"page-load timeout ({w}x{h}, {BASE}): 기다린 것 {e}. 주소 {state[0]}, readyState {state[1]}, 글꼴 {state[2]}, "
                               f"보내기 단추 그림 {state[3]}, 스크립트 {state[4]}개. 스크립트 오류 {self.errors or '없음'}. 실패한 요청 {self.failed or '없음'}") from None





def chrome_port(prof, proc, timeout=15):
    """Chrome 을 디버깅 포트 0 으로 띄우면 비어 있는 포트를 골라 프로필 폴더의 DevToolsActivePort 첫 줄에 적는다."""
    f, end = Path(prof) / "DevToolsActivePort", time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError(f"Chrome 이 바로 꺼졌다 (종료 코드 {proc.returncode})")
        if f.exists() and f.read_text().strip():
            return int(f.read_text().split()[0])
        time.sleep(0.05)
    raise TimeoutError("Chrome 디버깅 포트를 받지 못했다 (DevToolsActivePort 가 생기지 않음)")



STACK = "document.getElementById('panel').dataset.stack"
ANNOUNCE = "document.getElementById('announce').textContent"
# 지금 보이는 쪽의 바닥 줄: [불렛 글들, 한 줄을 넘는 불렛 수, 단추 글들]
FOOT = """(() => { const f = document.querySelector('.page:not([hidden]):not([inert]) .foot');
  if (!f || f.hidden) return [[], 0, []];
  const lis = [...f.querySelectorAll('.bullets li')], lh = (x) => parseFloat(getComputedStyle(x).lineHeight);
  return [lis.map((x) => x.textContent), lis.filter((x) => x.scrollWidth > x.clientWidth + 1 || x.getBoundingClientRect().height > lh(x) * 1.5).length,
          [...f.querySelectorAll('.go')].map((x) => x.textContent)]; })()"""
# 쪽 그림 안의 문장 글 (사용자 11/19: 글은 바닥 줄 불렛 둘뿐). 그림의 이름표·범례·원문은 문장이 아니다
SENTENCES = """[...document.querySelectorAll('.chart-fact, .art-note, .m3-note, .adapt-goal, .adapt-jobs, .page-count, #thread, .msg')].filter((x) => x.getClientRects().length).length"""


async def foot_ok(p, page, buttons):
    bullets, long_, got = await p.js(FOOT)
    assert 1 <= len(bullets) <= 2, f"{page}: 불렛 {len(bullets)}개 {bullets}"
    assert long_ == 0, f"{page}: 한 줄을 넘는 불렛 {long_}개 {bullets}"
    assert got == buttons, f"{page}: 단추 {got} (기대 {buttons})"
    assert await p.js(SENTENCES) == 0, f"{page}: 쪽 그림 안에 문장 글이 있다"
    print(f"  {page} 불렛: {' / '.join(bullets)}  단추: {got}", flush=True)


# 근거 줄: [줄 수, 공고 문장이나 결과 쪽 문장이 빈 줄 수] (사용자 11/21: 결과마다 근거 문장)
EVIDENCE = """((sel) => { const rows = [...document.querySelectorAll(sel + ' .ev')];
  return [rows.length, rows.filter((r) => [...r.querySelectorAll('blockquote')].some((q) => !q.textContent.trim() || q.textContent === '근거 문장 없음')).length]; })"""


async def evidence_ok(p, page, sel, at_least=1):
    n, empty = await p.js(f"{EVIDENCE}({json.dumps(sel)})")
    assert n >= at_least and empty == 0, f"{page}: 근거 줄 {n}개, 문장이 빈 줄 {empty}개"
    # 원문 캡처는 찍은 크기(2배 그림의 절반)보다 크게 그리지 않는다: srcset 2x 만 두면 naturalWidth 가 그 크기다 (src 가 있으면 배율 1 화면에서 2배로 커진다)
    big = await p.js(f"""[...document.querySelectorAll({json.dumps(sel + ' .ev-shot img')})].filter((i) => i.getAttribute('src') || (i.complete && i.naturalWidth && i.getBoundingClientRect().width > i.naturalWidth + 1)).length""")
    assert big == 0, f"{page}: 찍은 크기보다 크게 그린 캡처 {big}개"
    zoom = await p.js(f"[document.querySelectorAll({json.dumps(sel + ' .ev-shot')}).length, document.querySelectorAll({json.dumps(sel + ' .ev-zoom')}).length]")
    assert zoom[0] == zoom[1], f"{page}: 캡처 {zoom[0]}개, 크게 보기 단추 {zoom[1]}개"
    print(f"  {page} 근거 줄 {n}개", flush=True)


async def press(p, label):
    """지금 쪽 바닥 줄에서 그 이름의 단추를 진짜 마우스로 누른다 (아래로 굴려 숨었으면 위로 굴린 것처럼 다시 꺼낸다)"""
    await p.js("document.querySelectorAll('.page[data-foot-away]').forEach((x) => delete x.dataset.footAway), true")
    await p.js(f"[...document.querySelectorAll('.page:not([hidden]):not([inert]) .go')].find((b) => b.textContent === {json.dumps(label)}).dataset.press = ''")
    await p.mouse(".go[data-press]")


# ④ 간트차트 막대 칸마다 작업 번호의 학기 주: {"W2": [2, 3], …}
WEEK_JOBS = """(() => { const at = {}; for (const c of document.querySelectorAll('#weeks-doc .g-bar .g-cell[data-lv]')) {
  (at[c.closest('.g-bar').dataset.id] ||= []).push(Number(c.dataset.w)); } return at; })()"""


async def report_matches_weeks(p, cap):
    """⑥ 이 고른 계획(cap)의 리포트인지: 쪽 그림 주소, 쪽 위 본문 한 줄, 하루 칸 숨김, ⑥ 의 작업 주(리포트를 그린 값)가 ④ 화면의 주 칸과 같은지"""
    await p.until(f"document.querySelector('#report-doc img')?.getAttribute('src').includes('.{cap}.1.png') && document.querySelector('#report-doc img').naturalWidth > 0", timeout=10)
    basis = await p.js("document.querySelector('#report-doc .rep-basis')?.textContent || ''")
    assert basis.startswith(f"한 주 {cap}시간 계획 기준"), f"⑥ 기준 줄 {basis!r}"
    assert await p.js("document.getElementById('budget').hidden"), "⑥ 에 하루 공부 시간 칸이 보인다"
    want_go = ["pptx 받기"] + (["PDF 받기"] if (DATA / f"{CASE}.report.{cap}.all.pdf").is_file() else [])      # 질문 전체 PDF 는 파일이 있는 계획에만
    got_go = await p.js("[...document.querySelectorAll('.page:not([hidden]) .go')].map((x) => x.textContent)")
    assert got_go == want_go, f"⑥ {cap}시간 받기 단추 {got_go} (기대 {want_go})"
    if len(want_go) == 2:
        href = await p.js("[...document.querySelectorAll('.page:not([hidden]) .go')].find((x) => x.textContent === 'PDF 받기').href")
        pdf = urllib.request.urlopen(href).read()
        assert pdf[:5] == b"%PDF-" and len(pdf) == (DATA / f"{CASE}.report.{cap}.all.pdf").stat().st_size, f"⑥ {cap}시간 PDF 받기 {href}"
    at = await p.js(WEEK_JOBS)
    for r in REPORT_FACTS(cap)["rows"]:
        for pk in r["packages"]:
            assert sorted(at.get(pk["id"], [])) == pk["weeks"], f"⑥ {r['n']}번 줄 {pk['id']} 주 {pk['weeks']} ≠ ④ {sorted(at.get(pk['id'], []))}"
    print(f"  ⑥ {cap}시간: {basis}", flush=True)


async def gantt_ok(p, d):
    """④ 간트차트가 계획 파일(d)과 같은지: 열 16개(학기 주), 시험 띠 둘, 작업 줄·막대 주·끝나는 주 마름모·교육자료 동그라미 수, 미룸 줄, 글 크기"""
    from demo.pipeline import sem_week
    assert await p.js("!document.querySelector('#weeks-doc .wk, #weeks-doc .wk-list, #weeks-doc .wk-sem')"), "④ 옛 주 칸이 남아 있다"
    assert await p.js("document.querySelectorAll('#weeks-doc .g-head').length") == 16, "④ 학기 주 열이 16개가 아니다"
    if not d:
        assert await p.js("document.querySelectorAll('#weeks-doc .g-bar').length") >= 1, "④ 막대가 없다"
        return
    weeks = [sem_week(k) for k in range(1, 13)]
    heads = await p.js("[...document.querySelectorAll('#weeks-doc button.g-head')].map((x) => Number(x.textContent))")
    assert heads == weeks, f"④ 주 머리 단추 {heads} (학기 주 {weeks})"
    exams = await p.js("[...document.querySelectorAll('#weeks-doc .g-exam')].map((x) => [x.textContent, getComputedStyle(x.firstChild).fontSize, getComputedStyle(x.firstChild).color, x.getBoundingClientRect().width > 80])")
    assert exams == [["중간고사", "16px", "rgb(43, 42, 39)", True], ["기말고사", "16px", "rgb(43, 42, 39)", True]], f"④ 시험 띠 {exams}"
    rows = await p.js("[...document.querySelectorAll('#weeks-doc .g-grid > .g-label[data-id]')].map((x) => x.dataset.id)")
    held = await p.js("[...document.querySelectorAll('#weeks-doc .g-held .g-label')].map((x) => x.dataset.id)")
    assert rows == d["assigned"] and held == [h["id"] for h in d["held"]], f"④ 작업 줄 {rows} / 미룸 {held} (계획 {d['assigned']} / {[h['id'] for h in d['held']]})"
    assert bool(held) == await p.js("!!document.querySelector('#weeks-doc .g-held')"), "④ 미룸 줄"
    want = {}
    for w in d["weeks"]:
        for a in w["activities"]:
            if a["kind"] == "project" and a["id"] in d["assigned"]:
                want.setdefault(a["id"], set()).add(sem_week(w["week"]))
    got = {k: set(v) for k, v in (await p.js(WEEK_JOBS)).items()}
    assert got == want, f"④ 막대 주 {got} ≠ 계획 {want}"
    dia = await p.js("[...document.querySelectorAll('#weeks-doc .g-bar .g-done')].map((x) => [x.closest('.g-bar').dataset.id, Number(x.closest('.g-cell').dataset.w)])")
    fin = sorted((t["task"], sem_week(w["week"])) for w in d["weeks"] for t in w["deliverables_completed"])
    assert sorted(map(tuple, dia)) == fin, f"④ 끝나는 주 마름모 {dia} ≠ 산출물 {fin}"
    learn = [a for w in d["weeks"] for a in w["activities"] if a["kind"] == "learning"]
    marks = await p.js("[document.querySelectorAll('#weeks-doc .g-grid .g-mark[data-peek=m]').length, document.querySelectorAll('#weeks-doc .g-grid .g-mark[data-picked]').length]")
    assert marks == [len(learn), sum(any("기존 배정" in t for t in a["why"]) for a in learn)], f"④ 교육자료 동그라미 {marks}"
    assert await p.js("[...document.querySelectorAll('#weeks-doc .g-key-item')].length") == 4, "④ 범례 항목이 넷이 아니다"
    # 한 화면: 간트차트(주 14·28시간 모두) 아래가 바닥 줄에 가리지 않는다 (1440×900)
    box = await p.js("(() => { const g = document.querySelector('#weeks-doc .g-grid').getBoundingClientRect(), f = document.querySelector('#foot-weeks').getBoundingClientRect(); return [g.bottom, f.top]; })()")
    assert box[0] <= box[1] + 1, f"④ 간트차트가 바닥 줄에 가려진다 {box}"
    print(f"  ④ 간트차트: 작업 {len(rows)}개 · 미룸 {len(held)}개 · 동그라미 {marks[0]}개 · 마름모 {len(dia)}개", flush=True)


async def peek_ok(p, d):
    """④ 옆 패널: 작업 막대 → 주 머리 → 교육자료 동그라미, 주소 #, 초점, 앞 열 가리지 않음, 역량 카드, Esc·바깥 누르기"""
    hidden = "document.querySelector('.peek').hidden"
    await p.mouse("#weeks-doc .g-bar[data-id='W2']")
    await p.until("!" + hidden + " && document.querySelector('.peek[data-open]')")
    await asyncio.sleep(0.4)
    assert await p.js("document.querySelector('.pk-title').textContent") == "W2 RAG 파이프라인", "④ 패널 제목"
    assert await p.js("location.hash") == "#w=W2" and await p.js("document.activeElement === document.querySelector('.pk-title')"), "④ 패널 주소·초점"
    assert await p.js("document.querySelector('.g-bar[data-id=W2]').getAttribute('aria-pressed')") == "true"
    secs = await p.js("[...document.querySelectorAll('.peek .pk-h')].map((x) => x.textContent)")
    assert secs[0] == "할 일" and "산출물" in secs and secs[3] == "완료" and "다루는 역량" in secs and "붙은 공부 자료" in secs and secs[2].startswith("총 "), f"④ 작업 패널 {secs}"
    gap = await p.js("[document.querySelector('.peek').getBoundingClientRect().left, document.querySelector('#weeks-doc .g-grid').getBoundingClientRect().right]")
    assert gap[1] <= gap[0] + 1, f"④ 패널이 간트차트를 가린다 {gap}"      # 쪽 글이 패널 너비만큼 비켜 있다
    await p.shot("08d-peek-w2")
    await p.mouse(".peek .wk-comp")      # 역량을 누르면 공고 원문 카드. Esc 는 카드만 닫는다
    await p.until("!document.querySelector('.comp-pop').hidden && document.querySelector('.comp-pop blockquote')?.textContent.length > 10", timeout=5)
    await p.shot("08b-weeks-comp")
    await p.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'})), true")
    assert await p.js("document.querySelector('.comp-pop').hidden") and not await p.js(hidden), "④ Esc 가 역량 카드가 아니라 패널을 닫았다"
    await p.mouse("#weeks-doc .g-head[data-id='9']")      # 다른 것을 누르면 닫지 않고 내용만
    await p.until("document.querySelector('.pk-title').textContent === '9주차'")
    assert not await p.js(hidden) and await p.js("location.hash") == "#week=9", "④ 주 패널로 안 바뀐다"
    secs = await p.js("[...document.querySelectorAll('.peek .pk-h')].map((x) => x.textContent)")
    assert secs[:3] == ["주간 목표", "방법", "이유"] and "이번 주 할 일 차례" in secs and "이번 주 끝나는 산출물" in secs, f"④ 주 패널 {secs}"
    await p.shot("08e-peek-week9")
    await p.mouse("#weeks-doc .g-mark[data-peek=m]")
    await p.until("/^#m=L/.test(location.hash)")
    secs = await p.js("[...document.querySelectorAll('.peek .pk-h')].map((x) => x.textContent)")
    assert "다루는 역량" in secs and "배정 근거" in secs, f"④ 자료 패널 {secs}"
    await p.shot("08f-peek-material")
    await p.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'})), true")
    await p.until(hidden, timeout=3)
    assert await p.js("location.hash") == "" and await p.js("document.activeElement?.classList.contains('g-mark')"), "④ Esc 뒤 주소·초점"
    await p.mouse("#weeks-doc .g-label[data-id='W3']")
    await p.until("!" + hidden)
    await p.mouse("#weeks-doc .wk-line")      # 바깥을 누르면 닫는다
    await p.until(hidden, timeout=3)
    print("  ④ 옆 패널 열기·바꾸기·Esc·바깥 누르기 확인", flush=True)


async def flow(p):
    await p.open(1440, 900)
    assert await p.js("!document.getElementById('thread') && !document.getElementById('chat')"), "대화 칸이 남아 있다"
    await p.shot("01-landing")
    await p.mouse(EXAMPLE)
    await p.until("document.querySelectorAll('#attachments .chip, #attachments > *').length > 0")
    # 형광펜: 첫 칠이 켜진 때부터 마지막 칠이 다 번질 때까지 (켜진 때 + 칠하기 전환 --t-paint) 1.5초 안. 화면 안에서 켜진 때를 적어 둔다
    await p.js("""window.__paint = []; new MutationObserver((ms) => ms.forEach(() => __paint.push(performance.now())))
      .observe(document.getElementById('doc'), {attributes: true, subtree: true, attributeFilter: ['data-painted']}); 1""")
    await p.mouse("#send")
    await p.until("/역량 \\d+개를 찾았어요/.test(" + ANNOUNCE + ")", timeout=20)
    span, ease, marks = await p.js("[Math.max(...__paint) - Math.min(...__paint), parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--t-paint')), document.querySelectorAll('#doc mark.hl').length]")
    painted = (span + ease) / 1000
    assert painted <= 1.5, f"형광펜 {marks}개를 다 칠하는 데 {painted:.2f}초 (1.5초 안이어야)"
    print(f"  형광펜 {marks}개를 {painted:.2f}초에 다 칠함", flush=True)
    cells = await p.js("document.querySelectorAll('#posting-cells .want-btn').length + Number((document.querySelector('.want-rest summary')?.textContent.match(/(\\d+)개/) || [0, 0])[1])")
    rows = await p.js("Number(" + ANNOUNCE + ".match(/역량 (\\d+)개/)[1])")
    assert cells == rows, f"① 역량 목록 {cells}개, 찾은 역량 {rows}개"
    quotes = await p.js("[...document.querySelectorAll('[data-tier=\"필수\"] .want')].filter((li) => !li.querySelector('.want-q')?.textContent.trim()).length")
    assert quotes == 0, f"① 공고 문장이 없는 필수 역량 {quotes}개"
    await foot_ok(p, "①", ["이 역량으로 프로젝트 찾기 →"])
    await p.shot("02-posting")
    await press(p, "이 역량으로 프로젝트 찾기 →")      # 다음 단계는 바닥 줄 단추로 (사용자 11/21)
    await p.until("document.getElementById('search-doc').dataset.stage === 'scan'", timeout=15)
    await asyncio.sleep(0.5)
    blue = await p.js("[...document.querySelectorAll('#search-doc .field .dot[data-picked]')].filter((d) => getComputedStyle(d).backgroundColor === 'rgb(47, 111, 222)').length")
    want = round(PROJECT["counts"]["pool"] / 100)
    assert blue == want, f"② 파란 점 {blue}개 (낱말로 모은 후보 {PROJECT['counts']['pool']:,}개 = {want}개)"
    await p.shot("03-search-scan")
    await p.until("document.getElementById('search-doc').dataset.stage === 'judge'")
    await asyncio.sleep(1.0)
    await p.shot("04-search-judge")
    # ② 는 최종 응용 프로젝트 하나 (사용자 11/21): 찾기가 끝나면 같은 쪽에 응용 카드와 역량마다 근거 줄, 채운 줄이 "없음 → 다룸" 으로 바뀐다
    await p.until(STACK + ".endsWith('search') && document.querySelector('#search-doc .rs-gain[data-on]')", timeout=40)
    await p.send("Page.captureScreenshot", format="png")      # 능력치 효과가 도는 중 (움직임이 끝나기를 기다리지 않고 바로 찍는다)
    data = (await p.send("Page.captureScreenshot", format="png"))["data"]
    (OUT / "05a-adapted-filling.png").write_bytes(base64.b64decode(data))
    await p.until("/응용 프로젝트는/.test(" + ANNOUNCE + ") && document.querySelector('#foot-search .go')", timeout=30)
    # 응용 +1 은 몇 개든 1.5초 남짓에 다 튼다 (사용자 11/21: "+1 되는거 좀 느린듯"): 끝 알림 뒤 2.5초 안에 큰 숫자가 바닥 줄의 마지막 셈과 같다
    await p.until("""(() => { const b = [...document.querySelectorAll('#search-doc .rs-scores b')];
      return b.length === 2 && b.every((x) => x.dataset.after && x.textContent === x.dataset.after); })()""", timeout=2.5)
    # 숫자마다 무엇을 셌는지 (디자이너 2차 11/21): 바닥 줄 "공개 프로젝트 N개에서 …" / "필수 역량 …" · "우대 역량 …", 점수 줄 "필수 역량 8개 중 바탕 5.5개 → 빌려서 8개"
    foot2 = await p.js("[...document.querySelectorAll('#foot-search .bullets li')].map((x) => x.textContent)")
    assert foot2[0].startswith("공개 프로젝트 ") and "필수 역량 " in foot2[1] and "우대 역량 " in foot2[1] and "." not in foot2[1], f"② 바닥 줄 {foot2}"
    sc = await p.js("[...document.querySelectorAll('#search-doc .rs-score')].map((x) => { const c = x.cloneNode(true); c.querySelectorAll('.rs-gain').forEach((g) => g.remove()); return c.textContent; })")
    assert sc and all("개 중" in x and "바탕 " in x and "빌려서" in x and x.rstrip().endswith("개") for x in sc), f"② 점수 줄 {sc}"
    await foot_ok(p, "②", ["교육자료 찾기 →"])
    await evidence_ok(p, "② 최종 응용", "#search-doc")
    assert await p.js("!document.querySelector('#search-doc .rs-rivals') && !document.getElementById('page-sample')"), "② 에 1위 카드나 ③ 쪽이 남아 있다"
    await p.shot("05b-adapted")
    await press(p, "교육자료 찾기 →")
    await p.until("/교육자료 \\d+개를 골랐어요/.test(" + ANNOUNCE + ")", timeout=30)
    await foot_ok(p, "④", ["12주 계획 짜기 →"])
    states = await p.js("[...document.querySelectorAll('#materials-doc .flow .stop')].map((x) => x.dataset.state)")
    assert states and states[-1] == "end", f"④ 숫자 흐름 {states}"
    await evidence_ok(p, "④ 교육자료", "#materials-doc", 3)
    await p.shot("07-materials")
    await press(p, "12주 계획 짜기 →")
    await p.until("/주 계획을 짰어요/.test(" + ANNOUNCE + ")", timeout=30)
    await foot_ok(p, "⑤", ["정리 리포트 만들기 →"])
    await gantt_ok(p, PLAN)
    await p.shot("08-weeks")
    if len(BUTTONS) > 1:      # 한 주 공부 시간 고르기: 7 · 14(기본) · 28. 고른 다음 기본으로 돌아온다. 분량 한 줄, 보류 글, 바닥 줄이 고른 계획을 따른다
        assert await p.js("document.getElementById('budget').hidden && document.querySelectorAll('#weeks-doc input[type=radio]').length === " + str(len(BUTTONS))), \
            "④ 에 시간 고르기가 하나가 아니다 (하루 1·2·3시간 칸이 보인다)"
        labels = await p.js("[...document.querySelectorAll('#weeks-doc .plan-pick label')].map((x) => x.textContent)")
        assert labels == [f"주 {h}시간" for h in BUTTONS], f"④ 단추 {labels}"
        name = await p.js("document.querySelector('#weeks-doc .plan-name')?.textContent")
        assert name == "한 주 공부 시간", f"④ 시간 고르기 이름 {name!r}"
        checked = await p.js("document.querySelector('#weeks-doc .plan-pick input:checked')?.value")
        assert checked == f"{PLAN['constraints']['hours_per_week']:g}", f"④ 기본 계획 {checked}"
        await peek_ok(p, PLAN)      # 옆 패널: 열기·바꾸기·닫기·주소·초점
        for cap in [h for h in BUTTONS if h != checked] + [checked]:
            d = next((x for x in PLANS if f"{x['constraints']['hours_per_week']:g}" == cap), None)
            await p.mouse(f"#weeks-doc .plan-pick input[value='{cap}']")
            if d is None:      # 보류한 시간: 간트차트 없이 본문 글 셋, 바닥 줄은 보류와 최소 시간
                b = next(x for x in BLOCKED if f"{x['hours_per_week']:g}" == cap)
                await p.until(f"/한 주 {cap}시간으로는 12주 계획을 보류했어요/.test(document.querySelector('#foot-weeks').textContent)", timeout=5)
                note = await p.js("[document.querySelector('#weeks-doc .g-scroll').hidden, document.querySelector('#weeks-doc .wk-line').textContent, document.querySelector('#weeks-doc .wk-blocked')?.textContent || '', document.querySelector('#foot-weeks').textContent, document.querySelector('#weeks-doc .g-key').hidden]")
                assert note[0] and note[4] and not note[1] and f"{b['needed_minutes'] // 60}시간" in note[2] and "11시간 40분" not in note[2] and "11시간 40분" in note[3], f"④ {cap}시간 보류 글 {note}"      # 최소 시간은 바닥 줄에만
                await p.shot(f"08c-weeks-{cap}h")
                continue
            await p.until(f"document.querySelector('#weeks-doc .wk-line').textContent.includes('주 {cap}시간이면')", timeout=5)
            await p.until(f"/한 주 {cap}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=5)
            assert await p.js("!document.querySelector('#weeks-doc .wk-blocked') && !document.querySelector('#weeks-doc .g-scroll').hidden"), f"④ {cap}시간에 보류 글이 남아 있다"
            line = await p.js("document.querySelector('#weeks-doc .wk-line').textContent")
            want = (f"작업 {len(d['held'])}개는 12주 뒤로 미뤄요 (" + ", ".join(f"{h['id']} {h['name']}" for h in d["held"]) + ")") if d["held"] else f"작업 {len(d['assigned'])}개가 모두 12주 안에 들어가요"
            assert line == f"주 {cap}시간이면 " + want, f"④ 분량 줄 {line!r}"
            await gantt_ok(p, d)
            if d is not PLAN:
                await p.shot(f"08c-weeks-{cap}h")
    if len(PLANS) < 2:      # 하루 공부 시간 칸이 ④ 에 있는 예시: 리포트 전에 바꿔도 단추가 남는다 (사용자 11/21: 리포트로 안 넘어감)
        cap = {1: "7", 2: "14"} if not PLAN else {k: f"{PLAN['constraints']['hours_per_week']:g}" for k in (1, 2)}      # md 계획 하나면 시간을 바꿔도 그대로
        await p.mouse("#budget label:nth-of-type(2) input")
        await asyncio.sleep(1.5 if PLAN else 0)
        await p.until(f"/한 주 {cap[2]}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=10)
        await foot_ok(p, "⑤ 바꾼 뒤", ["정리 리포트 만들기 →"])
        await p.mouse("#budget label:nth-of-type(1) input")
        await asyncio.sleep(1.5 if PLAN else 0)
        await p.until(f"/한 주 {cap[1]}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=10)
    await press(p, "정리 리포트 만들기 →")
    await p.until("/정리 리포트를 만들었어요/.test(" + ANNOUNCE + ")", timeout=30)
    await p.until("document.querySelector('#report-doc img')?.complete && document.querySelector('#report-doc img').naturalWidth > 0")
    await foot_ok(p, "⑥", ["pptx 받기"] + (["PDF 받기"] if (DATA / f"{CASE}.report.{PLAN['constraints']['hours_per_week'] if PLAN else 84:g}.all.pdf").is_file() else []))
    pptx = await p.js("document.querySelector('.page:not([hidden]) .go').href")
    assert urllib.request.urlopen(pptx).read(2) == b"PK", f"pptx 받기 {pptx}"      # pptx 는 zip
    n = await p.js("document.querySelectorAll('#report-doc .sheet img').length")
    assert n >= 3, f"⑥ 슬라이드 {n}장"
    await p.shot("09-report")
    await p.js("document.getElementById('report-doc').scrollTop = 99999")
    await p.shot("10-report-bottom")

    if PLAN and len(BUTTONS) > 1:      # ⑥ 은 ④ 에서 고른 한 주 공부 시간의 계획: 하루 칸이 없고, 쪽 위 본문 한 줄이 그 계획을 말하고, 주는 ④ 와 같다
        await report_matches_weeks(p, checked)
        for cap in [h for h in BUTTONS if h != checked] + [checked]:
            await p.mouse("#panel-path button[data-to='weeks']")
            await p.until(STACK + ".endsWith('weeks')")
            await p.mouse(f"#weeks-doc .plan-pick input[value='{cap}']")
            await p.mouse("#panel-path button[data-to='report']")
            await p.until(STACK + ".endsWith('report')")
            if any(f"{b['hours_per_week']:g}" == cap for b in BLOCKED):      # 보류한 시간: 리포트 대신 본문 글
                await p.until("/보류/.test(document.querySelector('#report-doc .rep-note')?.textContent || '')", timeout=10)
                assert await p.js("!document.querySelector('#report-doc img') && document.getElementById('budget').hidden"), f"⑥ {cap}시간에 쪽 그림이나 하루 칸이 남았다"
                await p.shot(f"11-report-{cap}h")
                continue
            await report_matches_weeks(p, cap)
            if cap != checked:
                await p.shot(f"11-report-{cap}h")
    else:      # 공부 시간 바꾸기: ⑥ 쪽 그림이 그 안의 쪽으로 바뀐다
        before = await p.js("document.querySelector('#report-doc img').getAttribute('src')")
        await p.mouse("#budget label:nth-of-type(2) input")
        await p.until(f"document.querySelector('#report-doc img') && document.querySelector('#report-doc img').getAttribute('src') !== {json.dumps(before)}", timeout=10)
        await p.shot("11-report-budget")
    await p.mouse("#panel-path button[data-to='search']")
    await p.until(STACK + ".endsWith('search')")
    await foot_ok(p, "②", [])
    await p.shot("06-search-done")
    await p.mouse("#panel-path button[data-to='weeks']")
    await p.until(STACK + ".endsWith('weeks')")
    await foot_ok(p, "⑤ 바꾼 뒤", [])
    if len(PLANS) > 1:      # ⑥ 에서 하루 공부 시간을 바꿔도 ④ 는 고른 한 주 공부 시간 그대로, 하루 칸은 ④ 에서 숨는다
        assert await p.js("document.getElementById('budget').hidden"), "⑤ 로 돌아오니 하루 공부 시간 칸이 보인다"
        await p.until(f"/한 주 {PLAN['constraints']['hours_per_week']:g}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=5)
    await p.shot("12-weeks-budget")

    await p.mouse("#new-chat")
    await p.until("document.getElementById('app').dataset.empty === 'true' && document.getElementById('panel').hidden")
    await p.shot("13-new-posting")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        urllib.request.urlopen(BASE, timeout=5).read(1)
    except OSError as e:
        raise SystemExit(f"서버에 닿지 않는다: {BASE} ({e}). 먼저 `python -m demo --port …` 로 띄운다")
    prof = tempfile.mkdtemp(prefix="demo-shots-")
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=0",
                             f"--user-data-dir={prof}", "--window-size=1440,900", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p = None
    try:
        port = chrome_port(prof, proc)
        pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list").read())
        url = next(x["webSocketDebuggerUrl"] for x in pages if x["type"] == "page")
        async with websockets.connect(url, max_size=None) as ws:
            p = Page(ws)
            for m in ("Page.enable", "Runtime.enable", "Network.enable"):
                await p.send(m)
            try:
                await flow(p)
            except (AssertionError, TimeoutError):
                data = (await p.send("Page.captureScreenshot", format="png"))["data"]
                (OUT / "fail.png").write_bytes(base64.b64decode(data))
                print(f"검사가 어긋난 화면: {OUT / 'fail.png'}  스크립트 오류 {p.errors}", flush=True)
                raise
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(prof, ignore_errors=True)
        print(f"사진 {p.shots if p else 0}장, {time.time() - started:.0f}초 ({BASE}, {CASE})", flush=True)
    if p.problems:
        print("넘침·스크립트 오류·작은 글:", *p.problems, sep="\n  ")
        raise SystemExit(1)
    print("끝: 검사 실패 없음, 넘침 없음, 스크립트 오류 없음")


if __name__ == "__main__":
    asyncio.run(main())
