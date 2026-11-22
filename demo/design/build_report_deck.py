"""정리 리포트(⑥): 발표 자료와 같은 모양(1920×1080, 먹색 글, 공고 인용은 노란 형광펜)의 면접 대비 슬라이드 여러 장. 모델·API 호출 없이 저장본만 읽는다.
  cd code && PYTHONPATH=. ../기용/.venv/bin/python demo/design/build_report_deck.py <예시 이름>
공부 시간 세 안(84·168·252)마다 demo/data/<예시>.report.<시간>.<쪽>.png (화면용), .pptx (받기용, 쪽 그림을 한 장씩), .json (바닥 줄 불렛에 쓸 값).
주차 계획 md 가 있는 예시(aws_fde, naver_ml_intern)는 그 대신 ④ 의 한 주 공부 시간 계획마다 (report.14·report.28; 보류한 7 은 리포트가 없다):
말할 작업 묶음의 주는 그 계획에서 그 작업이 놓인 주, 미룬 작업은 '미룬 일', 미리 공부할 것은 그 계획의 교육자료 가운데 그 문장의 역량을 다루는 것 (없으면 없다고 쓴다).
.json 의 rows 에 37줄 모두의 작업·주·공부 자료를 남긴다 (tests/test_demo.py 가 계획 파일과 맞는지 본다).
만드는 길: HTML → Chrome 머리 없이 PDF → pdftoppm 쪽 그림 → python-pptx (uv 로 그때 불러 쓴다). 발표 pptx 를 만든 길과 같다.
넘침 검사: Chrome 이 HTML 을 그린 뒤 쪽 밖으로 나가거나 칸을 넘친 글을 세어, 하나라도 있으면 멈춘다.

쪽: 표지 → 질문 다섯 (한 쪽에 하나) → 프로젝트 밖에서 채울 역량 (응용 프로젝트 덮기 표에서 '있음'이 아닌 것, ③ 화면과 같은 저장본).
질문 고르기 (QUESTIONS 개):
  1. 문장의 우선순위: 필수 문장 → 우대 문장 → 나머지
  2. 질문의 출처: 회사 이름이 붙은 실제 질문 → 이름 없는 실제 질문(주제별 질문) → AI가 만든 질문
  3. 그 우선순위의 역량이 많은 문장 먼저, 같으면 공고 차례
답 요점은 저장본의 다섯 점 그대로(합니다체, 면접에서 말로 하는 답). 예시 숫자(지어낸 값)는 밑줄.
글자 크기: 본문(답·카드·밑줄 설명)은 32px, 머리 줄·공고 문장·칸 이름은 28px. 화면은 쪽 그림을 반쯤 줄여 보이므로 그보다 작은 글은 쓰지 않는다 (사용자 11/22: 작은 곁글 금지)."""
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from demo.pipeline import WORTH, example_case, exam_weeks, plans_case, sem_week, span_text, weeks_text

DEMO = Path(__file__).resolve().parent.parent
DATA = DEMO / "data"
FONT = DEMO / "static" / "fonts" / "PretendardVariable.woff2"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BUDGETS = ("84", "168", "252")
QUESTIONS = 5
PRIORITY = {"필수": 0, "우대": 1}
LEVEL = {"없음": "프로젝트로 다루지 않아요", "일부": "프로젝트로 일부만 다뤄요"}
JOBS = "말할 작업 묶음"      # 카드 이름 (발표 자료의 '작업 묶음', 11/22)
NO_STUDY = "이 질문에 맞는 교육자료는 계획에 없어요"
NOTE = "밑줄 숫자는 지어낸 예시예요. 내 프로젝트에서 잰 값으로 바꿔 말해요."      # 밑줄 설명 (다섯 질문 쪽과 전체 PDF 가 같은 글)


# ── 고르기 ───────────────────────────────────────────────────────────
def row_priority(row):
    return min(PRIORITY.get(c["priority"], 2) for c in row["competencies"])


