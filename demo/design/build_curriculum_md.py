"""주차 계획 md (submit/M-curriculum_bedrock.md 꼴) → data/<예시>.plan.<한 주 상한>.json. ④ 12주 계획이 읽는다.
  PYTHONPATH=. .venv/bin/python demo/design/build_curriculum_md.py aws_fde <M-curriculum_bedrock.md> <curriculum_bedrock.md> \
      <L-curriculum_bedrock.md> <"curriculum_bedrock (1).md">   (md 는 팀 저장소 submit/ 에 있다)
계획은 한 주 상한(md 의 '(상한 N시간)')으로 부른다 (11/21: 주 14시간이 기본, 15·28시간). 새 시간의 md 가 오면 같이 넣어 돌리면 된다.
배정을 보류한 md ('# … · 커리큘럼 배정 보류', 상태 blocked) 는 data/<예시>.blocked.<한 주 시간>.json 으로: 가용·필요 시간과 주당 최소 시간.
목표·학습·실습 방법은 글 그대로 두고, 화면용 개조식 줄(goal_steps·method_steps, 세 줄까지)을 따로 만든다 (steps).

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
MAX_STEPS = 3      # 토글의 개조식 줄 수 (사용자 11/21: 목표·할 일·배우는 역량을 개조식으로 세 줄까지)
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


# 개조식 줄: md 문장을 그 문장의 연결 어미(…고, / …며, / …한 뒤, / …한 다음, / 문장 끝)에서 나누고, 끝 어미만 '~기' 로 바꾼다.
# 낱말은 바꾸지 않는다. 나눈 조각이 세 개를 넘으면 가장 짧게 붙는 이웃 둘을 원문 그대로(쉼표째) 붙인다
CUT = re.compile(r"(?:(?<=고)|(?<=며)|(?<=뒤)|(?<=다음)|(?<=후)|(?<=하여)),\s+")
LEAD = ("아울러 ", "이어서 ")      # 조각 맨 앞의 잇는 말 (앞 조각이 따로 줄이 되면 필요 없다)
HANGUL = 0xAC00


def _drop_n(syllable):
    """받침 ㄴ 을 뗀다: 한 → 하, 킨 → 키"""
    c = ord(syllable) - HANGUL
    return chr(ord(syllable) - 4) if 0 <= c < 11172 and c % 28 == 4 else None


def ending(clause):
    """'…양식을 잡고' → '…양식을 잡기', '…점검한 뒤' → '…점검하기', '…수립한다.' → '…수립하기'"""
    t = clause.strip().rstrip(".")
    for tail in (" 뒤", " 다음", " 후"):
        if t.endswith(tail):
            t = t[: -len(tail)]
            if t.endswith("은"):
                return t[:-1] + "기"
            bare = _drop_n(t[-1])
            return (t[:-1] + bare if bare else t) + "기"
    for tail in ("하고", "하며", "하여", "한다"):
        if t.endswith(tail):
            return t[: -len(tail)] + "하기"
    for tail in ("고", "며", "는다", "다"):
        if t.endswith(tail):
            return t[: -len(tail)] + "기"
    return t


def steps(text):
    """md 문장 → 개조식 줄 (세 줄까지, 낱말은 md 그대로)"""
    parts = [x.strip() for sent in re.split(r"(?<=다)\.\s+", text.strip()) for x in CUT.split(sent) if x.strip()]
    while len(parts) > MAX_STEPS:
        i = min(range(len(parts) - 1), key=lambda k: len(parts[k]) + len(parts[k + 1]))
        parts[i:i + 2] = [f"{parts[i]}, {parts[i + 1]}"]
    out = []
    for x in parts:
        for lead in LEAD:
            x = x.removeprefix(lead)
        out.append(ending(x))
    flat = re.sub(r"\s+", "", text)
    for x in out:      # 끝 어미 말고는 md 에 그대로 있어야 한다
        assert re.sub(r"\s+", "", x[:-3]) in flat, f"개조식 줄이 md 에 없다: {x}"
    return out


def blocked(md, source):
    """배정 보류 md → 가용·필요 시간과 주당 최소 시간 (화면이 '이 시간으로는 짜지 않고 최소 시간을 알려 준다'고 쓴다)"""
    lines = [x.strip() for x in md.splitlines() if x.strip()]
    need = re.match(r"^구현 (.+?) \+ 학습 (.+?) = (.+)$", field(lines, "필요시간"))
    have = minutes(field(lines, "가용시간"))
    assert field(lines, "상태").strip("`") == "blocked", "보류 md 가 아니다"
    assert minutes(need.group(1)) + minutes(need.group(2)) == minutes(need.group(3)), "필요시간 합이 맞지 않다"
    weeks = 12
    assert have % (weeks * 60) == 0, "가용시간이 12주로 나뉘지 않는다"
    return {"schema_version": "jobaws.plan.blocked.v1", "source": source, "status": "blocked", "reason": field(lines, "보류 사유"),
            "weeks": weeks, "hours_per_week": have // 60 // weeks, "available_minutes": have, "needed_minutes": minutes(need.group(3)),
            "needed_build_minutes": minutes(need.group(1)), "needed_learning_minutes": minutes(need.group(2)),
            "short_minutes": minutes(field(lines, "총 가용시간 대비 부족")), "min_per_week_minutes": minutes(field(lines, "시간 합계 기준 주당 최소"))}


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
                      "goal_steps": steps(field(body, "목표")), "method_steps": steps(field(body, "학습·실습 방법")),
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
    return {"schema_version": "jobaws.plan.md.v3", "source": source, "status": "ok", "project": {"title": title},
            "assigned": assigned, "held": [{"id": x, "name": names.get(x, "")} for x in held],
            "constraints": {"weeks": len(weeks), "hours_per_week": float(cap), "capacity_hours": float(cap * len(weeks))},
            "summary": {"scheduled_hours": all_ / 60, "learning_hours": learn_ / 60, "implementation_hours": build_ / 60},
            "weeks": weeks}


if __name__ == "__main__":
    case = sys.argv[1]
    for src in map(lambda x: Path(x).resolve(), sys.argv[2:]):
        md = src.read_text(encoding="utf-8")
        if re.search(r"^# .+ · 커리큘럼 배정 보류$", md, re.M):
            b = blocked(md, src.name)
            out = DATA / f"{case}.blocked.{b['hours_per_week']}.json"
            out.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"{out.name} ← {src.name}: 보류 · 한 주 {b['hours_per_week']}시간, 가용 {b['available_minutes'] / 60:g} · 필요 {b['needed_minutes'] / 60:g}시간, "
                  f"주당 최소 {b['min_per_week_minutes']}분")
            continue
        d = parse(case, md, src.name)
        out = DATA / f"{case}.plan.{int(d['constraints']['hours_per_week'])}.json"
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        acts = [a for w in d["weeks"] for a in w["activities"]]
        s = d["summary"]
        print(f"{out.name} ← {src.name}: 상한 {d['constraints']['hours_per_week']:g}시간, {len(d['weeks'])}주, 줄 {len(acts)}개, "
              f"총 {s['scheduled_hours']:.2f} · 구현 {s['implementation_hours']:.2f} · 학습 {s['learning_hours']:.2f}시간, "
              f"보류 {[x['id'] for x in d['held']]}, 역량 없는 줄 {sum(not a['competencies'] for a in acts)}개")
