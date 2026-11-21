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
PLANS = sorted((json.loads(f.read_text(encoding="utf-8")) for f in DATA.glob(f"{CASE}.plan.*.json")), key=lambda d: d["constraints"]["hours_per_week"])
PLAN = next((d for d in PLANS if d.get("size") == "중"), PLANS[0] if PLANS else None)      # 주차 계획 md (기본 중): ⑤ 는 공부 시간과 상관없다

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
    print(f"  {page} 근거 줄 {n}개", flush=True)


async def press(p, label):
    """지금 쪽 바닥 줄에서 그 이름의 단추를 진짜 마우스로 누른다 (아래로 굴려 숨었으면 위로 굴린 것처럼 다시 꺼낸다)"""
    await p.js("document.querySelectorAll('.page[data-foot-away]').forEach((x) => delete x.dataset.footAway), true")
    await p.js(f"[...document.querySelectorAll('.page:not([hidden]):not([inert]) .go')].find((b) => b.textContent === {json.dumps(label)}).dataset.press = ''")
    await p.mouse(".go[data-press]")


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
    weeks_n = await p.js("document.querySelectorAll('#weeks-doc .wk').length")
    items_n = await p.js("document.querySelectorAll('#weeks-doc .wk-item').length")
    assert weeks_n == 12 and items_n >= 12, f"⑤ 주 칸 {weeks_n}개, 할 일 {items_n}개"
    if PLAN:
        outs = await p.js("document.querySelectorAll('#weeks-doc .wk-out').length")
        n_out = sum(len(w["deliverables_completed"]) for w in PLAN["weeks"])
        assert outs == n_out, f"⑤ 산출물 줄 {outs}개 ≠ 계획 {n_out}개"
        goal = await p.js("document.querySelector('#weeks-doc .wk-body dd li')?.textContent")
        assert goal == PLAN["weeks"][0]["goal"], f"⑤ 1주 목표 {goal!r}"
    await p.shot("08-weeks")
    if len(PLANS) > 1:      # 계획 크기 고르기: 중(기본) → 대 → 중. 주 칸 머리의 상한, 보류 작업 줄, 바닥 줄이 고른 계획을 따른다
        checked = await p.js("document.querySelector('#weeks-doc .plan-pick input:checked')?.value")
        assert checked == f"{PLAN['constraints']['hours_per_week']:g}", f"⑤ 기본 계획 {checked}"
        for d in [x for x in PLANS if x is not PLAN] + [PLAN]:
            cap = f"{d['constraints']['hours_per_week']:g}"
            await p.mouse(f"#weeks-doc .plan-pick input[value='{cap}']")
            await p.until(f"document.querySelector('#weeks-doc .wk-used').textContent.endsWith('상한 {cap}시간')", timeout=5)
            await p.until(f"/한 주 {cap}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=5)
            held = await p.js("document.querySelector('#weeks-doc .wk-held').textContent")
            want = "보류 작업 · " + (", ".join(f"{h['id']} {h['name']}" for h in d["held"]) or "없음")
            assert held == want, f"⑤ 보류 줄 {held!r} ≠ {want!r}"
            outs = await p.js("document.querySelectorAll('#weeks-doc .wk-out').length")
            assert outs == sum(len(w["deliverables_completed"]) for w in d["weeks"]), f"⑤ {cap}시간 산출물 줄 {outs}개"
            if d is not PLAN:
                await p.shot(f"08c-weeks-{d.get('size') or cap}")
    await p.js("document.querySelector('#weeks-doc .wk-more').open = true, true")      # 토글: 목표·할 일·배우는 역량, 줄마다 세 줄까지
    lines = await p.js("[...document.querySelectorAll('#weeks-doc .wk-more[open] .wk-lines')].map((u) => u.children.length)")
    assert lines and all(1 <= n <= 3 for n in lines), f"⑤ 토글 줄 수 {lines}"
    await p.mouse("#weeks-doc .wk-more[open] .wk-comp")      # 역량을 누르면 공고 원문 카드
    await p.until("!document.querySelector('.comp-pop').hidden && document.querySelector('.comp-pop blockquote')?.textContent.length > 10", timeout=5)
    await p.shot("08b-weeks-comp")
    await p.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'})), true")
    assert await p.js("document.querySelector('.comp-pop').hidden"), "⑤ 원문 카드가 Esc 로 닫히지 않음"
    await p.js("document.querySelector('#weeks-doc .wk-more').open = false, true")
    cap = {1: "7", 2: "14"} if not PLAN else {k: f"{PLAN['constraints']['hours_per_week']:g}" for k in (1, 2)}      # md 계획은 시간을 바꿔도 그대로
    await p.mouse("#budget label:nth-of-type(2) input")      # 리포트 전에 공부 시간을 바꿔도 단추가 남는다 (사용자 11/21: 리포트로 안 넘어감)
    await asyncio.sleep(1.5 if PLAN else 0)
    await p.until(f"/한 주 {cap[2]}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=10)
    await foot_ok(p, "⑤ 바꾼 뒤", ["정리 리포트 만들기 →"])
    await p.mouse("#budget label:nth-of-type(1) input")
    await asyncio.sleep(1.5 if PLAN else 0)
    await p.until(f"/한 주 {cap[1]}시간까지/.test(document.querySelector('#foot-weeks').textContent)", timeout=10)
    await press(p, "정리 리포트 만들기 →")
    await p.until("/정리 리포트를 만들었어요/.test(" + ANNOUNCE + ")", timeout=30)
    await p.until("document.querySelector('#report-doc img')?.complete && document.querySelector('#report-doc img').naturalWidth > 0")
    await foot_ok(p, "⑥", ["pptx 받기"])
    pptx = await p.js("document.querySelector('.page:not([hidden]) .go').href")
    assert urllib.request.urlopen(pptx).read(2) == b"PK", f"pptx 받기 {pptx}"      # pptx 는 zip
    n = await p.js("document.querySelectorAll('#report-doc .sheet img').length")
    assert n >= 3, f"⑥ 슬라이드 {n}장"
    await p.shot("09-report")
    await p.js("document.getElementById('report-doc').scrollTop = 99999")
    await p.shot("10-report-bottom")

    # 공부 시간 바꾸기: ⑥ 쪽 그림이 그 안의 쪽으로 바뀐다
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
