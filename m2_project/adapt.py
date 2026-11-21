"""③ 응용: 1등 후보(바탕) 하나를 보완 후보 2~3개의 부분을 빌려 학생 팀이 만들 프로젝트 하나로 바꾼다.

결과는 프로젝트 하나다. 보완은 재료일 뿐이다 (2026-11-18 사용자 규칙). 같은 날 규칙 몇 가지가 더 있다.
- 필수는 바탕(샘플)이 덮는다. 보완과 더한 일은 우대 → 나머지 차례로 채운다.
- 바탕이 '있음'으로 덮지 못한 필수는 보완이 먼저 채우고, 판정한 후보 누구도 덮지 못하면 AI 가 더한 일(added)로 채워 그렇게 적는다.
  AWS 공고는 판정한 100개 가운데 필수 8개를 모두 덮는 후보가 없고, C40 은 덮는 후보가 하나도 없다 (2026-11-19).
  그래서 '바탕이 필수를 모두 덮는가'(R0)는 고른 바탕에 대한 사실로 경고에 적고, 응용 답의 잘못으로 세지 않는다.
- 수행·협업·태도·도구 역량은 되도록 모두 덮는다. 지식은 교육자료(m3)로 넘겨도 된다.
- 다만 덮기는 목표일 뿐이다. 억지로 붙여 프로젝트가 이상해지면 덮지 않고 까닭을 적는다. 그래서 덮기 목표는 확인에서 경고로만 센다.
1. pick_complements (코드): 판정을 마친 후보 가운데 바탕이 덮지 못한 필수 → 우대 → 나머지 역량을 가장 많이 채우는 후보를 차례로 고른다. 돈이 들지 않는다.
2. ask (LLM 한 번): 바탕 + 보완 → 작업 묶음, 역량별 덮기 표, 결정 기록, 의심.
3. check (코드): 구절이 출처 글에 그대로 있나, 빌린 역량을 출처가 덮나, 필수가 핵심에서 덮이나, 시간 예산 등.
   걸리면 걸린 것(경고도 '선택'으로 함께)과 고치는 길을 적어 한 번만 다시 쓰게 한다. 그래도 걸리면 걸린 것을 checks 에 적은 채 낸다.
손으로 한 한 건과 제안은 research/adapt/ (hand_naver.md, automation.md) 에 있다.
"""
import hashlib
import json
import re

from shared import config, llm
from shared.llm import STR, arr, obj

from .pick import _ELLIPSIS, LEVELS, TIERS, VALUE, quote_ok, shown, tier_of
from .search import MODEL, PROMPT

TEAM = {"members": 4, "weeks": 12, "hours_per_week": 7, "budget_hours": 336}   # m4_weekly 와 데모 weeks.json 의 팀 예산
MAX_COMPLEMENTS = 3
MIN_WORDS = 5               # 근거 구절의 최소 낱말 수
PACKAGES = (6, 12)          # 묶음 수 범위
HOURS = (8, 80)             # 묶음 하나의 시간 범위
BASE_SHARE = 0.4            # 핵심 시간 가운데 바탕을 출처로 둔 묶음의 몫 하한
ALTERNATIVE = re.compile(r"등|또는|혹은|중 하나|\bor\b|\betc\b", re.I)
MUST = ("수행", "협업·태도", "도구")   # 프로젝트가 꼭 덮을 역량 유형. 지식만 교육자료(m3)로 넘겨도 된다 (11/18 사용자 규칙)

SYSTEM = (PROMPT / "adapt.txt").read_text("utf-8")
SOURCE = obj({"project": STR, "quote": STR, "for": arr(STR)})
SCHEMA = obj({
    "title": STR, "goal": STR,
    "packages": arr(obj({"id": STR, "name": STR, "do": STR, "out": STR, "hours": {"type": "integer"},
                         "core": {"type": "boolean"}, "order": {"type": "integer", "enum": [1, 2, 3]},
                         "competencies": arr(STR), "sources": arr(SOURCE),
                         "added": arr(obj({"competency": STR, "why": STR}))})),
    "coverage": arr(obj({"id": STR, "expect": {"type": "string", "enum": list(LEVELS)}, "note": STR})),
    "decisions": arr(obj({"about": STR, "chose": STR, "why": STR, "rejected": STR,
                          "evidence": arr(obj({"project": STR, "quote": STR}))})),
    "doubts": arr(STR)})


