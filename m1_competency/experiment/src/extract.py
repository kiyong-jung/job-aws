"""추출 방법별 프롬프트 만들기 + JSON 파싱.

방법(method)
- general : 우리 분류 기준으로 공고에서 바로 추출 (2차 회의 D 프롬프트)
- ncs     : general + NCS 능력단위 목록 중 가장 가까운 항목 매핑
- esco    : general + ESCO skill 목록 중 가장 가까운 항목 매핑
- via_q   : 공고 → 면접 질문 → 역량 (2단계 호출). 팀 문서의 '경로 비교' 실험용
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
STD_FILES = {"ncs": ("NCS 능력단위", "standards/ncs_units.csv"),
             "esco": ("ESCO skill", "standards/esco_skills.csv")}


def _read(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def load_standard(method: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / STD_FILES[method][1], comment="#")


def output_format(with_std: bool) -> str:
    extra = ',"standard_code":"코드","standard_name":"이름"' if with_std else ""
    return ("\n[출력 형식] 아래 JSON 배열만 출력한다. 설명, 마크다운, 코드블록 금지.\n"
            '[{"name":"역량명","type":"수행|지식|도구|협업·태도","priority":"필수|우대|구분없음",'
            '"basis":"명시|추론","evidence_id":"S05","reason":"추론일 때만, 명시면 빈 문자열"' + extra + "}]\n")


def competency_prompt(method: str, posting_numbered: str, questions_json: str = "") -> str:
    std = ""
    if method in STD_FILES:
        label = STD_FILES[method][0]
        items = "\n".join(f"{r.code} | {r.name}" for r in load_standard(method).itertuples())
        std = _read("standard_block.txt").format(label=label, items=items)
    body = "\n[채용공고 — 각 줄은 [문장ID](섹션) 문장]\n" + posting_numbered
    if method == "via_q":
        body += ("\n\n[면접 질문 — 이 질문들에 답하려면 필요한 역량을 뽑는다. "
                 "근거 문장ID는 질문의 evidence_id를 따른다]\n" + questions_json)
    return _read("rules.txt") + std + output_format(bool(std)) + body


def question_prompt(posting_numbered: str) -> str:
    return _read("questions.txt") + "\n[채용공고 — 각 줄은 [문장ID](섹션) 문장]\n" + posting_numbered


def parse_json_list(text: str):
    """```json 같은 코드블록 표시를 떼고 JSON 배열을 꺼낸다. (규칙 위반 여부도 반환)"""
    had_block = "```" in text
    t = re.sub(r"```(?:json)?", "", text).strip()
    s, e = t.find("["), t.rfind("]")
    if s == -1 or e == -1:
        raise ValueError("JSON 배열을 찾지 못함")
    return json.loads(t[s:e + 1]), had_block