def origin_rank(q):
    if q["origin"] != "은행":
        return 2
    return 0 if q.get("company_short") else 1


def rank(row):
    p = row_priority(row)
    same = sum(PRIORITY.get(c["priority"], 2) == p for c in row["competencies"])
    return (p, origin_rank(row["question"]), -same, row["sentence_no"])


def source_tag(q):
    """질문 출처 이름표 (발표 자료 14·38·53쪽의 말): 회사 면접 질문 · 주제별 질문(회사 이름 없는 공개 질문) · AI가 만든 질문"""
    return {0: f"{q.get('company_short')} 면접 질문", 1: "주제별 질문", 2: "AI가 만든 질문"}[origin_rank(q)]


def outside(case, adapt):
    """프로젝트 밖에서 채울 역량과 그것을 가르치는 교육자료 (④ 에서 고른 자료 가운데 그 역량을 다루는 것)"""
    picks = json.loads((DATA / f"{case}.m3.json").read_text("utf-8"))["picks"]
    out = []
    for c in adapt["coverage"]:
        if c["expect"] == "있음":
            continue
        mats = [p["title"] for p in picks if any(x["cid"] == c["id"] and x["level"] != "없음" for x in p["covers"])]
        out.append({"name": c["name"], "tier": c["tier"], "level": c["expect"], "materials": mats})
    return out


def page(case, budget):
    report = json.loads((DATA / f"{case}.report.json").read_text("utf-8"))
    adapt = json.loads((DATA / f"{case}.adapt.json").read_text("utf-8"))
    weeks = json.loads((DATA / f"{case}.weeks.json").read_text("utf-8"))
    posting = example_case(case)["posting"]
    exams = exam_weeks(weeks)
    team = weeks["team"]
    study = lambda s: s and {**s, "when": f"{s['week']}주차까지"}
    return {
        "company": posting["company"], "role": posting["title"], "project": weeks["project"]["title"],
        "coverage": (len(adapt["coverage"]), sum(WORTH[c["expect"]] for c in adapt["coverage"])),
        "weeks": team["weeks"], "when": f"팀 {team['members']}명 · 공부 {weeks['budgets'][budget]['label']}",
        "questions": [{
            "n": r["sentence_no"], "priority": ["필수", "우대", "나머지"][row_priority(r)], "q": r["question"],
            "sentence": r["sentence_text"], "points": r["answer_points"], "examples": [x["value"] for x in r["example_numbers"]],
            "packages": [(p["name"], weeks_text({"from": p["weeks"][0], "to": p["weeks"][-1]}, exams)) for p in r["packages"]],
            "study": study(r["study_point"][budget])} for r in sorted(report["rows"], key=rank)[:QUESTIONS]],
        "outside": outside(case, adapt)}


# ── 주차 계획 md 의 리포트 (④ 의 한 주 공부 시간 계획마다) ───────────────────
def placed(plan):
    """계획 → {작업 id: 그 작업이 놓인 학기 주들} (계획 1~12주 = 학기 1~6·9~14주, ④ 의 칸 이름과 같다)"""
    at = {}
    for w in plan["weeks"]:
        for x in w["activities"]:
            if x["kind"] == "project":
                at.setdefault(x["id"], []).append(sem_week(w["week"]))
    return at


def runs_text(weeks):
    """학기 주 [2, 3, 5] → "2~3주차, 5주차". 시험 주를 건너뛴 6·9 는 이어지지 않아 "6주차, 9주차" """
    runs = []
    for k in sorted(set(weeks)):
        if runs and runs[-1][1] == k - 1:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    return ", ".join(f"{a}주차" if a == b else f"{a}~{b}주차" for a, b in runs)


