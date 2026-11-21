"""근거 구절의 원문 캡처 (사용자 11/21: 프로젝트·교육자료 근거는 실제 README·자료 원문 캡처에 근거해야 한다).
  PYTHONPATH=. python -m demo.design.build_proof_shots <예시> [<예시> …]
② 최종 응용의 근거 줄(1위·빌린 프로젝트 README)과 ③ 교육자료의 근거 구절마다, 그 원문 페이지를 한 번 열어 구절을 찾고
구절 둘레만 잘라 형광펜 칸을 그린 PNG 로 둔다 → demo/data/proof/<id>.png, 표는 demo/data/proof/index.json {"<주소>\\t<구절>": id}.
robots.txt 가 허용하는 주소만, 호스트마다 한 번에 하나씩 연다 (사용자 에이전트 "Mozilla/5.0 (research collector)"). 모델 호출 없음.
구절을 못 찾은 줄(노트북 안 글 등)은 캡처 없이 남긴다 (화면은 글과 원문 링크만)."""
import asyncio
import base64
import hashlib
import re
import io
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import websockets
from PIL import Image, ImageDraw

from demo import pipeline as P

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = "Mozilla/5.0 (research collector)"
OUT = P.DATA / "proof"
W, CW, CH = 1280, 960, 300       # 페이지 너비, 자른 칸 (CSS px)
FIND = """((head, len) => { getSelection().removeAllRanges(); scrollTo(0, 0);
  if (!window.find(head, false, false, true)) return null;
  const sel = getSelection();
  for (let i = head.length; i < len; i++) sel.modify('extend', 'forward', 'character');
  const range = sel.getRangeAt(0);
  const r = [...range.getClientRects()].filter((b) => b.width > 2).map((b) => [b.left + scrollX, b.top + scrollY, b.width, b.height]);
  let el = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
  while (el && !/^(P|LI|TD|BLOCKQUOTE|H[1-6]|DD|ARTICLE)$/.test(el.tagName) && getComputedStyle(el).display === 'inline') el = el.parentElement;
  const b = el.getBoundingClientRect();
  sel.removeAllRanges();
  return r.length ? { rects: r, block: [b.left + scrollX, b.top + scrollY, b.width, b.height] } : null; })"""


def pairs(case_name):
    case = P.example_case(case_name)
    out = []
    for e in P.project(case, speed=0):
        if e["type"] == "adapt":
            out += [(r["url"], r["proof"]) for r in e["rows"] if r.get("url") and r.get("proof") and r["from"] != P.AI_ADDED]
    for e in P.materials(case, speed=0):
        if e["type"] == "pick":
            out += [(e["row"]["url"], c["quote"]) for c in e["row"]["covers"] if c.get("quote")]
    return out


def allowed(url, cache={}):
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host not in cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA})
            rp.parse(urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace").splitlines())
        except Exception:
            rp.parse([])
        cache[host] = rp
    return cache[host].can_fetch(UA, url)


def pieces(quote):
    """찾을 조각: 구절을 …·*·-·· 로 끊은 조각마다 (긴 것부터). 조각마다 (머리 60자, 조각 길이)"""
    parts = [p.strip() for p in re.split(r"\.\.\.|…| \* | - | · ", quote) if len(p.strip()) >= 12]
    parts = sorted(parts or [quote], key=len, reverse=True)
    return [(p[:60], len(p)) for p in parts] + [(p[:30], len(p)) for p in parts]


def capture_url(url):
    """GitHub 의 .ipynb 는 다른 도메인 틀 안에 그려져 찾을 수 없다: 같은 노트북을 그리는 nbviewer 로 연다 (robots 허용)"""
    m = re.match(r"https://github\.com/(.+\.ipynb)$", url)
    return f"https://nbviewer.org/github/{m.group(1)}" if m else url


async def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    index_f = OUT / "index.json"
    index = json.loads(index_f.read_text("utf-8")) if index_f.exists() else {}
    todo = {}
    for n in names:
        for url, q in pairs(n):
            todo.setdefault(url, set()).add(q)
    prof = tempfile.mkdtemp()
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=0", f"--user-data-dir={prof}",
                             f"--user-agent={UA}", f"--window-size={W},900", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f = Path(prof) / "DevToolsActivePort"
    while not f.exists() or not f.read_text().strip():
        time.sleep(0.1)
    port = int(f.read_text().split()[0])
    ws_url = next(x["webSocketDebuggerUrl"] for x in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list").read()) if x["type"] == "page")
    n = 0
    got = miss = 0
    try:
        async with websockets.connect(ws_url, max_size=None) as ws:
            async def send(method, **params):
                nonlocal n
                n += 1
                await ws.send(json.dumps({"id": n, "method": method, "params": params}))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("id") == n:
                        return m.get("result", {})

            async def js(e):
                r = await send("Runtime.evaluate", expression=e, returnByValue=True, awaitPromise=True)
                return r.get("result", {}).get("value")
            await send("Page.enable")
            await send("Emulation.setDeviceMetricsOverride", width=W, height=900, deviceScaleFactor=2, mobile=False)
            last = {}
            for url, quotes in todo.items():
                page_url = capture_url(url)
                if not allowed(page_url):
                    print("robots 막힘:", url)
                    continue
                host = urlparse(page_url).netloc
                wait = 1.0 - (time.time() - last.get(host, 0))
                if wait > 0:
                    await asyncio.sleep(wait)
                last[host] = time.time()
                await send("Page.navigate", url=page_url)
                for _ in range(100):
                    if await js("document.readyState") == "complete":
                        break
                    await asyncio.sleep(0.2)
                await asyncio.sleep(2.5)
                for q in quotes:
                    key = f"{url}\t{q}"
                    if key in index and (OUT / f"{index[key]}.png").exists():
                        continue
                    found = None
                    for h, n_ in pieces(q):
                        found = await js(FIND + "(" + json.dumps(h) + "," + str(n_) + ")")
                        if found:
                            break
                    if not found:
                        miss += 1
                        print("  못 찾음:", url[:60], "|", q[:50])
                        continue
                    rects, (bx, by, bw, bh) = found["rects"], found["block"]
                    cx = max(0, bx - 16)                          # 구절이 든 문단 전체 (왼쪽이 잘리지 않게)
                    cw = min(W - cx, max(bw + 32, 560), CW)
                    cy = max(0, min(by, rects[0][1]) - 40)
                    ch = min(max(bh, rects[-1][1] + rects[-1][3] - cy) + 80, CH + 120)
                    shot = await send("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                                      clip={"x": cx, "y": cy, "width": cw, "height": ch, "scale": 1})
                    im = Image.open(io.BytesIO(base64.b64decode(shot["data"]))).convert("RGBA")
                    k = im.width / cw                             # 화면 배율(2) × 찍기 배율
                    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
                    d = ImageDraw.Draw(layer)
                    for x, y, w, h in rects[:8]:      # 찾은 줄들에 형광펜 (반투명 노랑)
                        d.rectangle([(x - cx) * k, (y - cy) * k, (x - cx + w) * k, (y - cy + h) * k], fill=(253, 224, 71, 90), outline=(234, 179, 8, 255), width=3)
                    out = Image.alpha_composite(im, layer).convert("RGB")
                    pid = hashlib.sha1(key.encode()).hexdigest()[:12]
                    out.save(OUT / f"{pid}.png", optimize=True)
                    index[key] = pid
                    got += 1
    finally:
        proc.terminate()
    index_f.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"캡처 {got}개, 못 찾음 {miss}개 → {OUT}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["aws_fde", "naver_ml_intern"]))
