"""공고 텍스트를 문장 단위로 쪼개고 S01, S02 … 번호를 붙인다.

입력 형식: [섹션] 줄 아래에 문장들을 둔다.
    [담당업무]
    데이터 파이프라인을 구축합니다.
팀 공통 규칙: 모든 단계가 이 문장 번호를 근거로 단다.
"""
import re
import pandas as pd

LIST_MARK = re.compile(r"^(\d{1,2}[.)]\s+|[-•·*▶■□○●]\s*)")   # 목록 기호만 (10만 같은 숫자는 유지)


def split_posting(text: str) -> pd.DataFrame:
    rows, section = [], "기타"
    for raw in text.splitlines():
        line = LIST_MARK.sub("", raw.strip()).strip()
        if not line:
            continue
        m = re.fullmatch(r"\[\s*([^\]]{1,20})\s*\]", line)   # [섹션] 줄
        if m:
            section = m.group(1).strip()
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):        # 마침표 기준 문장 분리
            part = part.strip()
            if len(part) >= 2:
                rows.append({"section": section, "sentence": part})
    df = pd.DataFrame(rows, columns=["section", "sentence"])
    df.insert(0, "id", [f"S{i:02d}" for i in range(1, len(df) + 1)])
    return df


def numbered_text(sent: pd.DataFrame) -> str:
    """프롬프트에 넣을 형태: [S01](섹션) 문장"""
    return "\n".join(f"[{r.id}]({r.section}) {r.sentence}" for r in sent.itertuples())