def plan_study(row, plan, names):
    """그 줄의 역량을 다루는 그 계획의 교육자료 하나: 다루는 정도의 합이 큰 것, 같으면 이른 주. 다루는 자료가 없으면 None (카드는 없다고 쓴다).
    예전에는 그 작업이 시작하는 주의 자료를 '그 일을 시작하는 주에 보는 자료'로 채웠지만, 역량과 맞지 않는 자료를 내보여 뺐다 (11/22 리뷰)"""
    want = {c["cid"] for c in row["competencies"]}
    best = None
    for w in plan["weeks"]:
        for x in w["activities"]:
            hit = [c for c in x.get("covers", []) if x["kind"] == "learning" and c["cid"] in want and c["level"] != "없음"]
            if not hit:
                continue
            key = (-sum(WORTH[c["level"]] for c in hit), w["week"], x["sequence"])
            if best is None or key < best[0]:
                top = max(hit, key=lambda c: WORTH[c["level"]])
                best = (key, {"title": x["title"], "name": names[top["cid"]], "week": sem_week(w["week"]), "minutes": x["minutes"], "url": x.get("url", "")})
    return best and {**best[1], "when": f"{best[1]['week']}주차 · {span_text(best[1]['minutes'])}"}


def plan_rows(report, plan, names):
    """줄 모두: 줄의 작업마다 그 계획의 주 (미룬 작업은 held), 공부 자료 하나. 어느 쪽도 아닌 작업은 계획이 틀린 것이라 멈춘다.
    줄의 작업은 plan_packages (계획과 같은 번호, 네이버), 없으면 packages (AWS 는 응용 번호가 곧 계획 번호다)"""
    at, held = placed(plan), {h["id"] for h in plan["held"]}
    out = []
    for r in report["rows"]:
        pk = []
        for p in r.get("plan_packages", r["packages"]):
            if p["id"] not in at and p["id"] not in held:
                raise SystemExit(f"{p['id']} 가 {plan['source']} 에 놓이지도 미뤄지지도 않았다")
            pk.append({"id": p["id"], "name": p["name"], "weeks": sorted(set(at.get(p["id"], []))), "held": p["id"] in held})
        out.append({"n": r["sentence_no"], "packages": pk, "study": plan_study(r, plan, names)})
    return out


def plan_page(case, plan):
    report = json.loads((DATA / f"{case}.report.json").read_text("utf-8"))
    adapt = json.loads((DATA / f"{case}.adapt.json").read_text("utf-8"))
    posting = example_case(case)["posting"]
    hours = plan["constraints"]["hours_per_week"]
    names = {c["id"]: c["name"] for c in adapt["coverage"]}
    rows = {x["n"]: x for x in plan_rows(report, plan, names)}
    job = lambda p: (p["name"], f"미룬 일 · 한 주 {hours:g}시간 계획에는 넣지 못했어요" if p["held"] else runs_text(p["weeks"]))
    total = plan["summary"]["scheduled_hours"] * 60
    return {
        "company": posting["company"], "role": posting["title"], "project": plan["project"]["title"],
        "coverage": (len(adapt["coverage"]), sum(WORTH[c["expect"]] for c in adapt["coverage"])),
        "weeks": len(plan["weeks"]), "when": f"한 주 {hours:g}시간 계획 · 총 {span_text(round(total))}",
        "plan": {"hours": hours, "held": [h["id"] for h in plan["held"]], "source": plan["source"]}, "rows": list(rows.values()),
        "questions": [{
            "n": r["sentence_no"], "priority": ["필수", "우대", "나머지"][row_priority(r)], "q": r["question"],
            "sentence": r["sentence_text"], "points": r["answer_points"], "examples": [x["value"] for x in r["example_numbers"]],
            "packages": [job(p) for p in rows[r["sentence_no"]]["packages"]],
            "study": rows[r["sentence_no"]]["study"]} for r in sorted(report["rows"], key=rank)[:QUESTIONS]],
        "outside": plan_outside(adapt, plan, case)}


