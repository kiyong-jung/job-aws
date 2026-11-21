"""형식이 제각각인 공고를 [섹션] + 한 줄 한 항목으로 정리한다 (AI) + 정리 결과를 원문과 대조한다 (코드).

처리하는 특이 케이스 (prompts/format.txt)
- 영·한 이중 표기: 번역 짝이 있는 영어만 버림. 짝 없는 영어는 남김
- 탑다운: 업무 목록 앞의 목표·미션 한 줄은 [부서소개]로
- 질문 목록(보이저엑스형): [기술질문] 섹션
- 직무 여러 개: target_role 로 한 직무 + 공통만
- 이미지 공고: 이미지 파일을 그대로 보냄
코드가 못 하는 것: 접힌 내용(원티드 '더 보기', 노션 토글)은 펼쳐서 복사해야 한다.
"""
import os, re
from pathlib import Path

PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "format.txt").read_text(encoding="utf-8")


def _norm(t):
    return re.sub(r"\s+", "", t)


def _is_english(t):
    return bool(re.search(r"[A-Za-z]{4,}", t)) and not re.search(r"[가-힣]", t)


def format_posting(model_id, raw_text="", images=(), target_role=""):
    import boto3
    role_rule = f"8. 대상 직무: {target_role}" if target_role else ""
    prompt = PROMPT.format(role_rule=role_rule)
    if images:
        blocks = [{"image": {"format": Path(f).suffix[1:].lower().replace("jpg", "jpeg"),
                             "source": {"bytes": Path(f).read_bytes()}}} for f in images]
        blocks.append({"text": prompt + "\n(공고는 위 이미지에 있다. 이미지의 글자를 그대로 옮겨 정리하라.)"})
    else:
        blocks = [{"text": prompt + "\n[공고 원문]\n" + raw_text}]
    rt = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-2"))
    r = rt.converse(modelId=model_id, messages=[{"role": "user", "content": blocks}],
                    inferenceConfig={"maxTokens": 6000})
    return "".join(c.get("text", "") for c in r["output"]["message"]["content"]).strip()


def check(formatted, raw_text=""):
    """AI 정리 결과 점검. 사람이 볼 메시지 목록을 돌려준다."""
    msgs = []
    lines = [l.strip() for l in formatted.splitlines() if l.strip() and not l.strip().startswith("[")]
    secs = re.findall(r"^\s*\[([^\]]+)\]", formatted, flags=re.M)
    msgs.append(f"섹션: {secs}")
    if raw_text:
        src = _norm(raw_text)
        kept = sum(1 for l in lines if _norm(l.lstrip("-•·*▶■□○● "))[:25] in src)
        msgs.append(f"원문과 일치하는 줄 {kept}/{len(lines)} (낮으면 AI가 문장을 바꾼 것)")
        src_en = [l.strip().lstrip("-•·*▶■□○● ") for l in raw_text.splitlines()]
        src_en = [l for l in src_en if _is_english(l) and len(l) > 20]
        dropped = [l for l in src_en if _norm(l)[:25] not in _norm(formatted)]
        msgs.append(f"원문 영어 문장 {len(src_en)}개 중 뺀 것 {len(dropped)}개 → 번역 짝이 있는지 사람이 확인")
        msgs += [f"  - 뺌: {l[:90]}" for l in dropped[:15]]
    if not any(s in secs for s in ("자격요건", "기술질문")):
        msgs.append("⚠️ [자격요건]/[기술질문] 섹션 없음 → 접힌 내용이 빠졌는지 확인")
    return msgs
