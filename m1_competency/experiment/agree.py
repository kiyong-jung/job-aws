"""① 사람 둘이 따로 만든 정답의 일치도 (SkillSpan 방식: 독립 라벨 → 일치도 → 셋째가 정리).

1) 양식 만들기:   python agree.py template postings/naver_ml_intern.txt
   → annot/naver_ml_intern_A.csv, _B.csv  (두 사람이 각자 competencies 칸만 채움. 서로 보지 않기)
   competencies: 그 문장에서 뽑은 역량 이름을 ; 로 구분. 역량이 없는 문장은 비움
2) 일치도:        python agree.py compare annot/naver_ml_intern_A.csv annot/naver_ml_intern_B.csv
   → 문장 단위 κ(역량이 있는 문장인가), 역량 단위 엄격·관대 F1, 갈린 항목 목록 annot/*_diff.csv
   갈린 항목을 셋째가 정리해 gold/<공고>_gold.csv 를 다시 만든다.
"""
import sys
from pathlib import Path
import pandas as pd
from src.split import split_posting
from src.textmatch import norm, dice, cohen_kappa

RELAX = 0.5   # 관대 기준: 같은 문장 + 이름 글자 겹침(Dice) 0.5 이상


def items(df):
    out = []
    for r in df.itertuples():
        for n in str(r.competencies if pd.notna(r.competencies) else "").split(";"):
            if n.strip():
                out.append((r.id, n.strip()))
    return out


def prf(ref, sys_, strict):
    used, hit = set(), 0
    for sid, name in sys_:
        for j, (rid, rname) in enumerate(ref):
            if j in used or rid != sid:
                continue
            if (norm(name) == norm(rname)) if strict else (dice(name, rname) >= RELAX or norm(name) == norm(rname)):
                used.add(j); hit += 1; break
    p = hit / len(sys_) if sys_ else 0
    r = hit / len(ref) if ref else 0
    return p, r, (2 * p * r / (p + r) if p + r else 0)


if sys.argv[1] == "template":
    post = Path(sys.argv[2]); sent = split_posting(post.read_text(encoding="utf-8"))
    Path("annot").mkdir(exist_ok=True)
    for who in ("A", "B"):
        sent.assign(competencies="").to_csv(f"annot/{post.stem}_{who}.csv", index=False, encoding="utf-8-sig")
    print(f"annot/{post.stem}_A.csv, _B.csv 생성 · 문장 {len(sent)}개")
else:
    A, B = pd.read_csv(sys.argv[2]), pd.read_csv(sys.argv[3])
    has = lambda d: [int(pd.notna(x) and str(x).strip() != "") for x in d.competencies]
    print(f"문장 단위 κ (역량이 있는 문장인가): {cohen_kappa(has(A), has(B)):.2f}")
    ia, ib = items(A), items(B)
    for label, strict in (("엄격(이름 같음)", True), ("관대(같은 문장 + 겹침)", False)):
        p, r, f = prf(ia, ib, strict)
        print(f"역량 단위 {label}: A 기준 B의 P {p:.2f} R {r:.2f} F1 {f:.2f}")
    diff = A[["id", "section", "sentence"]].assign(A=A.competencies, B=B.competencies)
    diff = diff[diff.A.fillna("").map(norm) != diff.B.fillna("").map(norm)]
    out = Path(sys.argv[2]).with_name(Path(sys.argv[2]).stem.rsplit("_", 1)[0] + "_diff.csv")
    diff.assign(합의="").to_csv(out, index=False, encoding="utf-8-sig")
    print(f"갈린 문장 {len(diff)}개 → {out} (셋째가 '합의' 칸 정리)")
