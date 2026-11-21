"""주차 계획 md (submit/M-curriculum_bedrock.md 꼴) → data/<예시>.plan.<한 주 상한>.json. ④ 12주 계획이 읽는다.
  PYTHONPATH=. .venv/bin/python demo/design/build_curriculum_md.py aws_fde <M-curriculum_bedrock.md> <L-curriculum_bedrock.md>   (md 는 팀 저장소 submit/ 에 있다)
파일 이름 앞 글자가 크기다: S- 소, M- 중, L- 대 (11/21: 중 = 주 14시간이 기본, 대 = 주 28시간). 새 크기의 md 가 오면 같이 넣어 돌리면 된다.
상한은 md 의 '(상한 N시간)' 에서 읽는다.

md 꼴: '# <프로젝트> · 주차별 커리큘럼', '**총 …** · 구현 … · 학습 …', '**배정 작업** · W1, …', '**보류 작업** · W9, W10 | 없음',
주마다 '## N주차 · <쓴 시간> (상한 N시간)', '**목표** ·', '**학습·실습 방법** ·', '**배정 이유** ·',
'- 학습 20분 · [제목](<주소>)' 아래 '  - 다루는 역량 · C06 (일부), C23', '  - 배정 근거 · …',
'- 구현 12시간 · W1' 아래 '  - 산출물 · …' (그 작업이 이 주에 끝난다), '  - 목표 역량 · C01, C06', '  - 작업 근거 · …',
끝에 '## 프로젝트 작업별 목표 역량' ('- W1 <이름> · C01 <이름>; …'). 보류 작업 이름은 거기 없으면 data/<예시>.adapt.json 에서.
역량은 md 에 적힌 번호(C06)를 그대로 둔다 (화면에 낼 때 pipeline.full_id 로 공고의 역량 id 에 잇는다). 시간 합은 md 머리와 맞춰 본다."""
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SIZE = {"S": "소", "M": "중", "L": "대"}
SPAN = re.compile(r"^(?:(\d+)시간)?\s*(?:(\d+)분)?$")
LINK = re.compile(r"^\[(.+)\]\(<(.+)>\)$")
COMP = re.compile(r"^(C\d+)(?: \((있음|일부)\))?$")


def minutes(text):
    m = SPAN.match(text.strip())
    if not m or not any(m.groups()):
        raise ValueError(f"시간 글을 읽지 못했다: {text!r}")
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)


def field(lines, name):
    hit = [x for x in lines if x.startswith(f"**{name}** · ")]
    if len(hit) != 1:
        raise ValueError(f"'{name}' 줄이 {len(hit)}개")
    return hit[0].split(" · ", 1)[1].strip()


def comps(text):
    """'C26 (일부), C23' → [{cid, level}] (level 이 안 적혔으면 '있음')"""
    out = []
    for x in text.split(","):
        m = COMP.match(x.strip())
        if not m:
            raise ValueError(f"역량 번호를 읽지 못했다: {x!r}")
        out.append({"cid": m.group(1), "level": m.group(2) or "있음"})
    return out


def ids(text):
    return [] if text.strip() == "없음" else [x.strip() for x in text.split(",")]


def task_names(blocks, case):
    """'## 프로젝트 작업별 목표 역량' 의 작업 이름. 없는 작업(보류)은 adapt.json 이름"""
    names = {p["id"]: p["name"] for p in json.loads((DATA / f"{case}.adapt.json").read_text(encoding="utf-8"))["packages"]}
    for b in blocks:
        if b.startswith("프로젝트 작업별 목표 역량"):
            for row in b.splitlines()[1:]:
                m = re.match(r"^- (W\d+) (.+?) · C\d+", row)
                if m:
                    names[m.group(1)] = m.group(2)
    return names