def items(case):
    """역량 → 덮을 거리. 대개 역량 하나가 거리 하나다.
    예외: 유형이 '도구'이고 근거 문장이 같으며 그 문장이 '등·또는·중 하나' 처럼 고를 거리를 말하면 한 거리로 본다.
    "Isaac Sim, Omniverse, Blender, Unreal Engine 등" 은 넷 중 하나의 경험을 묻는다. 넷으로 세면 Isaac Sim 과 Omniverse 를
    함께 덮는 후보가 우대 둘을 얻어, Blender 하나를 덮는 후보보다 앞서 돌리기 어려운 쪽이 먼저 뽑힌다 (hand_naver.md).
    유형이 지식·수행이면 같은 문장이어도 각각 요구한다: "연산 및 I/O 병목" 은 둘 다, "Judge 와 캡셔닝 프롬프트" 도 둘 다다.
    → [[cid, ...]] 공고 차례."""
    text = {s["id"]: s["text"] for s in case["sentences"]}
    groups, tools = [], {}
    for c in case["competencies"]:
        ev = c["evidence_id"].split(",")[0].strip()
        if c["type"] == "도구" and ALTERNATIVE.search(text.get(ev, "")):
            if ev not in tools:
                tools[ev] = []
                groups.append(tools[ev])
            tools[ev].append(c["id"])
        else:
            groups.append([c["id"]])
    return groups


def _value(cells, group):
    return max(VALUE[cells.get(cid, {}).get("level", "없음")] for cid in group)


def pick_complements(case, cells, order, k=MAX_COMPLEMENTS):
    """판정한 후보의 칸들(cells, 후보 차례)과 순위(order, 첫째가 바탕) → [(후보 번호, (필수 몫, 우대 몫, 나머지 몫))].
    탐욕: 지금 덮은 정도(처음은 바탕)보다 더 덮는 몫을 단계별로 세어 튜플로 견주고(필수 먼저) 가장 큰 후보를 더한다.
    바탕이 필수를 모두 '있음'으로 덮으면 필수 몫은 누구나 0 이라 우대 → 나머지로 고른다 (네이버). 같으면 순위가 앞인 후보.
    멈춤: k 개를 골랐거나, 가장 큰 몫이 필수·우대 0 이고 나머지 1.0 미만일 때 (반 칸 하나를 위해 재료를 늘리지 않는다)."""
    tier = {c["id"]: tier_of(c) for c in case["competencies"]}
    groups = items(case)
    cur = [_value(cells[order[0]], g) for g in groups]
    chosen = []
    while len(chosen) < k:
        best, gain = None, None
        for i in order[1:]:
            if i in (j for j, _ in chosen):
                continue
            g = tuple(sum(max(0, _value(cells[i], grp) - cur[n]) for n, grp in enumerate(groups) if tier[grp[0]] == t)
                      for t in TIERS)
            if gain is None or g > gain:
                best, gain = i, g
        if best is None or (not any(gain[:2]) and gain[2] < 1.0):
            break
        chosen.append((best, gain))
        cur = [max(cur[n], _value(cells[best], grp)) for n, grp in enumerate(groups)]
    return chosen


def _key(title):
    """프로젝트 이름 견주기용. 공용 호출(shared.llm)이 답 안의 큰따옴표를 작은따옴표로 바꾸게 하므로 따옴표를 떼고 견준다."""
    return title.replace('"', "'").strip("' ")


