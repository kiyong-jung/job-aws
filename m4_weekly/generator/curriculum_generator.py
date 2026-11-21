#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RoundLab: schema-driven, deterministic project curriculum generator.

Input 1: upstream adapted project (`*.adapt.json`, containing packages[]).
Input 2: shortlisted educational materials (core + reference, with skill IDs and durations).
Output: auditable curriculum.json and curriculum.md; no LLM or API required.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Any


SLOT_MINUTES = 10
SIZE_HOURS = {"소형": 7, "중형": 14, "대형": 30}


class InputError(ValueError):
    """An input field violates the documented integration contract."""


def fail(message: str) -> None:
    raise InputError(message)


def text_value(value: Any, label: str, *, required: bool = True) -> str:
    s = str(value or "").strip()
    if required and not s:
        fail(f"{label}: 비어 있습니다")
    return s


def ids(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        fail(f"{label}: 문자열 또는 ID 객체의 배열이어야 합니다")
    out: list[str] = []
    for item in value:
        val = item.get("id") if isinstance(item, dict) else item
        if not isinstance(val, str) or not val.strip():
            fail(f"{label}: 항목마다 역량 ID가 필요합니다: {item!r}")
        out.append(val.strip())
    return tuple(dict.fromkeys(out))


def to_minutes(value: Any, label: str, multiplier: int, *, ceiling: bool = False) -> int:
    if isinstance(value, bool):
        fail(f"{label}: 시간은 숫자여야 합니다")
    try:
        n = Decimal(str(value)) * multiplier
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InputError(f"{label}: 시간값을 읽을 수 없습니다: {value!r}") from exc
    if not n.is_finite() or n <= 0:
        fail(f"{label}: 양수여야 합니다: {value!r}")
    rounding = ROUND_FLOOR if ceiling else ROUND_CEILING
    slots = (n / SLOT_MINUTES).to_integral_value(rounding=rounding)
    if slots == 0:
        fail(f"{label}: 10분 이상이어야 합니다")
    return int(slots) * SLOT_MINUTES


def get_duration(obj: dict, label: str, *, project_package: bool = False) -> int | None:
    # Project packages.hours and material hours are hours, not minutes.
    keys = (("hours", 60), ("estimated_hours", 60)) if project_package else (
        ("estimated_minutes", 1), ("minutes", 1), ("duration_minutes", 1),
        ("estimated_hours", 60), ("hours", 60))
    for key, scale in keys:
        if obj.get(key) is not None and obj.get(key) != "":
            return to_minutes(obj[key], f"{label}.{key}", scale)
    return None


def read_json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise InputError(f"파일을 읽지 못했습니다: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON 파싱 실패: {path}: {exc}") from exc


@dataclass(frozen=True)
class Task:
    id: str
    do: str
    out: str
    minutes: int
    core: bool
    competencies: tuple[str, ...]
    depends_on: tuple[str, ...]
    sources: tuple[Any, ...]
    added: tuple[Any, ...]
    position: int
    requires: tuple[str, ...] | None
    completion_check: str
    excerpts: tuple[str, ...]


@dataclass(frozen=True)
class LearningUnit:
    id: str
    material_id: str
    role: str
    title: str
    url: str
    minutes: int | None
    competencies: tuple[str, ...]
    evidence: str
    section: str | None
    requires: tuple[str, ...]
    method: str
    explicit: bool
    teaches_explicit: bool
    requires_explicit: bool
    excerpts: tuple[str, ...]


def normalize_project(obj: Any) -> tuple[dict, list[Task], list[str]]:
    if not isinstance(obj, dict):
        fail("project: 최상위 JSON은 객체여야 합니다")
    title = text_value(obj.get("title"), "project.title")
    pkgs = obj.get("packages")
    if not isinstance(pkgs, list) or not pkgs:
        fail("project.packages: 하나 이상의 작업 묶음이 필요합니다")
    tasks: list[Task] = []
    seen: set[str] = set()
    notes: list[str] = []
    for n, raw in enumerate(pkgs, 1):
        if not isinstance(raw, dict):
            fail(f"project.packages[{n}]: 객체여야 합니다")
        tid = text_value(raw.get("id") or f"W{n}", f"packages[{n}].id")
        if tid in seen:
            fail(f"중복된 작업 ID: {tid}")
        seen.add(tid)
        if not isinstance(raw.get("core"), bool):
            fail(f"packages[{n}].core: true 또는 false가 필요합니다")
        task = Task(
            id=tid, do=text_value(raw.get("do"), f"packages[{n}].do"),
            out=text_value(raw.get("out"), f"packages[{n}].out"),
            minutes=get_duration(raw, f"packages[{n}]", project_package=True) or 0,
            core=raw["core"], competencies=ids(raw.get("competencies"), f"packages[{n}].competencies"),
            depends_on=ids(raw.get("depends_on"), f"packages[{n}].depends_on"),
            sources=tuple(raw.get("sources") or []), added=tuple(raw.get("added") or []),
            position=n, excerpts=excerpts(raw), requires=ids(raw["requires"], f"{tid}.requires") if "requires" in raw else None,
            completion_check=text_value(raw.get("completion_check"), f"{tid}.completion_check", required=False))
        if task.minutes <= 0:
            fail(f"packages[{n}].hours: 작업시간(시간 단위)이 반드시 필요합니다")
        if not task.competencies:
            notes.append(f"{tid}: 연결 역량 ID가 없습니다. 학습자료 자동 연결에 추가 확인이 필요합니다")
        tasks.append(task)
    if not any(t.core for t in tasks):
        fail("핵심 작업(core=true)이 하나 이상 필요합니다")
    valid = {t.id for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            if dep not in valid:
                fail(f"{t.id}: 존재하지 않는 선행 작업 {dep}")
            if dep == t.id:
                fail(f"{t.id}: 자기 자신을 선행 작업으로 지정할 수 없습니다")
    topo(tasks)  # verify cycles, preserves input order for ties
    if not any(t.depends_on for t in tasks):
        notes.append("선행 작업 depends_on이 없습니다. 입력 packages[] 순서를 기본 배치 순서로 사용합니다")
    return obj, tasks, notes


def topo(tasks: list[Task]) -> list[Task]:
    by_id = {t.id: t for t in tasks}
    deg = {t.id: len(t.depends_on) for t in tasks}
    edges: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d not in edges:
                fail(f"{t.id}: 알 수 없는 선행 작업 {d}")
            edges[d].append(t.id)
    ready = [(t.position, t.id) for t in tasks if deg[t.id] == 0]
    heapq.heapify(ready)
    order: list[Task] = []
    while ready:
        _, tid = heapq.heappop(ready)
        order.append(by_id[tid])
        for nxt in edges[tid]:
            deg[nxt] -= 1
            if deg[nxt] == 0:
                heapq.heappush(ready, (by_id[nxt].position, nxt))
    if len(order) != len(tasks):
        fail("작업 선행 관계에 순환(cycle)이 있습니다")
    return order


def material_role(raw: Any) -> str:
    x = str(raw or "reference").strip().lower()
    if x in {"core", "essential", "main", "required", "핵심", "필수"}:
        return "core"
    if x in {"reference", "ref", "supplement", "optional", "참고", "보조"}:
        return "reference"
    fail(f"교육자료 role 값이 올바르지 않습니다: {raw!r}")


def excerpts(*records):
    return tuple(dict.fromkeys(value.strip() for row in records
        for key in ("summary", "description", "prerequisites", "prerequisite_text", "quote", "overview")
        if isinstance(value := row.get(key), str) and value.strip()))


def normalize_materials(data: Any) -> tuple[list[LearningUnit], list[str], dict[str, int]]:
    if isinstance(data, list):
        mats = data
    elif isinstance(data, dict):
        if isinstance(data.get("materials"), list):
            mats = data["materials"]
        else:
            mats = []
            for key, role in (("core", "core"), ("essential", "core"), ("references", "reference"),
                              ("reference", "reference"), ("supplementary", "reference")):
                arr = data.get(key, [])
                if not isinstance(arr, list):
                    fail(f"materials.{key}: 배열이어야 합니다")
                mats.extend([{**m, "role": role} for m in arr] if all(isinstance(m, dict) for m in arr) else arr)
    else:
        fail("materials: 최상위 JSON은 배열 또는 객체여야 합니다")
    if not mats:
        fail("교육자료가 비어 있습니다")
    result: list[LearningUnit] = []
    warnings: list[str] = []
    seen_materials: set[str] = set()
    role_counts = {"core": 0, "reference": 0}
    for k, m in enumerate(mats, 1):
        if not isinstance(m, dict):
            fail(f"materials[{k}]: 객체여야 합니다")
        mid = text_value(m.get("id") or f"M{k}", f"materials[{k}].id")
        if mid in seen_materials:
            fail(f"중복 교육자료 ID: {mid}")
        seen_materials.add(mid)
        role = material_role(m.get("role"))
        role_counts[role] += 1
        title = text_value(m.get("title"), f"materials[{k}].title")
        url = text_value(m.get("url"), f"materials[{k}].url", required=False)
        if not url:
            warnings.append(f"{mid}: 자료 URL이 없어서 학습 출처를 추적할 수 없습니다")
        parent_skills = ids(m.get("teaches", m.get("competencies", m.get("skill_ids"))), f"materials[{k}].competencies")
        sec = m.get("sections")
        can_use_sections = (isinstance(sec, list) and bool(sec)
                            and all(isinstance(s, dict) and any(k in s for k in ("teaches", "competencies", "skill_ids"))
                                    for s in sec))
        if sec and not can_use_sections:
            warnings.append(f"{mid}: sections별 역량 ID가 없어 자료 전체 단위로 취급합니다")
        if can_use_sections:
            for j, s in enumerate(sec, 1):
                sid = text_value(s.get("id") or f"S{j}", f"{mid}.sections[{j}].id")
                result.append(LearningUnit(
                    id=f"{mid}/{sid}", material_id=mid, role=role,
                    title=f"{title} — {text_value(s.get('title') or sid, f'{mid}.sections[{j}].title')}",
                    url=text_value(s.get("url") or url, f"{mid}.sections[{j}].url", required=False),
                    minutes=get_duration(s, f"{mid}.sections[{j}]"),
                    competencies=ids(s.get("teaches", s.get("competencies", s.get("skill_ids"))), f"{mid}.sections[{j}].competencies"),
                    evidence=text_value(s.get("evidence") or m.get("evidence"), f"{mid}.evidence", required=False),
                    section=sid, requires=tuple(dict.fromkeys((*ids(m.get("requires"), mid), *ids(s.get("requires"), sid)))),
                    method=str(s.get("study_method") or m.get("study_method") or ""),
                    excerpts=excerpts(m, s), teaches_explicit="teaches" in s, requires_explicit="requires" in s or "requires" in m,
                    explicit=any(k in obj for obj in (s, m) for k in ("teaches", "requires"))))
        else:
            result.append(LearningUnit(
                id=mid, material_id=mid, role=role, title=title, url=url,
                minutes=get_duration(m, f"materials[{k}]"), competencies=parent_skills,
                evidence=text_value(m.get("evidence"), f"{mid}.evidence", required=False), section=text_value(m.get("section"), f"{mid}.section", required=False) or None,
                requires=ids(m.get("requires"), mid), method=str(m.get("study_method") or ""),
                explicit="teaches" in m or "requires" in m, excerpts=excerpts(m), teaches_explicit="teaches" in m, requires_explicit="requires" in m))
        if not parent_skills and not (can_use_sections and any(x.material_id == mid and x.competencies for x in result)):
            warnings.append(f"{mid}: 대응 역량 ID가 없습니다. 제목만으로 역량을 추정하지 않습니다")
    if role_counts["core"] != 2 or not 3 <= role_counts["reference"] <= 4:
        warnings.append("교육자료 개수가 관례(핵심 2개 + 참고 3~4개)와 다릅니다. 범용 입력이므로 실행은 허용합니다")
    if len({unit.id for unit in result}) != len(result):
        fail("교육자료 구간 ID가 중복됩니다")
    return result, warnings, role_counts


def dependency_closure(selected: set[str], by_id: dict[str, Task]) -> set[str]:
    closure = set(selected)
    queue = list(selected)
    while queue:
        for d in by_id[queue.pop()].depends_on:
            if d not in closure:
                closure.add(d)
                queue.append(d)
    return closure


def choose_units(selected_tasks: list[Task], units: list[LearningUnit]) -> dict:
    """Keep relevant core units; exact min-minute cover on reference units.

    With missing skill-ID mappings, compute the best provable partial cover and report gaps.
    A unit with unknown duration is NOT assigned a guessed duration.
    """
    needed = set(itertools.chain.from_iterable(t.competencies for t in selected_tasks))
    base = [u for u in units if u.role == "core" and needed.intersection(u.competencies)]
    known_core = set(itertools.chain.from_iterable(u.competencies for u in base))
    missing = sorted(needed - known_core)
    known_refs = [u for u in units if u.role == "reference" and u.minutes is not None
                  and bool(set(u.competencies).intersection(missing))]
    # Exact DP is appropriate for the recommended 3–4 reference items.
    # Fallback to deterministic greedy if sections multiply the candidate count.
    method = "exact_dp"
    if len(known_refs) <= 20:
        bit = {s: i for i, s in enumerate(missing)}
        dp: dict[int, tuple[int, int, tuple[str, ...]]] = {0: (0, 0, ())}
        by_unit = {u.id: u for u in units}
        for u in sorted(known_refs, key=lambda x: x.id):
            mask = 0
            for skill in set(u.competencies).intersection(bit):
                mask |= 1 << bit[skill]
            next_dp = dict(dp)
            for current, value in dp.items():
                nxt = current | mask
                proposed = (value[0] + (u.minutes or 0), value[1] + 1, value[2] + (u.id,))
                if nxt not in next_dp or proposed < next_dp[nxt]:
                    next_dp[nxt] = proposed
            dp = next_dp
        _, best = min(dp.items(), key=lambda kv: (-kv[0].bit_count(), kv[1]))
        chosen = [by_unit[i] for i in best[2]]
    else:
        method = "greedy_fallback_over_20_reference_units"
        chosen = []
        remain = set(missing)
        options = list(known_refs)
        while remain and options:
            scored = sorted(options, key=lambda u: (
                -(len(set(u.competencies) & remain) / (u.minutes or 1)),
                u.minutes, u.id))
            best = scored[0]
            gain = set(best.competencies) & remain
            if not gain:
                break
            chosen.append(best)
            remain -= gain
            options.remove(best)
    already = known_core | set(itertools.chain.from_iterable(u.competencies for u in chosen))
    # Unknown duration units can explain uncovered competencies but cannot be scheduled.
    still_missing = needed - already
    unknown_refs = [u for u in units if u.role == "reference" and u.minutes is None
                    and bool(set(u.competencies) & still_missing)]
    uncovered = sorted(still_missing)
    unknown_candidate_ids = sorted(u.id for u in unknown_refs)
    chosen = sorted(base + chosen, key=lambda x: (x.role != "core", x.id))
    missing_minutes = sorted(u.id for u in chosen if u.minutes is None)
    return {"units": chosen, "needed": sorted(needed), "covered": sorted(needed & already),
            "uncovered": uncovered, "unknown_duration_selected": missing_minutes,
            "unknown_duration_candidates": unknown_candidate_ids,
            "education_minutes": sum(u.minutes or 0 for u in chosen),
            "selection_method": method}


def prerequisite_plan(tasks, units, known):
    """Walk backwards from each task. A failed branch never commits partial study."""
    acquired = set(known)
    chosen, before, gaps = [], {}, {}
    providers = {}
    for unit in units:
        for topic in unit.competencies:
            providers.setdefault(topic, []).append(unit)

    def resolve(topic, available, trail):
        if topic in available:
            return [], None
        if topic in trail:
            return [], "선수 관계 순환: " + " → ".join((*trail, topic))
        alternatives, errors = [], []
        for unit in providers.get(topic, []):
            if unit.minutes is None:
                errors.append(f"{unit.id} 학습시간 미확정")
                continue
            branch, learned = [], available.copy()
            for prior in unit.requires:
                steps, error = resolve(prior, learned, (*trail, topic))
                if error:
                    errors.append(f"{unit.id} → {error}")
                    break
                for step in steps:
                    branch.append(step)
                    learned.update(step.competencies)
            else:
                if topic not in learned:
                    branch.append(unit)
                alternatives.append((unit.role != "core", sum(s.minutes for s in branch), unit.id, branch))
        if alternatives:
            return min(alternatives, key=lambda a: a[:3])[3], None
        return [], f"{topic}: " + (" / ".join(dict.fromkeys(errors)) or "제공하는 자료가 없습니다")

    missing_sources = {}
    needed = set()
    missing = set()
    for task in tasks:
        before[task.id] = []
        required = task.competencies if task.requires is None else task.requires
        needed.update(required)
        for topic in required:
            steps, error = resolve(topic, acquired, ())
            if error:
                gaps.setdefault(task.id, []).append(error)
                missing.add(topic)
                if topic not in providers:
                    missing_sources.setdefault(task.id, []).append(topic)
            for unit in steps:
                acquired.update(unit.competencies)
                chosen.append(unit)
                before[task.id].append(unit.id)
    return {"units": chosen, "before": before, "gaps": gaps, "missing_sources": missing_sources, "needed": sorted(needed),
            "uncovered": sorted(missing), "unknown_duration_selected": [], "unknown_duration_candidates": [],
            "education_minutes": sum(u.minutes for u in chosen), "selection_method": "prerequisites"}


def learning_within_budget(tasks, units, known, budget):
    """Find a feasible lower-cost path after the core-first path exceeds the budget."""
    if budget < 0:
        return None
    required = [set(t.competencies if t.requires is None else t.requires) for t in tasks]
    timed_units = [u for u in units if u.minutes is not None]
    relevant_units = []
    for topics in required:
        relevant = topics.copy()
        while True:
            options = [u for u in timed_units if relevant.intersection(u.competencies)]
            expanded = relevant.union(*(u.requires for u in options))
            if expanded == relevant:
                break
            relevant = expanded
        relevant_units.append(options)

    first = (0, frozenset(known))
    queue = [(0, 0, first)]
    best = {first: 0}
    previous = {}
    serial = itertools.count(1)
    while queue:
        cost, _, state = heapq.heappop(queue)
        if cost != best[state]:
            continue
        index, acquired = state
        if index == len(tasks):
            steps = []
            while state != first:
                prior, unit = previous[state]
                if unit is not None:
                    steps.append((tasks[prior[0]].id, unit))
                state = prior
            before = {t.id: [] for t in tasks}
            ordered_units = []
            for tid, unit in reversed(steps):
                before[tid].append(unit.id)
                ordered_units.append(unit)
            return {"units": ordered_units, "before": before, "gaps": {},
                    "needed": sorted(set().union(*required)), "uncovered": [],
                    "unknown_duration_selected": [], "unknown_duration_candidates": [],
                    "education_minutes": cost, "selection_method": "budget_fallback"}

        if required[index] <= acquired:
            candidates = [((index + 1, acquired), None)]
        else:
            candidates = [((index, acquired.union(u.competencies)), u)
                          for u in relevant_units[index]
                          if set(u.requires) <= acquired and not set(u.competencies) <= acquired]
        for candidate, unit in candidates:
            new_cost = cost + (unit.minutes if unit is not None else 0)
            if new_cost <= budget and new_cost < best.get(candidate, budget + 1):
                best[candidate] = new_cost
                previous[candidate] = (state, unit)
                heapq.heappush(queue, (new_cost, next(serial), candidate))
    return None


def minutes_sum(tasks: list[Task]) -> int:
    return sum(t.minutes for t in tasks)


def as_hours(minutes: int) -> float:
    return round(minutes / 60, 4)


def supplemental_plan(requested, units, selected, learn, known, budget, blocked, strict):
    by_material = {}
    for unit in units:
        if unit.role == "reference":
            by_material.setdefault(unit.material_id, []).append(unit)

    first_task = {topic: index for index in reversed(range(len(selected)))
                  for topic in selected[index].competencies}
    index_by_task = {task.id: index for index, task in enumerate(selected)}
    before = learn.get("before")
    placement = {}
    for unit in learn["units"]:
        if before is not None:
            placement[unit.id] = next(index_by_task[tid] for tid, ids in before.items() if unit.id in ids)
        else:
            placement[unit.id] = min(first_task[s] for s in unit.competencies if s in first_task)

    after, decisions = {}, []
    scheduled = {unit.id: unit for unit in learn["units"]}
    for material_id in dict.fromkeys(requested):
        candidates = by_material.get(material_id)
        if not candidates:
            fail(f"참고 교육자료 ID를 찾을 수 없습니다: {material_id}")
        row = {"material_id": material_id, "title": candidates[0].title, "status": "skipped"}
        decisions.append(row)
        pending = [unit for unit in candidates if unit.id not in scheduled]
        if blocked:
            row["reason"] = "기본 일정 배정 보류"
        elif not pending:
            row.update(status="already_scheduled", reason="기본 일정에 이미 배정됨")
        elif any(unit.minutes is None for unit in pending):
            row["reason"] = "학습시간 미확정"
        elif strict and any(not unit.url or not unit.evidence or unit.evidence.strip() in
                            {"근거 확인 필요", "미정", "TBD"} for unit in pending):
            row["reason"] = "엄격 모드: 학습 근거 미확인"
        elif (cost := sum(unit.minutes for unit in pending)) > budget:
            row["reason"] = "남은 시간 부족"
        else:
            topics = {topic.removeprefix("입문-") for unit in pending for topic in unit.competencies}
            related = [i for i, task in enumerate(selected) if topics.intersection(
                topic.removeprefix("입문-") for topic in (*task.competencies, *(task.requires or ())))]

            for index in range(related[-1] if related else len(selected) - 1, len(selected)):
                available = set(known).union(*(unit.competencies for uid, unit in scheduled.items()
                                               if placement[uid] <= index))
                ordered, remaining = [], pending.copy()
                while remaining:
                    eligible = next((unit for unit in remaining if set(unit.requires) <= available), None)
                    if eligible is None:
                        break
                    remaining.remove(eligible)
                    ordered.append(eligible)
                    available.update(eligible.competencies)
                if not remaining:
                    task_id = selected[index].id
                    reason = f"{task_id} 작업 완료 후 보완학습" if related else "프로젝트 작업 완료 후 별도 보완학습"
                    related_task = selected[related[-1]].id if related else None
                    after.setdefault(task_id, []).extend((unit, reason, related_task) for unit in ordered)
                    for unit in ordered:
                        scheduled[unit.id] = unit
                        placement[unit.id] = index
                    budget -= cost
                    row.update(status="included", minutes=cost, after_task_id=task_id,
                               reason=reason)
                    break
            else:
                row["reason"] = "선수지식을 충족할 수 없음"
    return after, decisions


def build_schedule(selected: list[Task], units: list[LearningUnit], weeks: int,
                   per_week: int, total_minutes: int, before=None, after=None) -> list[dict]:
    weekly_slots, extra_weeks = divmod(total_minutes // SLOT_MINUTES, weeks)
    week_rows = [{"week": n, "capacity_minutes": per_week, "used_minutes": 0,
                  "activities": [], "deliverables_completed": []} for n in range(1, weeks + 1)]
    placed_units: set[str] = set()
    current_week = 0
    serial = 0

    def place(kind: str, title: str, activity_id: str, minutes: int, extra: dict) -> None:
        nonlocal current_week, serial
        left = minutes
        while left:
            if current_week >= len(week_rows):
                raise AssertionError("내부 오류: 주차 용량이 부족합니다")
            wk = week_rows[current_week]
            target = SLOT_MINUTES * (weekly_slots + int(current_week < extra_weeks))
            room = target - wk["used_minutes"]
            if room == 0:
                current_week += 1
                continue
            step = min(room, left)
            left -= step
            serial += 1
            activity = {"sequence": serial, "kind": kind, "id": activity_id,
                        "title": title, "minutes": step, "hours": as_hours(step),
                        "completed_in_this_chunk": left == 0, **extra}
            if kind == "project" and left == 0:
                wk["deliverables_completed"].append(extra["out"])
            wk["activities"].append(activity)
            wk["used_minutes"] += step

    def place_learning(u, task, supplemental_reason=None, related_task=None):
        if u.minutes is None:
            raise AssertionError("시간 미확정 자료는 일정 배정 불가")
        details = {
            "material_id": u.material_id, "role": u.role, "url": u.url,
            "competencies": list(u.competencies), "evidence": u.evidence,
            "section": u.section, "for_task": task.id, "requires": list(u.requires),
            "reason": f"{task.id} 작업 전 선수학습", "study_method": u.method or
            f"{u.title}의 개념을 정리하고 예제를 실행한 뒤 {task.do}에 적용합니다."}
        if supplemental_reason:
            details.update(learning_purpose="supplemental", reason=supplemental_reason, for_task=related_task,
                           study_method=u.method or f"{u.title}의 관련 구간을 공부하고 예제 결과를 기록합니다.")
        place("learning", u.title, u.id, u.minutes, details)

    unit_by_id = {u.id: u for u in units}
    for t in selected:
        ordered_units = ([unit_by_id[uid] for uid in before[t.id]] if before is not None else units)
        for u in ordered_units:
            if u.id not in placed_units and (before is not None or set(u.competencies).intersection(t.competencies)):
                place_learning(u, t)
                placed_units.add(u.id)
        place("project", t.do, t.id, t.minutes, {
            "out": t.out, "core": t.core, "competencies": list(t.competencies),
            "completion_check": t.completion_check or f"{t.out} 산출물 확인 (상세 검증 기준 미제공)",
            "prerequisites": list(t.requires if t.requires is not None else t.competencies),
            "depends_on": list(t.depends_on), "sources": list(t.sources), "added": list(t.added)})
        for u, reason, related_task in (after or {}).get(t.id, ()):
            place_learning(u, t, supplemental_reason=reason, related_task=related_task)
    if set(u.id for u in units) != placed_units:
        raise AssertionError("선택된 학습자료가 어떤 작업에도 연결되지 않았습니다")
    for wk in week_rows:
        learn_minutes = sum(a["minutes"] for a in wk["activities"] if a["kind"] == "learning")
        wk["learning_minutes"] = learn_minutes
        wk["implementation_minutes"] = wk["used_minutes"] - learn_minutes
        wk["actual_learning_percent"] = round(100 * learn_minutes / wk["used_minutes"], 1) if wk["used_minutes"] else None
        wk["recommended_learning_percent"] = (60 if wk["week"] <= 3 else 40 if wk["week"] <= 8 else 25) if weeks == 12 else None
        wk["goals"] = list(dict.fromkeys(a["title"] for a in wk["activities"]))
        wk["used_hours"] = as_hours(wk["used_minutes"])
        wk["remaining_hours"] = as_hours(per_week - wk["used_minutes"])
    return week_rows


def generate(project: Any, materials: Any, *, weeks: int, hours_per_week: float,
             strict: bool = False, analysis=None, model=None, profile=None, region=None,
             include_references=()) -> dict:
    if not isinstance(weeks, int) or isinstance(weeks, bool) or weeks <= 0:
        fail("weeks: 양의 정수여야 합니다")
    per_week = to_minutes(hours_per_week, "hours_per_week", 60, ceiling=True)
    capacity = weeks * per_week
    raw, tasks, notes = normalize_project(project)
    units, material_warnings, counts = normalize_materials(materials)
    team_csv = raw.get("team_csv") is True
    if model or analysis is not None:
        import lesson_analysis
        if model:
            analysis = lesson_analysis.propose(tasks, units, model, profile, region, team_csv)
        explicit_deps = {t.id for t, row in zip(tasks, raw["packages"]) if "depends_on" in row}
        tasks, units, analysis_provenance = lesson_analysis.apply(analysis, tasks, units, explicit_deps, revise_team_defaults=team_csv)
    notes.extend(material_warnings)
    learner = raw.get("learner", {})
    if not isinstance(learner, dict):
        fail("learner: 객체가 필요합니다")
    known = ids(learner.get("known"), "learner.known")
    explicit = bool(known or any(t.requires is not None for t in tasks) or any(u.explicit for u in units))
    ordered = topo(tasks)
    by_id = {t.id: t for t in ordered}
    upstream_hours = raw.get("hours") if isinstance(raw.get("hours"), dict) else {}
    project_budget = upstream_hours.get("budget")
    project_budget_m = (to_minutes(project_budget, "project.hours.budget", 60, ceiling=True)
                        if project_budget is not None else None)
    required = dependency_closure({t.id for t in tasks if t.core}, by_id)
    promoted = sorted(t.id for t in tasks if t.id in required and not t.core)
    if promoted:
        notes.append("핵심 작업의 선행 작업이므로 확장으로 표기된 작업도 포함: " + ", ".join(promoted))

    def evaluate(task_ids: set[str]) -> tuple[list[Task], dict, int]:
        selected = [t for t in ordered if t.id in task_ids]
        learn = prerequisite_plan(selected, units, known) if explicit else choose_units(selected, units)
        implementation = minutes_sum(selected)
        learning_budget = capacity - implementation
        if learn["education_minutes"] > learning_budget or learn["unknown_duration_selected"] or learn.get("gaps"):
            fallback = learning_within_budget(selected, units, known, learning_budget)
            if fallback is not None:
                learn = fallback
        return selected, learn, implementation + learn["education_minutes"]

    def has_blocking_gaps(plan):
        gaps = plan.get("gaps", {})
        if not (team_csv and analysis is not None and not strict):
            return bool(gaps)
        missing_sources = plan.get("missing_sources", {})
        return any(len(errors) != len(missing_sources.get(task_id, ())) for task_id, errors in gaps.items())

    selected, learn, total = evaluate(required)
    omitted: list[dict] = []
    core_over_budget = total > capacity
    core_project_budget_exceeded = (project_budget_m is not None and
                                    minutes_sum(selected) > project_budget_m)
    if not (core_over_budget or core_project_budget_exceeded or has_blocking_gaps(learn)) and not learn["unknown_duration_selected"]:
        # Extension tasks are optional. Include each task and its prerequisites only if feasible.
        for t in ordered:
            if t.id in required:
                continue
            candidate = dependency_closure(required | {t.id}, by_id)
            new_tasks, new_learn, new_total = evaluate(candidate)
            if has_blocking_gaps(new_learn):
                omitted.append({"id": t.id, "reason": "확장 작업 선수학습 미충족", "gaps": new_learn["gaps"]})
            elif new_learn["unknown_duration_selected"]:
                omitted.append({"id": t.id, "reason": "필요한 학습자료 시간 미확정"})
            elif project_budget_m is not None and minutes_sum(new_tasks) > project_budget_m:
                omitted.append({"id": t.id, "reason": "상위 프로젝트 구현 예산 hours.budget 초과",
                                "projected_implementation_hours": as_hours(minutes_sum(new_tasks))})
            elif new_total > capacity:
                omitted.append({"id": t.id, "reason": "핵심 작업 보호 및 시간 상한 초과",
                                "projected_hours": as_hours(new_total)})
            else:
                required, selected, learn, total = candidate, new_tasks, new_learn, new_total
    else:
        omitted.extend({"id": t.id, "reason": "핵심 일정이 우선하여 확장 작업 배정 보류"}
                       for t in ordered if t.id not in required)

    included_ids = {t.id for t in selected}
    omitted = [o for o in omitted if o["id"] not in included_ids]
    for t in ordered:
        if t.id not in included_ids and t.id not in {o["id"] for o in omitted}:
            omitted.append({"id": t.id, "reason": "선택되지 않은 확장 작업"})
    upstream_checks = (raw.get("checks") or {}) if isinstance(raw.get("checks"), dict) else {}
    upstream_passed = upstream_checks.get("passed")
    if upstream_passed is False:
        notes.append("상위 프로젝트 checks.passed=false: 원본 산출물의 문제를 검토해야 합니다")
    elif upstream_passed is None:
        notes.append("상위 프로젝트 checks.passed 값이 제공되지 않았습니다")
    unverified = raw.get("unverified") or []
    if unverified:
        notes.append(f"상위 프로젝트에 사람이 확인할 항목 {len(unverified)}개가 있습니다")
    if learn["uncovered"]:
        notes.append("학습 경로를 확보하지 못한 항목: " + ", ".join(learn["uncovered"]))
    if learn["unknown_duration_candidates"] and learn["uncovered"]:
        notes.append("미해결 역량과 관련되지만 학습시간이 없는 참고 자료: " +
                     ", ".join(learn["unknown_duration_candidates"]))
    if learn["unknown_duration_selected"]:
        notes.append("학습시간이 없는 핵심 자료/선택 자료: " + ", ".join(learn["unknown_duration_selected"]))
    all_core_materials = {u.material_id for u in units if u.role == "core"}
    used_core_materials = {u.material_id for u in learn["units"] if u.role == "core"}
    unused_core_materials = sorted(all_core_materials - used_core_materials)
    if explicit:
        # A core course is legitimately unused when its topics are already known.
        unused_core_materials = [mid for mid in unused_core_materials if any(
            set(u.competencies) - set(known) for u in units if u.material_id == mid)
            and any(set(u.competencies).intersection(learn["uncovered"]) for u in units if u.material_id == mid)]
    if unused_core_materials:
        notes.append("핵심 교육자료가 프로젝트 작업 역량과 연결되지 않았습니다: " +
                     ", ".join(unused_core_materials))
    missing_evidence = [u.id for u in learn["units"] if not u.evidence or not u.url]
    if missing_evidence:
        notes.append("선택 교육자료의 URL 또는 연결 근거(evidence) 미제공: " + ", ".join(missing_evidence))
    added_claims = sum(len(t.added) for t in selected)
    if learn["selection_method"] == "budget_fallback":
        notes.append("시간 또는 선수조건을 충족하는 대체 학습 경로를 선택했습니다")
    if added_claims:
        notes.append(f"선택 작업의 added 항목 {added_claims}개는 검증된 근거로 간주하지 않습니다")
    if learn.get("gaps") and not has_blocking_gaps(learn):
        notes.append("LLM이 제안한 선수지식 중 연결 자료가 없는 항목을 미충족으로 남긴 검토용 초안입니다")
    for tid, errors in learn.get("gaps", {}).items():
        notes.append(f"{tid} 선수학습 확인 필요: " + "; ".join(errors))
    review = [f"{t.id} 작업 출처 또는 완료 기준 미제공" for t in selected if not any((isinstance(src, str) and src.strip()) or (isinstance(src, dict) and (src.get("url") or src.get("quote"))) for src in t.sources) or not t.completion_check]
    if analysis is None and any(t.id in included_ids and "depends_on" not in row for t, row in zip(tasks, raw["packages"])):
        review.append("선행 작업을 명시하지 않은 항목이 있어 입력 순서를 사용했습니다")
    if any(not t.competencies for t in selected):
        review.append("일부 작업의 목표 역량 ID가 누락됐습니다")
    if any(t.requires is None for t in selected):
        review.append("명시되지 않은 작업 선수지식은 연결 역량으로 추정했습니다")
    if any(isinstance(u.evidence, str) and u.evidence.strip() in {"근거 확인 필요", "미정", "TBD"} for u in learn["units"]):
        review.append("학습 근거에 미확정 표시가 있습니다")
    if analysis is not None:
        review.append("LLM 제안의 입력 인용 일치 여부를 검사했습니다. 제안의 의미와 교육 적합성은 검토가 필요합니다")
    notes.extend(review)
    plan_blocked = has_blocking_gaps(learn) or core_over_budget or core_project_budget_exceeded or bool(learn["unknown_duration_selected"])
    if core_project_budget_exceeded:
        notes.append(f"핵심 작업 구현시간 {as_hours(minutes_sum(selected))}h이 프로젝트 예산 {project_budget}h 초과")
    if core_over_budget:
        minimum_weekly_minutes = SLOT_MINUTES * ((total // SLOT_MINUTES + weeks - 1) // weeks)
        hours, minutes = divmod(minimum_weekly_minutes, 60)
        notes.append(f"핵심 작업과 시간이 확인된 학습자료에 {as_hours(total - capacity)}시간이 더 필요합니다. "
                     f"현재 확인된 시간 기준으로 주당 최소 {hours}시간 {minutes}분이 필요합니다.")
    if strict and (review or not upstream_passed or unverified or learn["uncovered"] or missing_evidence or added_claims or unused_core_materials):
        plan_blocked = True
        notes.append("엄격 모드: 상위 검증·미확인 항목·학습 커버리지 문제로 일정 생성을 보류합니다")

    after, supplements = {}, []
    if include_references:
        after, supplements = supplemental_plan(include_references, units, selected, learn, known,
                                               capacity - total, plan_blocked, strict)
    extra_units = [u for t in selected for u, _, _ in after.get(t.id, ())]
    extra_minutes = sum(u.minutes for u in extra_units)
    total += extra_minutes
    scheduled_units = learn["units"] + extra_units
    extra_missing_evidence = [u.id for u in extra_units if not u.url or not u.evidence or
                              u.evidence.strip() in {"근거 확인 필요", "미정", "TBD"}]
    if extra_missing_evidence:
        notes.append("보완학습의 근거 확인 필요: " + ", ".join(extra_missing_evidence))
    missing_evidence.extend(extra_missing_evidence)
    output_weeks = [] if plan_blocked else build_schedule(
        selected, learn["units"], weeks, per_week, total, learn.get("before"), after)
    included_skills = sorted(set(itertools.chain.from_iterable(t.competencies for t in selected)))
    covered_skills = sorted(set(included_skills).intersection(s for u in scheduled_units for s in u.competencies))
    missing_materials = sorted(set(included_skills) - set(covered_skills))
    duration_ok = not learn["unknown_duration_selected"] and not any("학습시간 미확정" in msg for errors in learn.get("gaps", {}).values() for msg in errors)
    ready = (not review and not plan_blocked and not learn["uncovered"] and upstream_passed is True and
             not unverified and not missing_evidence and not unused_core_materials and added_claims == 0 and
             all(t.competencies for t in selected))
    status = "blocked" if plan_blocked else ("ready" if ready else "needs_review")

    result = {
        "schema_version": "roundlab.curriculum.output.v1",
        "status": status,
        "project": {"title": raw["title"], "goal": raw.get("goal"), "base": raw.get("base"),
                    "complements": raw.get("complements", [])},
        "policy": {"source": "adapt.json packages[] + selected materials",
                   "order": "명시된 depends_on 우선, 그 외에는 입력 순서",
                   "learning": ("작업·구간별 선수지식에서 보유 개념을 제외하고 필요한 구간을 순서대로 배치" if explicit else "역량 ID 일치 기반 추정"),
                   "core": "핵심 작업과 선행 작업 보호, 나머지는 시간 범위에서 포함",
                   "references": ("선수조건을 충족할 수 있는 경로 중 핵심 자료 우선, 이후 경로 시간 우선" if explicit else "핵심 자료로 부족한 역량을 참고자료로 보완"),
                   "no_invention": "시간·역량·작업·근거는 입력에 없는 내용을 생성하지 않음",
                   "reference_selection": learn["selection_method"]},
        "inputs": {"packages_total": len(tasks), "materials_total": sum(counts.values()),
                   "core_materials": counts["core"], "reference_materials": counts["reference"]},
        "constraints": {"weeks": weeks, "hours_per_week": hours_per_week,
                        "capacity_hours": as_hours(capacity), "project_budget_hours": project_budget},
        "summary": {"included_packages": [t.id for t in selected],
                    "core_packages": [t.id for t in selected if t.core],
                    "promoted_dependencies": promoted,
                    "excluded_packages": omitted,
                    "selected_learning_units": [u.id for u in scheduled_units],
                    "selected_material_ids": list(dict.fromkeys(u.material_id for u in scheduled_units)),
                    "implementation_hours": as_hours(minutes_sum(selected)),
                    "learning_hours": as_hours(learn["education_minutes"] + extra_minutes),
                    "scheduled_hours": as_hours(total) if not plan_blocked else None,
                    "remaining_hours": as_hours(capacity - total) if not plan_blocked else None,
                    "uncovered_competencies": learn["uncovered"]},
        "learning_matches": [{"unit_id": u.id, "material_id": u.material_id, "role": u.role,
                              "title": u.title, "url": u.url, "section": u.section,
                              "competencies": list(u.competencies), "duration_minutes": u.minutes,
                              "evidence": u.evidence} for u in scheduled_units],
        "competency_coverage": {"target": included_skills, "covered_by_materials": covered_skills,
                                "missing_materials": missing_materials},
        "weeks": output_weeks, "learner_known": list(known),
        "prerequisite_gaps": learn.get("gaps", {}), "required_learning_topics": learn["needed"],
        "checks": {"scheduled": not plan_blocked, "core_not_dropped": all(t.id in included_ids for t in tasks if t.core),
                   "within_total_capacity": total <= capacity, "material_durations_known": duration_ok,
                   "educational_coverage_complete": not learn["uncovered"] and not missing_materials,
                   "educational_evidence_complete": not missing_evidence and not any("학습 근거에 미확정" in msg for msg in review),
                   "project_implementation_within_budget": (project_budget_m is None or
                                                            minutes_sum(selected) <= project_budget_m),
                   "added_claims_to_review": added_claims,
                   "unmatched_core_material_ids": unused_core_materials,
                   "upstream_project_passed": upstream_passed,
                   "all_week_caps_ok": all(w["used_minutes"] <= per_week for w in output_weeks) if output_weeks else None,
                   "unverified_count": len(unverified)},
        "warnings": list(dict.fromkeys(notes)),
        "upstream_review": {"unverified": unverified, "decisions": raw.get("decisions", []),
                            "checks": upstream_checks},
    }
    if supplements:
        result["supplemental_references"] = supplements
    result["task_preparation"] = [{
        "task_id": t.id, "required": list(t.requires if t.requires is not None else t.competencies),
        "already_known": sorted(set(known).intersection(t.requires if t.requires is not None else t.competencies)),
        "depends_on": list(t.depends_on), "completion_check": t.completion_check or None,
        "sources": list(t.sources), "study_before_task": learn.get("before", {}).get(t.id, []),
        "gaps": learn.get("gaps", {}).get(t.id, [])} for t in selected]
    if model and output_weeks:
        lesson_analysis.weekly_guides(output_weeks, model, profile, region)
    if analysis is not None:
        result["analysis_proposal"] = analysis
        result["analysis_provenance"] = analysis_provenance
    if core_over_budget:
        result["summary"]["core_shortfall_minutes"] = total - capacity
        result["summary"]["minimum_weekly_minutes"] = minimum_weekly_minutes
    return result


def display_minutes(minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours}시간 {remainder}분"
    return f"{hours}시간" if hours else f"{remainder}분"


def format_md(result: dict) -> str:
    project, sumry, constraints = result["project"], result["summary"], result["constraints"]
    analysis_provenance = result.get("analysis_provenance", {})
    team = result.get("team_export")
    size_label = f" | **규모:** {constraints['size']}" if "size" in constraints else ""
    all_gaps = result["prerequisite_gaps"]
    missing_suffix = ": 제공하는 자료가 없습니다"
    optional_topics = {}
    if team and analysis_provenance and result["weeks"]:
        optional_topics = {
            task_id: {gap.removesuffix(missing_suffix) for gap in errors if gap.endswith(missing_suffix)}
            for task_id, errors in all_gaps.items()
        }
    out = [f"# {project['title']} — 주차별 커리큘럼", "",
           f"**상태:** `{result['status']}` | **기간:** {constraints['weeks']}주 × {constraints['hours_per_week']}시간/주{size_label}", "",
           f"**목표:** {project.get('goal') or '목표 문단 미제공'}", "",
           "## 생성 흐름", "",
           result["policy"]["source"] + " → 작업·역량 확인 → 핵심/참고 교육자료 매칭 → 학습·작업 순서 정렬 → 주차 배분 → 검증", "",
           "## 배정 결과", "",
           f"- 포함 작업: {', '.join(sumry['included_packages']) or '없음'}",
           f"- 프로젝트 구현: {sumry['implementation_hours']}시간 / 학습: " + (f"{sumry['learning_hours']}시간" if result["checks"]["material_durations_known"] else "미정"),
           f"- 선택 교육자료: {', '.join(sumry['selected_material_ids']) or '없음'}",
           f"- 제외된 확장 작업: {', '.join(x['id'] for x in sumry['excluded_packages']) or '없음'}",
           ""]
    if result.get("team_export"):
        out.extend(["## 작업안과 시간 추정", "",
                    "CSV의 차용 역량과 자료 인용문을 바탕으로 만든 축소 실습안입니다. P번호는 생성기가 제안한 작업이며, 원본 W번호는 출처 참조로 보존했습니다.",
                    "구현 추정은 예제·설계 5시간, 기능 하나 구현 16시간, 재현 검증 7시간, 독립 확장 기능당 14시간입니다. 학습 추정은 관련 부분 한 번 읽기 60분, 튜토리얼 90분, 노트북 실습 120분, 워크숍 실습 180분입니다. 정확한 수강 구간과 시간은 확인이 필요합니다.",
                    "", "## 팀 추천 교육자료", ""])
        for item in result["team_export"]["recommended_materials"]:
            out.append(f"- {item['role']} · [{item['title']}]({item['url']}) · {item['covers']}")
        out.append("")
    if result.get("learner_known"):
        out.extend(["시작 전 보유 지식 · " + ", ".join(result["learner_known"]), ""])
    if result["status"] == "blocked":
        out.extend(["> 일정 생성이 보류되었습니다. 아래 경고와 입력을 수정한 뒤 다시 실행하세요.", ""])
    else:
        out.extend(["## 주차별 계획", ""])
        for w in result["weeks"]:
            duration = display_minutes(w["used_minutes"])
            out.extend([f"### {w['week']}주차 — {duration} (주당 상한 {constraints['hours_per_week']}시간)", ""])
            if w["activities"]:
                guide = w.get("guide", {})
                out.append("주간 목표 · " + (guide.get("goal") or " / ".join(w["goals"])))
                if guide:
                    out.extend(["LLM 생성 안내 · 원문 미확인",
                                "학습 방법 · " + guide["method"], "배정 이유 · " + guide["reason"]])
                ratio = w["recommended_learning_percent"]
                guideline = f" (권장 학습 비중 {ratio}%)" if ratio is not None else ""
                out.append(f"학습 {w['learning_minutes']}분 · 구현 {w['implementation_minutes']}분 · 실제 학습 비중 {w['actual_learning_percent']}%{guideline}")
            out.append("")
            if not w["activities"]:
                out.extend(["배정된 학습·작업 없음 (임의로 시간을 채우지 않음)", ""])
            for a in w["activities"]:
                if a["kind"] == "learning":
                    label = "보완학습" if a.get("learning_purpose") == "supplemental" else "학습"
                    out.append(f"- **{label}** ({display_minutes(a['minutes'])}): [{a['title']}]({a['url']}) — 역량 {', '.join(a['competencies']) or '미지정'}")
                    if a["section"]:
                        out.append("  - 학습 구간 · " + a["section"])
                    unit_proposal = analysis_provenance.get("units", {}).get(a["id"])
                    if unit_proposal:
                        out.append("  - LLM 생성 제안 · 원문 미확인 (학습 방법·선수지식)")
                        scope = unit_proposal.get("suggested_scope")
                        if scope:
                            out.append("  - 제안 학습 범위 · " + scope)
                    if a["requires"]:
                        out.append("  - 이 구간의 선수지식 · " + ", ".join(a["requires"]))
                    out.append(f"  - {a['reason']} · {a['study_method']} · 근거 {a['evidence'] or '미제공'}")
                else:
                    out.append(f"- **구현** ({display_minutes(a['minutes'])}): {a['id']} · {a['title']}" +
                               (f" → 산출물: {a['out']}" if a["completed_in_this_chunk"] else " (이어 진행)"))
                    if a["id"] in analysis_provenance.get("tasks", {}):
                        out.append("  - LLM 분석 반영 · 원문 미확인 (선수지식·선행 관계)")
                    out.append("  - 선행 작업 · " + (", ".join(a["depends_on"]) or "선행 작업 지정 없음"))
                    prerequisites = [topic for topic in a["prerequisites"]
                                     if topic not in optional_topics.get(a["id"], ())]
                    if prerequisites:
                        out.append("  - 필요한 선수지식 · " + ", ".join(prerequisites))
                    if a["completed_in_this_chunk"]:
                        out.append(f"  - 완료 기준 · {a['completion_check']}")
                    if a["sources"]:
                        for source in a["sources"]:
                            citation = (" · ".join(str(source[k]) for k in ("project", "url", "quote")
                                                   if source.get(k)) if isinstance(source, dict) else str(source))
                            if citation:
                                out.append("  - 작업 근거 · " + citation)
            out.append("")
    if result["learning_matches"]:
        out.extend(["## 교육자료 연결 근거", "",
                    "| 자료/구간 | 구분 | 역량 | 학습시간 | 원본 근거 |", "|---|---|---|---:|---|"])
        for a in result["learning_matches"]:
            title = a["title"].replace("|", "\\|")
            evidence = str(a["evidence"] or "입력 근거 없음").replace("|", "\\|").replace("\n", " ")
            out.append(f"| [{title}]({a['url']}) | {a['role']} | {', '.join(a['competencies'])} | "
                       f"{display_minutes(a['duration_minutes']) if a['duration_minutes'] is not None else '미확정'} | {evidence} |")
        out.append("")
    if result.get("supplemental_references"):
        out.extend(["## 요청한 보조자료", ""])
        for item in result["supplemental_references"]:
            duration = f" · {display_minutes(item['minutes'])}" if "minutes" in item else ""
            out.append(f"- {item['title']} ({item['material_id']}) · {item['reason']}{duration}")
        out.append("")
    if result["summary"]["excluded_packages"]:
        out.extend(["## 제외·보류 작업", ""])
        out.extend([f"- {a['id']}: {a['reason']}" for a in result["summary"]["excluded_packages"]])
        out.append("")
    gaps = {}
    references = {}
    for task_id, errors in all_gaps.items():
        for error in errors:
            topic = error.removesuffix(missing_suffix)
            if topic in optional_topics.get(task_id, ()):
                references.setdefault(topic, []).append(task_id)
            else:
                gaps.setdefault(task_id, []).append(error)
    internal_warnings = (
        "상위 프로젝트 checks.passed 값이 제공되지 않았습니다",
        "상위 프로젝트에 사람이 확인할 항목 ",
        "학습 경로를 확보하지 못한 항목: ",
        "LLM이 제안한 선수지식 중 연결 자료가 없는 항목을 미충족으로 남긴 검토용 초안입니다",
        "LLM 제안의 입력 인용 일치 여부를 검사했습니다.",
        *(f"{task_id} 선수학습 확인 필요: " for task_id in all_gaps),
    )
    notes = [line for line in result["warnings"] if not line.startswith(internal_warnings)]
    uncovered = [topic for topic in sumry["uncovered_competencies"] if topic not in references]
    if gaps or uncovered or notes:
        out.extend(["## 확인 및 경고", ""])
        if gaps or uncovered:
            out.extend(["> **주의 · 작업 전 선수학습을 확인하세요.**", ""])
            if not gaps:
                out.append("- 학습자료 연결이 필요한 역량 · " + ", ".join(uncovered))
            for task_id, errors in gaps.items():
                missing = []
                for error in errors:
                    topic, _, reason = error.partition(": ")
                    if reason == "제공하는 자료가 없습니다":
                        missing.append(topic)
                    else:
                        out.append(f"- **{task_id}** · {error}")
                if missing:
                    out.append(f"- **{task_id}** · 선수학습 자료 없음 ({', '.join(missing)})")
        out.extend(f"- {note}" for note in notes)
        out.append("")
    if references:
        names = {}
        for project_row in team["selected_projects"]:
            for entry in project_row["borrowed"].split(";"):
                code, _, name = entry.strip().partition(" ")
                if name:
                    names.setdefault(code, name.strip())
        out.extend(["## 추가 학습 참고", "",
                    "선정 교육자료에 연결되지 않은 주제입니다. 작업하면서 필요할 때 찾아보세요.", ""])
        for topic, task_ids in references.items():
            name = names.get(topic)
            label = f"{name} ({topic})" if name else topic
            keywords = f" · 검색어 `{name} 공식 문서 예제`" if name else ""
            out.append(f"- **{label}** · 관련 작업 {', '.join(task_ids)}{keywords}")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RoundLab: 응용 프로젝트 + 교육자료 → 근거가 남는 주차별 커리큘럼")
    p.add_argument("--team-folder", help="선정 프로젝트·교육자료 CSV 2개가 있는 폴더 (기본: data/aws_fde)")
    p.add_argument("--project", help="상위 단계의 *.adapt.json")
    p.add_argument("--materials", help="핵심·참고 교육자료 JSON")
    p.add_argument("--weeks", type=int, default=12, help="총 주차 수")
    capacity = p.add_mutually_exclusive_group(required=True)
    capacity.add_argument("--size", choices=SIZE_HOURS, help="주당 가용시간 · 소형 7시간, 중형 14시간, 대형 30시간")
    capacity.add_argument("--hours-per-week", type=float, help="주당 학습·구현 가용시간 (시간)")
    p.add_argument("--include-reference", action="append", default=[], metavar="ID",
                   help="남는 시간에 배정할 보조 교육자료 ID. 여러 번 지정 가능")
    p.add_argument("--output-dir", default="outputs", help="저장 폴더")
    p.add_argument("--strict", action="store_true", help="상위 검증/학습 근거 미충족 시 일정 생성 보류")
    reasoning = p.add_mutually_exclusive_group()
    reasoning.add_argument("--bedrock-model", help="Bedrock Converse 모델 ID. 작업·자료 내용을 전송해 선수학습 제안 생성")
    reasoning.add_argument("--analysis", help="저장된 동일 형식의 제안 JSON을 검증해 재사용")
    p.add_argument("--profile", help="Bedrock 호출에 사용할 AWS 프로필")
    p.add_argument("--region", help="Bedrock 호출 리전")
    a = p.parse_args(argv)
    try:
        hours = SIZE_HOURS[a.size] if a.size else a.hours_per_week
        if a.project or a.materials:
            if a.team_folder or not (a.project and a.materials):
                p.error("--project와 --materials를 함께 사용하거나 팀 폴더를 지정하세요")
            project, materials = read_json(a.project), read_json(a.materials)
            team = None
        else:
            from team_csv import prepare_team
            project, materials, team = prepare_team(a.team_folder or Path(__file__).parent / "data/aws_fde")
        result = generate(project, materials, weeks=a.weeks, hours_per_week=hours, strict=a.strict,
                          analysis=read_json(a.analysis) if a.analysis else None, model=a.bedrock_model,
                          profile=a.profile, region=a.region, include_references=a.include_reference)
        if a.size:
            result["constraints"]["size"] = a.size
        if team is not None:
            result["team_export"] = team
            result["policy"]["source"] = "선정 프로젝트 CSV + 선정 교육자료 CSV"
            result["policy"]["no_invention"] = "CSV 근거를 보존하며 작업·학습시간은 검토 필요 추정값으로 제안"
    except (InputError, ValueError, KeyError, OSError) as exc:
        print("입력 오류:", exc, file=sys.stderr)
        return 2
    output = Path(a.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "curriculum.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "curriculum.md").write_text(format_md(result), encoding="utf-8")
    print(f"결과: {result['status']} / {output / 'curriculum.json'} / {output / 'curriculum.md'}")
    return 0 if result["status"] == "ready" else 3  # intentional: output still written


if __name__ == "__main__":
    raise SystemExit(main())
