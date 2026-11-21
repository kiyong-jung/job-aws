"""Build a proposed curriculum from the two recommendation exports."""
import csv
import re
from pathlib import Path

PROJECTS = "프로젝트_뽑힌프로젝트.csv"
MATERIALS = "교육자료_고른자료.csv"


# Reading scopes verified against the linked materials supplied with this package.
SCOPES = {
    "https://github.com/crewAIInc/crewAI/blob/main/docs/edge/en/concepts/production-architecture.mdx": (
        "The Architecture → The Flow Class → Crews as Units of Work",
        "Flow가 상태를 받아 Crew에 넘기는 예제를 읽고, 프로젝트에서 호출 흐름과 도구의 책임을 한 장에 정리합니다.",
    ),
    "https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/UI-UX/recommended-technologies.md": (
        "TypeScript → Guidance on types and interfaces",
        "타입과 인터페이스 예제를 비교하고, 프로젝트의 입력·응답 구조를 TypeScript 타입으로 정의합니다.",
    ),
    "https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaluating_adk_agent.ipynb": (
        "Prepare Agent Evaluation dataset → Evaluate final response",
        "평가 입력과 응답 지표를 확인하고, 프로젝트 질문 한 건으로 같은 형식의 입력과 채점 기준을 만듭니다.",
    ),
}


def read_rows(folder, name, required):
    with (Path(folder) / name).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{name}: 열 누락 {sorted(missing)}")
        rows = []
        for row in reader:
            missing_cells = sorted(key for key in required if not (row.get(key) or "").strip())
            if missing_cells or None in row or any(value is None for value in row.values()):
                detail = ", ".join(missing_cells) or "헤더와 열 개수가 다릅니다"
                raise ValueError(f"{name} {reader.line_num}행: {detail}")
            rows.append(row)
    if not rows:
        raise ValueError(f"{name}: 데이터 행이 없습니다")
    return rows