def _project(role, c, text, cells, adds=()):
    got = "".join(f'<cell c="{cid}" level="{x["level"]}">{x["quote"]}</cell>'
                  for cid, x in sorted(cells.items()) if x["level"] != "없음")
    extra = f' adds="{",".join(adds)}"' if adds else ""
    return f'<project role="{role}" title="{c["title"]}" url="{c.get("url", "")}"{extra}>\n<text>{text}</text>\n<cells>{got}</cells>\n</project>'


def request(case, projects, team):
    """공고와 프로젝트들 → LLM 에 줄 글. projects = [{c, text, cells, role, adds}] 첫째가 바탕."""
    sents = "\n".join(f'<s id="{s["id"]}" section="{s["section"]}">{s["text"]}</s>'
                      for s in case["sentences"] if s.get("section") != "전형")
    base = projects[0]["cells"]
    comps = "\n".join(f'<c id="{c["id"]}" tier="{tier_of(c)}" type="{c["type"]}" must="{"yes" if c["type"] in MUST else "no"}" '
                      + (f'base="{base.get(c["id"], {}).get("level", "없음")}" ' if tier_of(c) == TIERS[0] else "")
                      + f'evidence="{c["evidence_id"]}">{c["name"]}</c>'
                      for c in case["competencies"])
    p = case["posting"]
    return (f'<team members="{team["members"]}" weeks="{team["weeks"]}" budget_hours="{team["budget_hours"]}">'
            "Hours are whole-team project hours. Study time is separate.</team>\n"
            f'<posting company="{p.get("company", "")}" title="{p.get("title", "")}">\n{sents}\n</posting>\n'
            f"<competencies>\n{comps}\n</competencies>\n"
            + "\n".join(_project(x["role"], x["c"], x["text"], x["cells"], x.get("adds", ())) for x in projects)
            + f'\nWrite the full project now: {PACKAGES[0]} to {PACKAGES[1]} packages, one coverage row for each of the '
              f'{len(case["competencies"])} competencies, decisions, and doubts.')


