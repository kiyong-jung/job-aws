"""① 공고 읽기: 실제 공고 사이트 화면 한 장과 핵심 문장의 자리 (사용자 11/21: 실제 캡처본 위에 형광펜).
  PYTHONPATH=. .venv/bin/python demo/design/build_posting_shot.py <예시> <공고 주소>
→ demo/data/<예시>.posting.png (페이지 전체, 2배) · .posting.json {url, width, height, marks: {문장 번호: [[왼, 위, 너비, 높이], …]}, missing: [번호]}.
공고 쪽은 한 번만 연다 (robots.txt 가 허용하는 경로만, 사용자 에이전트 "Mozilla/5.0 (research collector)"). 모델 호출 없음.
문장 찾기: 페이지에서 그 문장의 앞 40자를 브라우저 찾기(window.find)로 찾고, 문장 길이만큼 고름을 늘려 그 줄들의 사각형을 적는다.
못 찾은 문장은 missing 에 남긴다 (화면은 그 형광펜을 원문 글 쪽에서만 칠한다)."""
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

from demo.pipeline import DATA, example_case, plan

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W = 1280
FIND = """((items) => { const out = {}, missing = [];
  for (const [n, text] of items) {
    const t = text.replace(/\\s+/g, ' ').trim(); let hit = false;
    for (const len of [t.length, 80, 40, 24]) {
      const head = t.slice(0, len); if (head.length < 12 && len !== t.length) continue;
      getSelection().removeAllRanges(); scrollTo(0, 0);
      if (!window.find(head, false, false, true)) continue;
      const sel = getSelection(); for (let i = head.length; i < t.length; i++) sel.modify('extend', 'forward', 'character');
      const rs = [...sel.getRangeAt(0).getClientRects()].filter((b) => b.width > 2 && b.height > 4)
        .map((b) => [Math.round(b.left + scrollX), Math.round(b.top + scrollY), Math.round(b.width), Math.round(b.height)]);
      if (rs.length) { out[n] = rs; hit = true; break; }
    }
    if (!hit) missing.push(n);
  }
  getSelection().removeAllRanges(); scrollTo(0, 0);
  return {marks: out, missing, height: document.documentElement.scrollHeight}; })"""


async def main(case, url):
    c = example_case(case)
    text = {s["id"]: s["text"] for s in c["sentences"]}
    marks, _ = plan(c["sentences"], c["competencies"])
    items = [[m["n"], text[m["sid"]]] for m in marks]
    prof = tempfile.mkdtemp()
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-port=0", f"--user-data-dir={prof}",
                             "--user-agent=Mozilla/5.0 (research collector)", f"--window-size={W},900", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f = Path(prof) / "DevToolsActivePort"
    while not f.exists() or not f.read_text().strip():
        time.sleep(0.1)
    port = int(f.read_text().split()[0])
    ws_url = next(x["webSocketDebuggerUrl"] for x in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list").read()) if x["type"] == "page")
    n = 0
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
                if "exceptionDetails" in r:
                    raise RuntimeError(r["exceptionDetails"])
                return r["result"].get("value")
            await send("Page.enable")
            await send("Emulation.setDeviceMetricsOverride", width=W, height=900, deviceScaleFactor=2, mobile=False)
            await send("Page.navigate", url=url)
            for _ in range(150):
                if await js("document.readyState") == "complete":
                    break
                await asyncio.sleep(0.2)
            await asyncio.sleep(4)
            got = await js(FIND + "(" + json.dumps(items, ensure_ascii=False) + ")")
            h = got["height"]
            await send("Emulation.setDeviceMetricsOverride", width=W, height=h, deviceScaleFactor=2, mobile=False)      # 한 번에 찍게 화면을 페이지 높이로
            await asyncio.sleep(1.5)
            png = base64.b64decode((await send("Page.captureScreenshot", format="png"))["data"])
    finally:
        proc.terminate()
    (DATA / f"{case}.posting.png").write_bytes(png)
    meta = {"url": url, "width": W, "height": h, "marks": got["marks"], "missing": got["missing"]}
    (DATA / f"{case}.posting.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(case, f"문장 {len(items)}개 중 {len(got['marks'])}개 찾음 · 못 찾음 {got['missing']} · 높이 {h}px")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