def prepare_team(folder):
    projects = read_rows(folder, PROJECTS, {"title", "role", "borrowed", "packages", "url"})
    materials = read_rows(folder, MATERIALS, {"id", "role", "title", "covers", "quote", "url"})
    bases = [r for r in projects if r["role"] == "원본"]
    if len(bases) != 1:
        raise ValueError("원본 프로젝트 1개가 필요합니다")
    base = bases[0]
    units = []
    full, partial = set(), set()
    for row in materials:
        tags = {}
        for part in row["covers"].split(";"):
            match = re.fullmatch(r"\s*(C\d+)\s+(.+?)\s*:\s*(있음|일부)\s*", part)
            if not match:
                raise ValueError(f"{row['id']}: covers 형식을 확인하세요: {part}")
            cid, _, level = match.groups()
            tags[cid] = cid if level == "있음" else "입문-" + cid
            (full if level == "있음" else partial).add(cid)
        kind = row.get("type", "")
        minutes = 180 if "워크숍" in kind else 120 if "노트북" in kind else 90 if "튜토리얼" in kind else 60
        verified_section, method = SCOPES.get(row["url"], ("", ""))
        section = (row.get("section") or "").strip() or verified_section
        if not section:
            topic = (row.get("topic") or "").strip() or ", ".join(tags)
            section = f"CSV 인용문 기준 학습 범위 · {topic} (원문 절 미확인)"
        if not method:
            method = "표시된 범위에서 인용문과 관련된 내용을 찾고, 예제 한 건을 프로젝트에 적용할 방법을 기록합니다."
        units.append({**row, "section": section, "role": "core" if row["role"] == "핵심" else "reference",
                      "minutes": minutes, "teaches": list(tags.values()), "requires": [],
                      "evidence": row["quote"], "study_method": method})


    def terms(project):
        result = {}
        for term in project["borrowed"].split(";"):
            match = re.fullmatch(r"\s*(C\d+)\s+(.+?)\s*", term)
            if match:
                result[match[1]] = match[2]
        if not result:
            raise ValueError(f"{project['title']}: 차용 역량을 확인하세요")
        return result

    tasks = []
    def add(row, action, deliverable, check, hours, core, deps, target, learn):
        tid = f"P{len(tasks)+1:02}"
        catalog = terms(row)
        source = {"project": row["title"], "url": row["url"],
                  "quote": "; ".join(f"{k} {catalog[k]}" for k in target), "original_package_refs": row["packages"]}
        project_study = [f"{k} {catalog[k]}" for k in dict.fromkeys([*target, *learn]) if k not in full and k not in partial]
        required = [k if k in full else "입문-" + k for k in learn if k in full or k in partial]
        tasks.append(dict(id=tid, do=action, out=deliverable, completion_check=check, hours=hours,
                          core=core, depends_on=deps, competencies=target, requires=required,
                          sources=[source], project_study=project_study, added=[]))
        return tid

    skills = terms(base)
    def select(mapping, pattern):
        return [k for k, label in mapping.items() if re.search(pattern, label, re.I)]
    design = select(skills, "설계|개념")[:2] or list(skills)[:1]
    main = select(skills, "검색 파이프라인|RAG|에이전트 개발")[:3] or list(skills)[:2]
    intro = select(skills, "파운데이션 모델 개념|에이전트 툴링")[:2]
    setup = add(base, f"{base['title']} 예제를 실행하고 최소 기능의 입력·출력 정의",
                "예제 실행 기록과 기능 명세 1장", "같은 입력으로 예제를 재실행하고 예상 출력과 비교한다.",
                5, True, [], design, intro)
    prototype = add(base, f"{skills[main[0]]} 기능 하나를 샘플 입력으로 구현",
                    "실행 가능한 프로토타입과 입력 예제", "정상 입력 2건과 빈 입력 1건의 결과를 기록한다.",
                    16, True, [setup], main, intro + select(skills, "TypeScript")[:1])
    verified = add(base, "프로토타입의 성공·실패 사례를 재실행하고 사용법 작성",
                   "검증 스크립트, 결과표, 실행 안내서", "새 환경에서 안내서대로 실행하고 테스트 결과를 재현한다.",
                   7, True, [prototype], main, [])
    for row in projects:
        if row is base:
            continue
        options = terms(row)
        # Pick a reproducible small extension from the recorded borrowed capabilities.
        keys = select(options, "Eval 프레임워크|CI/CD|AWS 서비스")
        key = next(iter(keys or options))
        if "Eval" in options[key]:
            action, output, check = "프로토타입 평가 질문과 채점 코드 연결", "평가 질문 5개와 결과표", "두 실행의 점수를 비교하고 실패 사례를 설명한다."
        elif "CI/CD" in options[key]:
            action, output, check = "테스트 자동 실행과 실패 시 배포 중단 절차 구성", "CI 설정과 성공·실패 로그", "실패하는 테스트를 넣고 다음 단계가 중단되는지 확인한다."
        elif "AWS" in options[key]:
            action, output, check = "AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검", "인프라 템플릿과 설정 검증 기록", "템플릿 생성 성공과 필수 리소스의 존재를 확인한다."
        else:
            action, output, check = options[key] + "의 최소 예제를 연결", "실행 예제와 결과 기록", "예제 입력의 기대값과 실제 출력을 대조한다."
        add(row, action, output, check, 14, False, [verified], [key], [key])
    # The project source supplies the implementation walkthrough for skills absent from courses.
    for task in tasks:
        if task["project_study"]:
            topics = ", ".join(task["project_study"])
            task["do"] += f" (준비: 추천 교육자료에 없는 {topics} 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)"
    project = {"team_csv": True, "title": f"{base['title']} 기반 프로토타입 구현과 검증", "goal": "원본 프로젝트의 기능 한 가지를 구현하고 재현 가능한 검증 결과를 만든다.",
               "base": base, "complements": [r for r in projects if r is not base],
               "packages": tasks, "unverified": ["작업 분해·선수관계·시간은 생성기 제안이며 실측 전입니다."]}
    return project, {"materials": units}, {"input_files": [PROJECTS, MATERIALS], "selected_projects": projects,
            "recommended_materials": materials, "proposed_tasks": tasks,
            "learning_estimates": [{"id": u["id"], "minutes": u["minutes"], "type": u.get("type","")} for u in units]}