def check(got, case, projects, team):
    """LLM 의 답 → [{rule, level, detail}]. level 'fix' 는 통과를 막는 것, 'warn' 은 적어 두기만 하는 것.
    projects = [{c, text, cells, role}] 첫째가 바탕. 규칙 번호는 research/adapt/automation.md 1절의 첫 판(R1~R13)을 따른다.
    그 뒤 automation.md 는 번호를 바꿨다 (필수는 바탕에서 = 거기 R14, 덮기 목표 = 거기 R7). 대응은 research/adapt/auto_vs_hand.md.
    R0 (경고): 바탕 판정이 '있음'으로 덮지 못한 필수. 고른 바탕에 대한 사실이라 답이 고칠 수 없다.
    R7: 필수는 모두 핵심 묶음에서 덮인다. 바탕이 '있음'인 필수는 바탕을 출처(for)로 둔다.
        바탕이 못 덮는 필수는 보완을 출처로 두거나(그 칸은 R3 가 본다), 아무도 못 덮으면 added 로 둔다.
    R14 (경고): 덮기 목표. 수행·협업·태도·도구 역량이 핵심 묶음에서 있음·일부인가. 지식은 교육자료로 넘겨도 된다.
    R10 (경고): 공고가 고를 거리로 묶은 도구는 하나가 핵심에서 있음, 나머지도 일부 이상 (같은 장면을 다른 도구로 내보내는 싼 길로).
    덮기 목표는 억지로 채우지 않는다 (11/18 사용자 규칙). 협업·태도가 '있음'이어도 경고하지 않는다 (과정 산출물로 덮는다)."""
    out = []

    def bad(rule, detail, level="fix"):
        out.append({"rule": rule, "level": level, "detail": detail})

    by = {_key(x["c"]["title"]): x for x in projects}
    comp = {c["id"]: c for c in case["competencies"]}
    packs = got["packages"]
    core = [p for p in packs if p["core"]]

    def quote(where, project, q):
        if _key(project) not in by:
            bad("R2", f"{where}: 출처 '{project}' 는 넘긴 프로젝트가 아니다")
        elif _ELLIPSIS.search(q) or not quote_ok(q, by[_key(project)]["text"]):
            bad("R1", f"{where}: 구절이 '{project}' 글에 그대로 없다. 줄임표 없이 글에서 그대로 베껴라: {q[:60]}")
        elif len(q.split()) < MIN_WORDS:
            bad("R1", f"{where}: 구절 '{q}' 는 글에 있지만 {len(q.split())}낱말이라 짧다. "
                      f"글에서 앞뒤 낱말(목록이면 이웃 항목)까지 이어 {MIN_WORDS}낱말 이상 그대로 베껴라")

    for p in packs:
        backed = set()
        for s in p["sources"]:
            quote(p["id"], s["project"], s["quote"])
            for cid in s["for"]:
                backed.add(cid)
                if _key(s["project"]) in by and by[_key(s["project"])]["cells"].get(cid, {}).get("level", "없음") == "없음":
                    bad("R3", f"{p['id']}: {cid} 를 '{s['project']}' 에서 빌렸다는데 그 칸은 없음이다. 그 출처의 for 에서 {cid} 를 빼라. "
                              f"다른 입력 프로젝트의 칸이 덮으면 그 프로젝트를 출처로, 아무도 덮지 않으면 added 에 까닭과 함께 둬라")
        added = {a["competency"] for a in p["added"]}
        for cid in added:
            if any(x["cells"].get(cid, {}).get("level") == "있음" for x in projects):
                bad("R4", f"{p['id']}: {cid} 는 입력 프로젝트가 있음으로 덮는데 added 에 있다. 그 칸을 의심했다면 doubts 에 있어야 한다",
                    "warn")
        for cid in set(p["competencies"]) - backed - added:
            bad("R4", f"{p['id']}: {cid} 가 출처의 for 에도 added 에도 없다")
        for cid in set(p["competencies"]) - set(comp):
            bad("R8", f"{p['id']}: 없는 역량 id {cid}")
        if not HOURS[0] <= p["hours"] <= HOURS[1]:
            bad("R5", f"{p['id']}: {p['hours']}시간. 묶음 하나는 {HOURS[0]}~{HOURS[1]}시간")
    for d in got["decisions"]:
        for e in d["evidence"]:
            quote(f"결정 {d['about']}", e["project"], e["quote"])

    hours = sum(p["hours"] for p in core)
    if hours > team["budget_hours"]:
        bad("R5", f"핵심 시간 {hours} 이 예산 {team['budget_hours']} 을 넘는다")
    ids = [p["id"] for p in packs]
    if not PACKAGES[0] <= len(packs) <= PACKAGES[1]:
        bad("R6", f"묶음 {len(packs)}개. {PACKAGES[0]}~{PACKAGES[1]}개여야 한다")
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"W\d+", i) for i in ids):
        bad("R6", f"묶음 id 가 W1, W2 … 꼴로 겹치지 않아야 한다: {ids}")

    cov = {}
    for r in got["coverage"]:
        if r["id"] in cov:
            bad("R8", f"덮기 표에 {r['id']} 가 두 번 있다")
        cov[r["id"]] = r
    for cid in set(comp) - set(cov):
        bad("R8", f"덮기 표에 {cid} 가 없다")
    for cid in set(cov) - set(comp):
        bad("R8", f"덮기 표에 없는 역량 id {cid}")
    in_core = {cid for p in core for cid in p["competencies"]}
    base = _key(projects[0]["c"]["title"])
    from_base = {cid for p in core for s in p["sources"] if _key(s["project"]) == base for cid in s["for"]
                 if cid in p["competencies"]}
    for cid, r in cov.items():
        linked = linked_packages(packs, cid)
        if cid not in comp:
            continue
        if r["expect"] == "없음" and not r["note"].strip():
            bad("R13", f"{cid} 를 덮지 않는데 까닭이 없다")
        if r["expect"] != "없음" and not linked:
            bad("R8", f"{cid} 를 {r['expect']} 로 적었지만 그 역량을 적은 묶음이 없다")
    for cid, c in comp.items():
        if tier_of(c) != TIERS[0]:
            continue
        on_base = projects[0]["cells"].get(cid, {}).get("level", "없음")
        if on_base != "있음":
            bad("R0", f"필수 {cid} 를 바탕 판정이 있음으로 덮지 않는다 ({on_base}). 보완이나 AI 가 더한 일로 채운다", "warn")
        if cid not in in_core or cov.get(cid, {}).get("expect", "없음") == "없음":
            bad("R7", f"필수 {cid} 가 핵심 묶음에서 덮이지 않는다. 핵심 묶음의 competencies 에 넣고 덮기 표를 있음·일부로 적어라")
        elif on_base == "있음" and cid not in from_base:
            bad("R7", f"필수 {cid} 는 바탕이 있음으로 덮으니 바탕을 출처로 둔 핵심 묶음의 for 에 넣어라")

    base_hours = sum(p["hours"] for p in core if any(_key(s["project"]) == base for s in p["sources"]))
    if hours and base_hours < BASE_SHARE * hours:
        bad("R9", f"바탕을 출처로 둔 핵심 묶음이 {base_hours}/{hours}시간. {BASE_SHARE:.0%} 이상이어야 바탕이 뼈대다")

    level = core_levels(got, case)
    for cid, c in comp.items():
        if c["type"] in MUST and level[cid] == "없음":
            bad("R14", f"덮기 목표: {c['type']} {cid} 를 핵심 묶음이 덮지 않는다 (까닭: {cov.get(cid, {}).get('note', '')[:60]})", "warn")
    for group in (g for g in items(case) if len(g) > 1):
        if not any(level[cid] == "있음" for cid in group) or any(level[cid] == "없음" for cid in group):
            bad("R10", f"고를 거리로 묶은 도구 {group}: 하나는 핵심에서 있음, 나머지는 일부 이상이 목표다 "
                       f"(지금 {[level[cid] for cid in group]})", "warn")

    used = {_key(s["project"]) for p in packs for s in p["sources"]} | {_key(e["project"]) for d in got["decisions"]
                                                                       for e in d["evidence"]}
    said = _key(" ".join(d["about"] + " " + d["chose"] + " " + d["rejected"] for d in got["decisions"]))
    for x in projects[1:]:
        t = _key(x["c"]["title"])
        if t not in used and t not in said:
            bad("R11", f"보완 '{t}' 를 쓰지도, 버린 까닭을 적지도 않았다", "warn")
    return out


