"""데모를 서버 없는 정적 사이트로 만든다 (GitHub Pages).
  PYTHONPATH=. python -m demo.export_static [만들 폴더, 기본 site]
예시 공고마다 단계별 사건(서버가 보내던 것)을 미리 돌려 data/runs/<예시>.<단계>[.<공부 시간>].json 으로 두고,
화면(api.js 의 정적 판)이 그 파일을 같은 간격으로 다시 튼다. 사건마다 wait 는 그 사건 앞에서 서버가 쉬던 초다.
주소는 모두 상대 주소로 바꾼다 (Pages 는 /<레포 이름>/ 아래에서 열린다). 모델·네트워크를 부르지 않는다."""
import json
import shutil
import sys
import time
from pathlib import Path

from demo import pipeline, server

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


def record(req):
    """요청 하나 → [{wait, ...사건}]. 서버의 쉬는 시간(time.sleep)을 재지 않고 적어 둔다."""
    waits, out = [0.0], []
    real = time.sleep
    time.sleep = lambda s: waits.__setitem__(0, waits[0] + s)
    try:
        for ev in server.events(req, live_mode=False, default_speed=1.0):
            out.append({"wait": round(waits[0], 3), **ev})
            waits[0] = 0.0
    finally:
        time.sleep = real
    text = json.dumps(out, ensure_ascii=False).replace('"/posting/', '"posting/').replace('"/report/', '"report/').replace('"/proof/', '"proof/')
    return text


def main(out):
    if out.exists():
        shutil.rmtree(out)
    (out / "data" / "runs").mkdir(parents=True)
    for f in STATIC.rglob("*"):
        if f.is_dir() or "HALUNA" in f.name:      # 받은 상용 글꼴은 싣지 않는다
            continue
        to = out / "static" / f.relative_to(STATIC)
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, to)
    for css in (out / "static").rglob("*.css"):      # 싣지 않은 글꼴의 @font-face 를 뺀다 (서버가 하던 일)
        css.write_text(server.without_missing_fonts(css.read_text(encoding="utf-8"), css), encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8").replace('"/static/', '"static/')
    html = html.replace("<head>", '<head>\n  <meta name="demo-static" content="1">', 1)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / ".nojekyll").write_text("")
    if (pipeline.DATA / "proof").is_dir():      # 근거 구절의 원문 캡처
        shutil.copytree(pipeline.DATA / "proof", out / "proof", ignore=shutil.ignore_patterns("*.json"))

    examples = [server.example(name) for name in pipeline.examples()]
    for ex in examples:      # 2~5단계 요청은 원문 대신 ① 의 문장을 이은 글을 보낸다 (main.js store.text). 화면이 그 글로도 예시를 찾게 둔다
        posting = next(e for e in json.loads(record({"text": ex["text"]})) if e["type"] == "posting")
        ex["steps_text"] = "\n".join(x["text"] for sec in posting["sections"] for x in sec["items"])
    (out / "data" / "examples.json").write_text(json.dumps(examples, ensure_ascii=False), encoding="utf-8")
    n = 0
    for ex in examples:
        name, text = ex["case"], ex["text"]
        jobs = [("read", {"text": text})] + [(s, {"text": text, "step": s}) for s in ("project", "materials")]
        jobs += [(f"weeks.{b}", {"text": text, "step": "weeks", "budget": b}) for b in pipeline.budget_keys(name)]
        jobs += [(f"report.{b}", {"text": text, "step": "report", "budget": b}) for b in pipeline.report_keys(name)]      # 주차 계획 md 예시는 한 주 공부 시간마다
        for key, req in jobs:
            (out / "data" / "runs" / f"{name}.{key}.json").write_text(record(req), encoding="utf-8")
            n += 1
        for f in pipeline.DATA.glob(f"{name}.posting.png"):
            (out / "posting").mkdir(exist_ok=True)
            shutil.copy2(f, out / "posting" / f"{name}.png")
        for f in pipeline.DATA.glob(f"{name}.report.*"):      # 서버 주소 꼴 그대로: report/<예시>.<시간>[.<쪽>].png·.pptx
            if f.suffix in (".png", ".pptx"):
                (out / "report").mkdir(exist_ok=True)
                shutil.copy2(f, out / "report" / f.name.replace(".report.", ".", 1))
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"{out}: 예시 {len(examples)}개, 사건 파일 {n}개, {size / 1e6:.1f}MB")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve())
