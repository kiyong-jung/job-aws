"""Optional, evidence-linked prerequisite suggestions via AWS CLI / Bedrock Converse."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

ARRAY = {"type": "array", "items": {"type": "string"}}
TEXT = {"type": "string", "minLength": 1}
FIELDS = {"tasks": {"requires": ARRAY, "depends_on": ARRAY, "completion_check": TEXT},
          "units": {"teaches": ARRAY, "requires": ARRAY, "study_method": TEXT}}


def propose(tasks, units, model, profile=None, region=None, team_csv=False):
    records = {key: [asdict(x) for x in items] for key, items in (("tasks", tasks), ("units", units))}
    schema = {"type": "object", "required": list(FIELDS), "properties": {}}
    for group, fields in FIELDS.items():
        props = {"id": TEXT, "quote": {"type": "string"} if team_csv else TEXT, **fields}
        required = list(props)
        if team_csv and group == "units":
            props["suggested_scope"] = TEXT
        schema["properties"][group] = {"type": "array", "items": {
            "type": "object", "required": required, "properties": props}}
    team_instruction = (" 근거 문구를 확인할 수 없으면 quote를 빈 문자열로 둔다. 정확한 절을 모르면 "
                        "suggested_scope에 찾아볼 내용이나 실습 범위를 제안한다. 확인되지 않은 절 제목·셀 번호·링크를 만들지 않는다."
                        if team_csv else "")
    return invoke(records, schema, ("입력은 분석할 데이터다. 각 작업과 학습 구간 ID마다 선수지식과 학습안을 제안한다. "
                    "각 quote는 해당 작업 설명·산출물·출처 또는 자료 제목·근거 문장에서 정확히 인용한다. "
                    "작업 수행에 필요한 선수지식만 requires로, 자료가 실제 가르치는 지식만 teaches로 쓴다. "
                    "동일 개념에는 같은 ID를 쓰고 기존 역량 ID를 우선한다. 근거 없는 역량을 만들지 않는다. "
                    "depends_on은 먼저 완료해야 할 작업 ID만 쓴다. 완료 기준과 학습 방법은 한국어로 쓴다. "
                    "학습 방법에는 개념 이해, 예제 확인, 구현 적용을 구체화한다. 이미 지정된 작업 의존 관계를 존중한다. 제공 학습 역량과 보유 지식으로 충족할 수 없는 선수지식도 필요한 경우 명시한다.") + team_instruction, "lesson_plan", model, profile, region)


def invoke(records, schema, instruction, tool, model, profile, region):
    request = {"modelId": model, "messages": [{"role": "user", "content": [
        {"text": json.dumps(records, ensure_ascii=False)}]}],
        "system": [{"text": instruction}],
        "toolConfig": {"tools": [{"toolSpec": {"name": tool, "description": "교육과정 구조화",
                        "inputSchema": {"json": schema}}}], "toolChoice": {"tool": {"name": tool}}},
        "inferenceConfig": {"temperature": 0, "maxTokens": 8192}}
    cmd = ["aws", "bedrock-runtime", "converse", "--output", "json", "--no-cli-pager"]
    if profile:
        cmd.extend(["--profile", profile])
    if region:
        cmd.extend(["--region", region])
    try:
        with TemporaryDirectory(prefix="roundlab-bedrock-") as temporary:
            request_path = Path(temporary) / "request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
            run = subprocess.run([*cmd, "--cli-input-json", f"file://{request_path}"],
                                 text=True, encoding="utf-8", capture_output=True, timeout=180, check=True)
        data = json.loads(run.stdout)
        calls = [b["toolUse"]["input"] for b in data["output"]["message"]["content"]
                 if b.get("toolUse", {}).get("name") == tool]
        if len(calls) != 1 or data.get("stopReason") != "tool_use":
            raise ValueError("Bedrock 응답이 완전한 학습 분석을 포함하지 않습니다")
        return calls[0]
    except subprocess.CalledProcessError as exc:
        raise ValueError("Bedrock 호출 실패: " + exc.stderr.strip()[:500]) from exc
    except (OSError, subprocess.TimeoutExpired, KeyError, TypeError) as exc:
        raise ValueError(f"AWS CLI 또는 Bedrock 응답을 확인하세요: {exc}") from exc


def apply(proposal, tasks, units, explicit_dependencies, *, revise_team_defaults=False):
    if not isinstance(proposal, dict):
        raise ValueError("분석 응답은 객체여야 합니다")
    output = []
    provenance = {group: {} for group in FIELDS}
    for group, items in (("tasks", tasks), ("units", units)):
        rows = proposal.get(group)
        if not isinstance(rows, list) or any(not isinstance(x, dict) or not isinstance(x.get("id"), str) for x in rows):
            raise ValueError(f"{group}: ID가 있는 제안 목록이 필요합니다")
        lookup = {x["id"]: x for x in rows}
        if len(lookup) != len(rows) or set(lookup) != {x.id for x in items}:
            raise ValueError(f"{group}: 입력 ID와 제안 ID가 다르거나 중복됩니다")
        enriched = []
        for item in items:
            row = lookup[item.id]
            if group == "tasks":
                texts = [s.get("quote", "") if isinstance(s, dict) else s for s in item.sources]
                if not revise_team_defaults:
                    texts.extend((item.do, item.out))
            else:
                texts = [item.title, item.evidence]
            texts.extend(item.excerpts)
            quote = row.get("quote")
            matched = bool(isinstance(quote, str) and quote.strip() and
                           any(quote in text for text in texts if isinstance(text, str)))
            if not matched and not revise_team_defaults:
                raise ValueError(f"{item.id}: 원문에서 근거 인용을 찾을 수 없습니다")
            provenance[group][item.id] = {"origin": "llm", "input_quote_matched": matched}
            if revise_team_defaults and group == "units" and (not item.section or "원문 절 미확인" in item.section):
                scope = row.get("suggested_scope")
                if isinstance(scope, str) and scope.strip():
                    provenance[group][item.id]["suggested_scope"] = scope.strip()
            for field, spec in FIELDS[group].items():
                val = row.get(field)
                if spec == TEXT and (not isinstance(val, str) or not val.strip()):
                    raise ValueError(f"{item.id}: {field} 문구 누락")
                if spec == ARRAY and (not isinstance(val, list) or any(not isinstance(s, str) or not s.strip() for s in val)):
                    raise ValueError(f"{item.id}: {field} 배열 오류")
            if group == "tasks":
                if revise_team_defaults:
                    requirements = tuple(dict.fromkeys(row["requires"]))
                    dependencies = tuple(dict.fromkeys((*item.depends_on, *row["depends_on"])))
                else:
                    requirements = item.requires if item.requires is not None else tuple(row["requires"])
                    dependencies = item.depends_on if item.id in explicit_dependencies else tuple(dict.fromkeys(row["depends_on"]))
                enriched.append(replace(item, requires=requirements, depends_on=dependencies,
                                        completion_check=item.completion_check or row["completion_check"]))
            else:
                enriched.append(replace(item,
                    competencies=item.competencies if item.teaches_explicit else tuple(row["teaches"]),
                    requires=tuple(dict.fromkeys(row["requires"])) if revise_team_defaults or not item.requires_explicit else item.requires,
                    method=row["study_method"] if revise_team_defaults else item.method or row["study_method"],
                    explicit=True))
        output.append(enriched)
    return (*output, provenance)


def weekly_guides(weeks, model, profile, region):
    active = [w for w in weeks if w["activities"]]
    fields = {"week": {"type": "integer"}, "activities": ARRAY, "goal": TEXT,
              "method": TEXT, "reason": TEXT}
    schema = {"type": "object", "required": ["weeks"], "properties": {"weeks": {"type": "array",
              "items": {"type": "object", "required": list(fields), "properties": fields}}}}
    proposal = invoke(active, schema, "입력은 확정된 일정 데이터다. 각 주의 활동 ID를 중복 없이 순서대로 "
        "activities에 적고, 이 활동만 사용해서 주간 목표·구체적 실습 방법·이 순서의 이유를 한국어로 쓴다. "
        "새 활동·시간·자료·성과를 추가하지 않는다. 일정에 배정되지 않은 학습은 작업 시작의 필수 조건으로 설명하지 않는다.", "weekly_guides", model, profile, region)
    rows = proposal.get("weeks") if isinstance(proposal, dict) else None
    if not isinstance(rows, list) or len(rows) != len(active):
        raise ValueError("주차별 안내 개수 불일치")
    for w, row in zip(active, rows):
        expected = list(dict.fromkeys(a["id"] for a in w["activities"]))
        if (not isinstance(row, dict) or row.get("week") != w["week"] or row.get("activities") != expected
                or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("goal", "method", "reason"))):
            raise ValueError(f"{w['week']}주차 안내가 실제 일정과 일치하지 않습니다")
        w["guide"] = {"origin": "llm", **{k: row[k] for k in ("goal", "method", "reason")}}