def drop_unnamed_tools(got, case):
    """도구 역량(React, Go 처럼 영문 이름이 있는 것)은 그 이름이 묶음 글(이름·할 일·산출물)에 있어야 그 묶음에 붙인다.
    11/19 AWS 응용이 React 를 React 가 한 번도 안 나오는 CI/CD 묶음에 붙여, 덱은 '프로젝트로 배움', 리포트는 '교육자료로만'으로 어긋났다.
    어느 묶음에도 남지 않은 도구는 덮기 표에서 없음으로 내린다. 뺀 (묶음, 역량) 목록을 돌려준다."""
    tools = {c["id"]: m.group(0) for c in case["competencies"] if c["type"] == "도구"
             for m in [re.search(r"[A-Za-z][A-Za-z0-9.+#-]*", c["name"])] if m}
    dropped = []
    for p in got["packages"]:
        text = " ".join(str(p.get(k, "")) for k in ("name", "do", "out"))
        keep = [cid for cid in p["competencies"] if cid not in tools
                or re.search(rf"(?<![A-Za-z]){re.escape(tools[cid])}(?![A-Za-z])", text, re.I)]
        gone = [cid for cid in p["competencies"] if cid not in keep]
        dropped += [(p["id"], cid) for cid in gone]
        p["competencies"] = keep
        for s in p.get("sources", []):
            s["for"] = [cid for cid in s["for"] if cid not in gone]
        p["sources"] = [s for s in p.get("sources", []) if s["for"]]
        p["added"] = [x for x in p.get("added", []) if (x.get("competency") if isinstance(x, dict) else x) not in gone]
    left = {cid for p in got["packages"] for cid in p["competencies"]}
    for r in got["coverage"]:
        if r["id"] in tools and r["id"] not in left and r["expect"] != "없음":
            r["expect"], r["note"] = "없음", f"{tools[r['id']]} 를 다루는 묶음이 없어 뺌 (교육자료에서 배움)"
    return dropped