def plan_outside(adapt, plan, case):
    """프로젝트 밖에서 채울 역량 (응용 덮기 표에서 '있음'이 아닌 것)과 그것을 다루는 그 계획의 교육자료 (주).
    계획에 그 역량의 자료가 없으면 ③ 이 고른 자료(m3.json picks)를 '12주 계획에는 없음'으로 적는다 (AWS Go · Learn Go with Tests, 11/22 리뷰).
    used: 계획에 놓인 작업 묶음 가운데 이름·할 일·산출물에 그 도구 이름이 나오는 것 (AWS React → W7). 도구 이름은 교육자료로 익히지만 그 묶음에서 써 본다"""
    picks = json.loads((DATA / f"{case}.m3.json").read_text("utf-8"))["picks"]
    at = placed(plan)
    out = []
    for c in adapt["coverage"]:
        if c["expect"] == "있음":
            continue
        mats = [f"{x['title']} ({sem_week(w['week'])}주차)" for w in plan["weeks"] for x in w["activities"]
                if x["kind"] == "learning" and any(k["cid"] == c["id"] and k["level"] != "없음" for k in x.get("covers", []))]
        mats = mats or [f"{p['title']} (③에서 고름 · 12주 계획에는 없음)" for p in picks
                        if any(k["cid"] == c["id"] and k["level"] != "없음" for k in p["covers"])]
        word = re.compile(rf"(?<![A-Za-z]){re.escape(c['name'])}(?![A-Za-z])")
        used = [k["id"] for k in adapt["packages"] if k["id"] in at and word.search(" ".join((k["name"], k["do"], k["out"])))]
        out.append({"name": c["name"], "tier": c["tier"], "level": c["expect"], "materials": mats, "used": used})
    return out


# ── 쪽 짜기 (HTML) ────────────────────────────────────────────────────
e = html.escape


def marked(text, values):
    """예시 숫자(지어낸 값)에 밑줄. 긴 값부터 찾고 겹치면 짧은 것을 버린다."""
    spans = []
    for v in sorted(set(values), key=len, reverse=True):
        at = text.find(v)
        if at >= 0 and not any(a < at + len(v) and at < b for a, b in spans):
            spans.append((at, at + len(v)))
    out, pos = "", 0
    for a, b in sorted(spans):
        out += e(text[pos:a]) + f'<u class="ex">{e(text[a:b])}</u>'
        pos = b
    return out + e(text[pos:]), bool(spans)


def points(x):
    return f"{x:g}"