def parse(case, md, source):
    head, *blocks = re.split(r"^## ", md, flags=re.M)
    lines = [x.strip() for x in head.splitlines() if x.strip()]
    title = re.match(r"^# (.+?) · 주차별 커리큘럼$", lines[0]).group(1)
    total = re.match(r"^\*\*총 (.+?)\*\* · 구현 (.+?) · 학습 (.+)$", lines[1])
    assigned, held = ids(field(lines, "배정 작업")), ids(field(lines, "보류 작업"))
    names = task_names(blocks, case)
    weeks, caps, seq = [], set(), 0
    for b in blocks:
        rows = b.splitlines()
        h = re.match(r"^(\d+)주차 · (.+?) \(상한 (\d+)시간\)$", rows[0].strip())
        if not h:
            continue      # 끝의 역량 모음 절
        week, used, cap = int(h.group(1)), minutes(h.group(2)), int(h.group(3))
        caps.add(cap)
        acts, done = [], []
        for raw in rows[1:]:
            if raw.startswith("  - "):
                key, val = raw[4:].split(" · ", 1)
                a = acts[-1]
                if key == "산출물":
                    assert a["kind"] == "project", f"{week}주 산출물 앞이 구현 줄이 아니다"
                    a["out"], a["completed_in_this_chunk"] = val.strip(), True
                    done.append({"task": a["id"], "out": a["out"]})
                elif key in ("다루는 역량", "목표 역량"):
                    a["covers"] = comps(val)
                    a["competencies"] = [c["cid"] for c in a["covers"]]
                elif key in ("배정 근거", "작업 근거", "자료 근거"):
                    a.setdefault("why", []).append(f"{key} · {val.strip()}")
                else:
                    raise ValueError(f"{week}주 모르는 아래 줄: {raw}")
                continue
            if not raw.startswith("- "):
                continue
            kind, rest = raw[2:].split(" ", 1)
            span, what = rest.split(" · ", 1)
            seq += 1
            if kind == "학습":
                link = LINK.match(what.strip())
                acts.append({"sequence": seq, "kind": "learning", "id": f"L{week:02d}{len(acts) + 1:02d}", "title": link.group(1), "url": link.group(2),
                             "minutes": minutes(span), "competencies": [], "completed_in_this_chunk": True})
            elif kind == "구현":
                w = what.strip()
                acts.append({"sequence": seq, "kind": "project", "id": w, "title": names[w], "minutes": minutes(span),
                             "competencies": [], "completed_in_this_chunk": False, "out": ""})
            else:
                raise ValueError(f"{week}주 모르는 줄: {raw}")
        for a in acts:
            a["hours"] = round(a["minutes"] / 60, 4)
        learn = sum(a["minutes"] for a in acts if a["kind"] == "learning")
        build = sum(a["minutes"] for a in acts if a["kind"] == "project")
        assert learn + build == used, f"{week}주 줄 합 {learn + build}분 ≠ 머리 {used}분"
        body = [x.strip() for x in rows[1:] if x.strip()]
        weeks.append({"week": week, "capacity_minutes": cap * 60, "used_minutes": used, "learning_minutes": learn, "implementation_minutes": build,
                      "goal": field(body, "목표"), "method": field(body, "학습·실습 방법"), "reason": field(body, "배정 이유"),
                      "deliverables_completed": done, "activities": acts})
    assert [w["week"] for w in weeks] == list(range(1, len(weeks) + 1)), "주 번호가 1부터 이어지지 않는다"
    assert len(caps) == 1, f"주마다 상한이 다르다: {caps}"
    ends = {d["task"]: w["week"] for w in weeks for d in w["deliverables_completed"]}
    assert sorted(ends) == sorted(assigned), f"끝나는 작업 {sorted(ends)} ≠ 배정 {assigned}"
    assert not set(held) & {a["id"] for w in weeks for a in w["activities"]}, "보류 작업이 주에 놓였다"
    for w in weeks:
        for a in w["activities"]:
            if a["kind"] == "project":
                a["ends_week"] = ends[a["id"]]
    all_, learn_, build_ = (sum(w[k] for w in weeks) for k in ("used_minutes", "learning_minutes", "implementation_minutes"))
    assert (all_, build_, learn_) == tuple(minutes(x) for x in total.groups()), f"합 {all_}·{build_}·{learn_}분 ≠ md 머리 {total.groups()}"
    cap = caps.pop()
    return {"schema_version": "jobaws.plan.md.v2", "source": source, "size": SIZE.get(source[:1], ""), "status": "ok", "project": {"title": title},
            "assigned": assigned, "held": [{"id": x, "name": names.get(x, "")} for x in held],
            "constraints": {"weeks": len(weeks), "hours_per_week": float(cap), "capacity_hours": float(cap * len(weeks))},
            "summary": {"scheduled_hours": all_ / 60, "learning_hours": learn_ / 60, "implementation_hours": build_ / 60},
            "weeks": weeks}


if __name__ == "__main__":
    case = sys.argv[1]
    for src in map(lambda x: Path(x).resolve(), sys.argv[2:]):
        d = parse(case, src.read_text(encoding="utf-8"), src.name)
        out = DATA / f"{case}.plan.{int(d['constraints']['hours_per_week'])}.json"
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        acts = [a for w in d["weeks"] for a in w["activities"]]
        s = d["summary"]
        print(f"{out.name} ← {src.name}: {d['size']} · 상한 {d['constraints']['hours_per_week']:g}시간, {len(d['weeks'])}주, 줄 {len(acts)}개, "
              f"총 {s['scheduled_hours']:.2f} · 구현 {s['implementation_hours']:.2f} · 학습 {s['learning_hours']:.2f}시간, "
              f"보류 {[x['id'] for x in d['held']]}, 역량 없는 줄 {sum(not a['competencies'] for a in acts)}개")