def linked_packages(packs, cid):
    """그 역량을 competencies 에 적은 묶음 id. 덮기 표의 묶음 칸은 모델에게 두 번 적게 하지 않고 여기서 만든다
    (11/18·11/19 AWS 실행에서 모델이 적은 묶음 칸이 실제 묶음과 어긋나 R8 로 걸리기를 거듭했다)."""
    return sorted(p["id"] for p in packs if cid in p["competencies"])


def core_levels(got, case):
    """역량 id → 핵심 묶음 기준 등급. 핵심 묶음에 없으면 덮기 표가 뭐라 하든 없음."""
    in_core = {cid for p in got["packages"] if p["core"] for cid in p["competencies"]}
    cov = {r["id"]: r["expect"] for r in got["coverage"]}
    return {c["id"]: cov.get(c["id"], "없음") if c["id"] in in_core else "없음" for c in case["competencies"]}


def targets(got, case):
    """덮기 목표 셈: 꼭 덮을 역량(수행·협업·태도·도구) 가운데 핵심에서 있음·일부인 수, 지식 가운데 덮은 수, 도구마다 등급."""
    lv = core_levels(got, case)
    must = [c["id"] for c in case["competencies"] if c["type"] in MUST]
    rest = [c["id"] for c in case["competencies"] if c["type"] not in MUST]
    return {"must_cover": f"{sum(lv[c] != '없음' for c in must)}/{len(must)}",
            "knowledge_touched": f"{sum(lv[c] != '없음' for c in rest)}/{len(rest)}",
            "tools": {c["id"]: lv[c["id"]] for c in case["competencies"] if c["type"] == "도구"}}


def tier_counts(got, case, base_cells):
    """덮기 표 → 단계별 {있음, 일부, 없음, of}. core 는 핵심 묶음만, with_extension 은 모든 묶음, base_alone_by_judge 는 바탕 판정."""
    packs = got["packages"]
    cov = {r["id"]: r for r in got["coverage"]}

    def count(keep):
        n = {t: {"있음": 0, "일부": 0, "없음": 0, "of": 0} for t in TIERS}
        for c in case["competencies"]:
            r = cov.get(c["id"], {"expect": "없음"})
            hit = any(keep(p) and c["id"] in p["competencies"] for p in packs)
            n[tier_of(c)][r["expect"] if hit else "없음"] += 1
            n[tier_of(c)]["of"] += 1
        return n

    alone = {t: {"있음": 0, "일부": 0} for t in TIERS}
    for c in case["competencies"]:
        lv = base_cells.get(c["id"], {}).get("level", "없음")
        if lv != "없음":
            alone[tier_of(c)][lv] += 1
    return {"core": count(lambda p: p["core"]), "with_extension": count(lambda p: True), "base_alone_by_judge": alone}