CSS = """
@font-face { font-family: "Pretendard Variable"; src: url("%s") format("woff2-variations"); font-weight: 45 920; }
@page { size: 1920px 1080px; margin: 0; }
:root { --paper: #faf9f5; --surface: #fff; --sunk: #f0eee6; --ink: #2b2a27; --line: rgba(43,42,39,.12); --line-strong: rgba(43,42,39,.2);
  --accent: #c6613f; --hl: #fde68a; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--paper); }
body { font-family: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo", sans-serif; color: var(--ink); font-size: 32px; line-height: 1.45;
  word-break: keep-all; line-break: strict; font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased; }
.slide { position: relative; width: 1920px; height: 1080px; overflow: hidden; background: var(--paper); page-break-after: always; break-after: page; }
.tag { position: absolute; left: 120px; top: 72px; font-size: 28px; font-weight: 600; display: flex; gap: 16px; align-items: center; }
.chip { display: inline-block; padding: 2px 14px; border-radius: 8px; font-size: 28px; font-weight: 600; }
.chip.ink { background: var(--ink); color: var(--paper); }
.chip.line { box-shadow: inset 0 0 0 2px var(--line-strong); }
.title { position: absolute; left: 120px; right: 120px; top: 124px; font-size: 44px; font-weight: 600; line-height: 1.3; }
.pg { position: absolute; right: 120px; bottom: 36px; font-size: 28px; }
.foot { position: absolute; left: 120px; bottom: 32px; font-size: 32px; }
u.ex { text-decoration: underline dotted 3px; text-underline-offset: 7px; }
.hl { background: var(--hl); padding: 2px 10px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.label { font-size: 28px; font-weight: 600; margin-bottom: 16px; }
/* 표지: 위에서부터 차례로 (직무 이름이 두 줄이어도 겹치지 않게) */
.cover .head { position: absolute; left: 120px; right: 120px; top: 110px; display: flex; flex-direction: column; gap: 20px; }
.cover .kicker { font-size: 32px; font-weight: 600; color: var(--accent); }
.cover .role { font-size: 96px; font-weight: 600; line-height: 1.12; letter-spacing: -0.01em; }
.cover .company { font-size: 44px; font-weight: 500; margin-top: 8px; }
.cover .project { font-size: 32px; }
.stats { position: absolute; left: 120px; right: 120px; top: 700px; display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 80px;
  border-top: 2px solid var(--ink); padding-top: 40px; }
.stat .n { font-size: 96px; font-weight: 600; line-height: 1.05; white-space: nowrap; }
.stat .n small { font-size: 44px; font-weight: 600; }
.stat .c { font-size: 32px; margin-top: 8px; }
/* 질문: 머리(번호·제목·공고 문장)를 위에서부터 쌓고, 남은 높이를 답과 카드가 쓴다 */
.slide.q { display: flex; flex-direction: column; padding: 72px 120px 96px; }
.slide.q .tag, .slide.q .title { position: static; }
.slide.q .title { margin-top: 20px; }
.quote { margin-top: 28px; font-size: 28px; line-height: 1.7; }
.quote .src { font-weight: 600; margin-right: 12px; }
.cols { flex: 1; min-height: 0; margin-top: 32px; display: grid; grid-template-columns: 1fr 620px; column-gap: 72px; }
ol.ans { list-style: none; counter-reset: a; }
ol.ans li { counter-increment: a; position: relative; padding-left: 52px; margin-bottom: 14px; font-size: 32px; line-height: 1.38; }
ol.ans li::before { content: counter(a); position: absolute; left: 0; top: 4px; width: 36px; height: 36px; border-radius: 50%%; background: var(--ink);
  color: var(--paper); font-size: 24px; font-weight: 600; display: grid; place-items: center; line-height: 1; }
.card { background: var(--surface); border: 2px solid var(--line); border-radius: 24px; padding: 20px 32px 10px; align-self: start; }
.card + .card { margin-top: 16px; }
.card .label { margin-bottom: 8px; }
.card ul { list-style: none; }
.card li { font-size: 32px; line-height: 1.3; margin-bottom: 10px; }
.card li b { display: block; font-weight: 600; }
.card ul.jobs li b { display: inline; }      /* 작업 묶음은 이름 · 주를 한 줄로 이어 쓴다 (묶음 셋이어도 칸 안에 든다) */
/* 밖에서 채울 역량 */
.gaps { position: absolute; left: 120px; right: 120px; top: 380px; display: grid; grid-template-columns: repeat(%d, 1fr); column-gap: 80px; }
.gap .name { font-size: 96px; font-weight: 600; line-height: 1.05; }
.gap .what { font-size: 32px; margin: 20px 0 40px; }
.gap .mat { font-size: 32px; font-weight: 600; }
.gap .mat span { display: block; font-size: 28px; font-weight: 500; margin-bottom: 8px; }
"""

# 그린 뒤 넘친 글을 센다: 쪽 밖으로 나간 것, 칸보다 긴 것. 결과는 body 의 data-over 에 (dump-dom 으로 읽는다)
CHECK = """<script>document.fonts.ready.then(() => { const bad = [];
  for (const s of document.querySelectorAll('.slide')) { const r = s.getBoundingClientRect();
    for (const x of s.querySelectorAll('*')) { const b = x.getBoundingClientRect();
      if (b.width && (b.right > r.right + 1 || b.bottom > r.bottom + 1 || b.left < r.left - 1)) bad.push(x.className || x.tagName); }
    const cols = s.querySelector('.cols'); if (cols) for (const c of cols.children) { const b = c.getBoundingClientRect(), k = cols.getBoundingClientRect();
      if (b.bottom > k.bottom + 1) bad.push('cols-overflow'); }
    const head = s.querySelector('.head'), stats = s.querySelector('.stats');
    if (head && stats && head.getBoundingClientRect().bottom > stats.getBoundingClientRect().top - 24) bad.push('cover-clash'); }
  document.body.dataset.over = bad.join(',') || 'none'; });</script>"""


def cover(p, total):
    n, got = p["coverage"]
    return f"""<section class="slide cover">
  <div class="head"><p class="kicker">면접 대비 리포트</p><h1 class="role">{e(p['role'])}</h1>
    <p class="company">{e(p['company'])}</p><p class="project">프로젝트 · {e(p['project'])}</p></div>
  <div class="stats">
    <div class="stat"><p class="n">{points(got)}<small> / {n}</small></p><p class="c">공고 역량을 프로젝트로</p></div>
    <div class="stat"><p class="n">{len(p['questions'])}<small>개</small></p><p class="c">예상 면접 질문</p></div>
    <div class="stat"><p class="n">{p['weeks']}<small>주</small></p><p class="c">{e(p['when'])}</p></div>
  </div>
  <p class="pg">1 / {total}</p>
</section>"""


def question(i, q, total):
    pts = [marked(t, q["examples"]) for t in q["points"]]
    jobs = "".join(f"<li><b>{e(name)}</b> · {e(when)}</li>" for name, when in q["packages"])
    s = q["study"]
    study = (f"<li><b>{e(s['title'])}</b>{e(s['name'])} · {e(s['when'])}</li>" if s and s.get("title")
             else f"<li>{NO_STUDY}</li>")
    tag = source_tag(q["q"])
    note = f'<p class="foot">{NOTE}</p>' if any(m for _, m in pts) else ""
    return f"""<section class="slide q">
  <p class="tag">질문 {i} / {QUESTIONS}<span class="chip {'ink' if q['q']['origin'] == '은행' else 'line'}">{e(tag)}</span><span class="chip line">{q['priority']} 문장</span></p>
  <h1 class="title">{e(q['q']['text_ko'])}</h1>
  <p class="quote"><span class="src">공고 {q['n']}번 문장</span><span class="hl">{e(q['sentence'])}</span></p>
  <div class="cols">
    <div><p class="label">이렇게 답해요</p><ol class="ans">{''.join(f'<li>{t}</li>' for t, _ in pts)}</ol></div>
    <div><div class="card"><p class="label">{JOBS}</p><ul class="jobs">{jobs}</ul></div>
         <div class="card"><p class="label">미리 공부할 것</p><ul>{study}</ul></div></div>
  </div>
  {note}
  <p class="pg">{i + 1} / {total}</p>
</section>"""


def what(g):
    """역량 아래 한 줄. 도구 이름은 교육자료로 익히는 것이 규칙이지만, 계획의 작업 묶음이 그 도구를 쓰면 '프로젝트로 다루지 않아요'가 틀린 말이라 그 묶음을 적는다"""
    if g["level"] == "없음" and g.get("used"):
        return f"{g['tier']} · 도구 이름은 교육자료로 익혀요 · {'·'.join(g['used'])}에서 써 봐요"
    return f"{g['tier']} · {LEVEL[g['level']]}"


def gaps(p, total):
    cards = "".join(f"""<div class="gap"><p class="name">{e(g['name'])}</p><p class="what">{e(what(g))}</p>
      <p class="mat"><span>교육자료</span>{e(', '.join(g['materials']) or '맞는 자료가 없어요')}</p></div>""" for g in p["outside"])
    return f"""<section class="slide">
  <h1 class="title" style="top:120px">프로젝트 밖에서 채울 역량</h1>
  <div class="gaps">{cards}</div>
  <p class="pg">{total} / {total}</p>
</section>"""


def deck_html(p):
    total = 1 + len(p["questions"]) + bool(p["outside"])
    slides = [cover(p, total)] + [question(i, q, total) for i, q in enumerate(p["questions"], 1)] + ([gaps(p, total)] if p["outside"] else [])
    css = CSS % (FONT.as_uri(), max(1, len(p["outside"])))
    return f"<!doctype html><html lang=ko><head><meta charset=utf-8><style>{css}</style></head><body>{''.join(slides)}{CHECK}</body></html>", total