def adapt(case, candidates, cells, order, team=TEAM):
    """판정을 마친 후보들 → 응용 프로젝트 하나 (hand_naver.json 과 같은 꼴 + checks).
    candidates·cells 는 같은 차례, order 는 pick_best 의 순위(첫째가 바탕).
    <공고>.adapt.json 에 두고, 모델에 줄 글(지시문 + 요청)이 같으면 다시 쓴다 (돈 0)."""
    path = config.OUTPUTS / "project" / f'{case["case"]}.adapt.json'
    picked = pick_complements(case, cells, order)
    titles = [candidates[order[0]]["title"]] + [candidates[i]["title"] for i, _ in picked]
    tier = {c["id"]: tier_of(c) for c in case["competencies"]}
    base_cells = cells[order[0]]
    covered = {cid for cid, x in base_cells.items() if x["level"] != "없음"}
    projects = [{"role": "base", "c": candidates[order[0]], "text": shown(candidates[order[0]]), "cells": base_cells}]
    for i, _ in picked:
        adds = [cid for cid, x in sorted(cells[i].items()) if x["level"] != "없음" and cid not in covered]
        covered |= set(adds)
        projects.append({"role": "complement", "c": candidates[i], "text": shown(candidates[i]), "cells": cells[i], "adds": adds})
    user = request(case, projects, team)
    key = hashlib.sha256((SYSTEM + user).encode()).hexdigest()[:16]
    if path.exists():
        saved = json.loads(path.read_text("utf-8"))
        if saved.get("request") == key:
            return saved
    before = llm.USAGE.get("krw", 0.0)
    got = llm.ask_json(user, SYSTEM, SCHEMA, model=MODEL, max_tokens=24000)
    dropped = drop_unnamed_tools(got, case)
    first = issues = check(got, case, projects, team)
    # 11/18 실행 세 번 모두 첫 답이 빈 꼴(출력 35토큰)이었고, 다시 물어도 비었다. 앞 답과 걸린 것을 함께 준 다시 쓰기에서는 채웠다.
    # 그래서 빈 답이면 다시 쓰기를 한 번 더 준다 (빈 답 뒤 첫 다시 쓰기는 사실상 첫 답이다)
    blank = not got["packages"]
    rewrote, limit = 0, 2 if blank else 1
    while rewrote < limit and any(x["level"] == "fix" for x in issues):
        problems = "\n".join(f'- [{x["rule"]}]{" (선택)" if x["level"] == "warn" else ""} {x["detail"]}' for x in issues)
        again = (user + "\n<previous_answer>" + json.dumps(got, ensure_ascii=False) + "</previous_answer>\n"
                 f"<problems>\n{problems}\n</problems>\n"
                 "Code checks found the problems above in your previous answer. Return the full corrected JSON. "
                 "Fix every problem not marked (선택). Items marked (선택) are coverage targets or facts about the inputs: "
                 "act on them only where the project stays natural. Change only what is needed.")
        got = llm.ask_json(again, SYSTEM, SCHEMA, model=MODEL, max_tokens=24000)
        dropped = drop_unnamed_tools(got, case)
        issues, rewrote = check(got, case, projects, team), rewrote + 1
    names = {c["id"]: c["name"] for c in case["competencies"]}
    packs = got["packages"]
    core_h = sum(p["hours"] for p in packs if p["core"])
    total_h = sum(p["hours"] for p in packs)
    out = {"case": case["case"], "request": key, "made": f"{MODEL}, 응용 한 번{' (첫 답 빔)' if blank else ''}{f' + 다시 쓰기 {rewrote}번' if rewrote else ''}", "team": team,
           "base": titles[0], "complements": titles[1:],
           "complement_gains": [{"title": candidates[i]["title"], **dict(zip(TIERS, g))} for i, g in picked],
           "project": {"title": got["title"], "goal": got["goal"], "packages": packs},
           "hours": {"core": core_h, "extension": total_h - core_h, "total": total_h, "budget": team["budget_hours"]},
           "coverage": [{"id": r["id"], "name": names.get(r["id"], ""), "tier": tier.get(r["id"], ""),
                         "packages": linked_packages(packs, r["id"]), "expect": r["expect"], "note": r["note"]}
                        for r in sorted(got["coverage"], key=lambda r: r["id"])],
           "tier_counts": tier_counts(got, case, base_cells),
           "decisions": got["decisions"], "unverified": got["doubts"],
           "checks": {"passed": not any(x["level"] == "fix" for x in issues), "issues": issues, "first_issues": first,
                      "rewrote": rewrote, "dropped_tool_claims": dropped, **targets(got, case),
                      "krw": round(llm.USAGE.get("krw", 0.0) - before, 1)}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    return out