def facts(p):
    qs = [q["q"] for q in p["questions"]]
    plan = {"plan": p["plan"], "shown": [q["n"] for q in p["questions"]], "rows": p["rows"]} if "plan" in p else {}
    # 질문 출처의 셈 (⑤ 바닥 줄 "질문 출처"가 회사 질문만이 아니라 주제별·AI가 만든 질문도 센다): company + topic + made = questions
    return {"questions": len(qs), "bank": sum(q["origin"] == "은행" for q in qs),
            "companies": list(dict.fromkeys(q["company_short"] for q in qs if q.get("company_short"))),
            "company": sum(origin_rank(q) == 0 for q in qs), "topic": sum(origin_rank(q) == 1 for q in qs), "made": sum(origin_rank(q) == 2 for q in qs),
            "uncovered": [g["name"] for g in p["outside"]], **plan}


def chrome(*args):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=4000", *args],
                   check=True, capture_output=True, text=True, timeout=120)


def build(case):
    plans = {f"{d['constraints']['hours_per_week']:g}": d for d in plans_case(case)}      # 주차 계획 md 예시는 계획마다, 아니면 공부 시간 안마다
    for budget in plans or BUDGETS:
        for old in DATA.glob(f"{case}.report.{budget}.*"):      # 이번에 다시 만드는 안의 지난 판만 지운다 (쪽 수가 다른 그림). 다른 안의 파일은 둔다 (네이버 84·168·252 는 11/22 부터 화면이 안 쓴다)
            if ".all." not in old.name:      # 전체 리포트(.all.)는 build_report_all.py 가 따로 만든다
                old.unlink()
        p = plan_page(case, plans[budget]) if plans else page(case, budget)
        doc, total = deck_html(p)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "deck.html"
            src.write_text(doc, "utf-8")
            dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=4000", "--window-size=1920,1080",
                                  "--dump-dom", src.as_uri()], check=True, capture_output=True, text=True, timeout=120).stdout
            over = re.search(r'data-over="([^"]*)"', dom)
            if not over or over[1] != "none":
                raise SystemExit(f"{case} {budget}: 넘친 글 {over[1] if over else '(검사가 돌지 않음)'}")
            pdf = Path(tmp) / "deck.pdf"
            chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf}", src.as_uri())
            subprocess.run(["pdftoppm", "-png", "-scale-to-x", "1920", "-scale-to-y", "1080", str(pdf), str(Path(tmp) / "p")], check=True)
            pngs = sorted(Path(tmp).glob("p-*.png"))
            if len(pngs) != total:
                raise SystemExit(f"{case} {budget}: 쪽 {len(pngs)}장 (기대 {total}장)")
            for k, png in enumerate(pngs, 1):
                shutil.copy(png, DATA / f"{case}.report.{budget}.{k}.png")
        pptx = DATA / f"{case}.report.{budget}.pptx"
        subprocess.run(["uv", "run", "--no-project", "--with", "python-pptx", "python", "-I", "-c", PPTX, str(pptx),
                        *[str(DATA / f"{case}.report.{budget}.{k}.png") for k in range(1, total + 1)]], check=True)
        (DATA / f"{case}.report.{budget}.json").write_text(json.dumps({**facts(p), "slides": total}, ensure_ascii=False, indent=1) + "\n", "utf-8")
        print(pptx.name, total, "장", [q["n"] for q in p["questions"]])


# 쪽 그림을 한 장씩 꽉 채운 16:9 pptx (발표 pptx 와 같은 길)
PPTX = """import sys
from pptx import Presentation
from pptx.util import Emu
prs = Presentation(); prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
for im in sys.argv[2:]:
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.shapes.add_picture(im, 0, 0, prs.slide_width, prs.slide_height)
prs.save(sys.argv[1])"""


if __name__ == "__main__":
    build(sys.argv[1])
