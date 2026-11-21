"""은행 다섯 개의 데이터 스키마와 표 저장소. 표 하나가 CSV 파일 하나다 (data/banks/{표}.csv).

  postings, posting_lines   공고 은행: 공고 본문과 정제한 줄 (필수·우대·배경, 중요도)
  resumes, resume_lines     이력서 은행: 이력서 본문과 면접관이 볼 줄
  questions                 면접 질문 은행
  materials                 교육자료 은행: 배우는 자료 (강의, 튜토리얼, 블로그 글, 논문, 저장소 소개)
  projects                  프로젝트 뱅크: 따라 구현하는 클론코딩 과제 (저장소, 앱, 논문 구현, 블로그 구현)

표마다 첫 칸 id 가 기본 키다. id 는 내용에서 만든다(주소나 문장의 해시). 원천 목록의 순서가 바뀌어도 같은 항목은 같은 id 다.
목록 칸(list)은 셀 안에 JSON 으로 둔다. 빈 셀은 값 없음이다. 엑셀에서 한글이 깨지지 않게 UTF-8 BOM 으로 쓴다.
search 표시한 칸을 이어 붙인 글(search_text)이 검색 대상이다. index(표).search(물음) 이 그 글을 낱말 검색(BM25, rank_bm25)으로 찾는다.
'가공 전에는 비움' 칸은 아직 채우지 않은 칸이다. 채우는 일은 TODO.md 에 있다.
칸 설명은 data/banks/_schema.csv 에도 같이 쓴다.

  python -m shared.schema          # 표마다 줄 수와 칸별로 채워진 비율
"""
import csv
import hashlib
import json
import re
from dataclasses import dataclass, field, fields
from functools import lru_cache
from typing import get_type_hints

from rank_bm25 import BM25Okapi

from . import config

DIR = config.BANKS


def col(desc, *, enum=None, required=False, search=False):
    return field(default=None, metadata={"desc": desc, "enum": enum, "required": required, "search": search})


def stable_id(prefix, *parts):
    return prefix + hashlib.sha1("\x1f".join(p or "" for p in parts).encode("utf-8")).hexdigest()[:10]


def norm(text):
    """같은 문장 판정용. 대소문자와 문장부호를 지운다."""
    return re.sub(r"\W+", " ", text.lower()).strip()


@dataclass
class Posting:
    id: str = col("공고 id. 스냅샷은 수집 때 붙인 id(J08, KK01), 붙여넣은 공고는 본문 해시(P…)", required=True)
    company: str = col("회사")
    title: str = col("공고 제목", required=True)
    url: str = col("공개 공고 주소")
    source: str = col("수집 경로 (Greenhouse 공개 API, 공식 채용 사이트, 붙여넣기)", required=True)
    updated: str = col("공고 갱신일")
    collected_at: str = col("수집 시각", required=True)
    text: str = col("공고 본문. 머리줄과 '- ' 목록 줄을 살린 평문", required=True)


@dataclass
class PostingLine:
    id: str = col("줄 id = 공고 id-순번", required=True)
    posting_id: str = col("postings.id", required=True)
    n: int = col("공고 안 순번", required=True)
    section: str = col("원래 구역", enum=["소개", "미션", "필수", "우대"], required=True)
    tier: str = col("정제 분류. 필수·우대 줄은 모두 질문이 되고 배경 줄은 맥락으로만 쓴다", enum=["필수", "우대", "배경"], required=True)
    importance: str = col("이 줄에서 나온 질문이 물려받는 중요도. 자격은 학위·실적·출장처럼 공부로 못 기르는 줄. 배경은 비움",
                          enum=["상", "중", "자격"])
    method: str = col("분류한 방법 (규칙: 머리줄, llm: 머리줄이 없어 Claude 가 가름, 사람: 손으로 고침)", enum=["규칙", "llm", "사람"], required=True)
    text: str = col("줄 글", required=True)


@dataclass
class Resume:
    id: str = col("이력서 id = 본문 해시(R…)", required=True)
    label: str = col("파일 이름이나 붙인 이름")
    source: str = col("어디서 왔나 (파일 경로, 붙여넣기)")
    created_at: str = col("넣은 시각", required=True)
    text: str = col("이력서 본문", required=True)


@dataclass
class ResumeLine:
    id: str = col("줄 id = 이력서 id-순번", required=True)
    resume_id: str = col("resumes.id", required=True)
    n: int = col("순번", required=True)
    text: str = col("줄 글. 머리 기호를 떼고 6자 미만 줄은 뺐다", required=True)


@dataclass
class Question:
    id: str = col("질문 id = 질문 문장(대소문자·문장부호 무시) 해시(Q…). 두 원천에 같은 문장은 하나만 둔다", required=True)
    text: str = col("질문 원문 (영어)", required=True, search=True)
    topic: str = col("원천의 주제 절", required=True, search=True)
    company: str = col("원천의 회사 절. 공통 질문은 비움")
    asked_at: list = col("질문했다고 적힌 회사들")
    answers: list = col("답 글 [{title, url}]. 본문은 옮기지 않는다")
    source: str = col("원천 (company: 회사별 은행, topic: 주제별 은행)", enum=["company", "topic"], required=True)
    source_url: str = col("원천 저장소 주소", required=True)
    license: str = col("원천 라이선스", required=True)
    intent: str = col("질문 의도. 답에 들어가야 할 요점의 틀을 정한다 (가공 전에는 비움)")
    concepts: list = col("질문이 묻는 개념 이름 (가공 전에는 비움)")


@dataclass
class Material:
    id: str = col("자료 id = 주소 해시(M…). 튜토리얼·강의는 목록 주소를 같이 쓰기도 해서 주소+제목 해시", required=True)
    type: str = col("자료 종류", enum=["대학 강의", "학회 튜토리얼", "기술 블로그", "논문", "저장소", "글", "영상"], required=True)
    source: str = col("원천 (awesome 목록 이름, blog:블로그, tutorial, course, interview-answers)", required=True)
    title: str = col("제목", required=True, search=True)
    url: str = col("주소", required=True)
    topic: str = col("원천의 주제 절, 학회, 회사", search=True)
    summary: str = col("원천이 준 설명. 본문은 옮기지 않는다. 질문 답 글은 그 글이 답하는 은행 질문들", search=True)
    code_url: str = col("논문의 공식 코드 저장소 (목록 줄에 함께 적힌 GitHub 링크)")
    extra_url: str = col("강의 영상 재생목록이나 튜토리얼 사이트")
    source_url: str = col("원천 목록 저장소 주소")
    license: str = col("원천 라이선스나 저작권 표시", required=True)
    minutes: int = col("공부 시간 어림, 분 (가공 전에는 비움)")
    concepts: list = col("가르치는 개념 이름 (가공 전에는 비움)")


@dataclass
class Project:
    id: str = col("프로젝트 id = 따라 만들 대상 주소 해시(PR…)", required=True)
    kind: str = col("종류", enum=["저장소", "앱 프로젝트", "논문 구현", "블로그 구현"], required=True)
    source: str = col("원천 (repo: 직접 고른 저장소, 앱 목록 이름, 논문이 나온 자료 목록 이름, blog:블로그)", required=True)
    title: str = col("제목", required=True, search=True)
    url: str = col("따라 만들 대상 (저장소, 앱 폴더, 논문의 공식 코드, 블로그 글)", required=True)
    paper_url: str = col("논문 구현의 논문 주소. 공식 코드 하나를 논문 여럿이 쓰면 먼저 나온 논문")
    stars: int = col("저장소 스타 수 (수집 때)")
    license: str = col("라이선스", required=True)
    topic: str = col("주제나 회사", search=True)
    summary: str = col("무엇을 만드는지 (설명, README 앞부분, 블로그 구현 과제)", search=True)
    concepts: list = col("구현하며 익히는 개념 이름 (가공 전에는 비움)")
    gpu: str = col("필요한 연산 자원 어림 (가공 전에는 비움)")
    hours: int = col("따라 만드는 데 드는 시간 어림 (가공 전에는 비움)")
    data: str = col("쓰는 데이터와 구하는 곳 (보강 행만, README 를 읽고 씀)")
    done: str = col("다 됐다고 볼 기준. README 에 없어 하는 일로 짐작한 것은 끝에 (어림) (보강 행만)")
    scale_note: str = col("크기·하드웨어·범위 메모. 보관된 저장소, README 의 시간 표현도 여기 (보강 행만)")
    checked: str = col("확인한 주소와 날짜 (보강 행만)")


TABLES = {"postings": Posting, "posting_lines": PostingLine, "resumes": Resume, "resume_lines": ResumeLine,
          "questions": Question, "materials": Material, "projects": Project}


@lru_cache(maxsize=None)
def columns(table):
    hints = get_type_hints(TABLES[table])
    return [(f.name, hints[f.name], f.metadata) for f in fields(TABLES[table])]


def search_text(table, row):
    return " ".join(row[c] or "" for c, _, m in columns(table) if m["search"])


def validate(table, row):
    """한 줄 → 문제 목록. 모르는 칸, 빈 필수 칸, 타입이 틀린 값, 정해진 값 밖의 값을 찾는다."""
    cols = {c: (t, m) for c, t, m in columns(table)}
    issues = [f"모르는 칸 {k}" for k in row if k not in cols]
    for c, (t, m) in cols.items():
        v = row.get(c)
        if v in (None, "", []):
            issues += [f"필수 칸 {c} 이 비었다"] if m["required"] else []
        elif not isinstance(v, t) or isinstance(v, bool):
            issues.append(f"{c} 는 {t.__name__} 이어야 한다 ({type(v).__name__})")
        elif m["enum"] and v not in m["enum"]:
            issues.append(f"{c} 값 {v!r} 은 {m['enum']} 밖이다")
    return issues


def _cell(v, t):
    return "" if v is None else json.dumps(v, ensure_ascii=False) if t is list else str(v)


def _value(s, t):
    return None if not s else json.loads(s) if t is list else int(s) if t is int else s


def read(table):
    """표 → dict 목록 (파일 순서). 스키마에 새로 생긴 칸은 None 으로 읽는다."""
    path = DIR / f"{table}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{c: _value(r.get(c), t) for c, t, _ in columns(table)} for r in csv.DictReader(f)]


def _save(path, header, rows):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    tmp.replace(path)


def write(table, rows, replace=False):
    """줄들을 검사하고 넣는다. 같은 id 는 그 자리에서 덮어쓰고 새 id 는 뒤에 붙인다. replace=True 면 표를 이 줄들로 바꾼다.
    스키마에 맞지 않는 줄이나 한 번에 같은 id 가 두 번 나오면 아무것도 쓰지 않고 멈춘다."""
    rows = list(rows)
    bad = [(r.get("id"), issues) for r in rows if (issues := validate(table, r))]
    if bad:
        raise ValueError(f"{table}: 스키마에 맞지 않는 줄 {len(bad)}개, 예: {bad[0]}")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError(f"{table}: 같은 id 가 두 번 나온다")
    merged = {r["id"]: r for r in ([] if replace else read(table))}
    merged.update((r["id"], r) for r in rows)
    cols = columns(table)
    _save(DIR / f"{table}.csv", [c for c, _, _ in cols],
          [[_cell(r.get(c), t) for c, t, _ in cols] for r in merged.values()])
    _save(DIR / "_schema.csv", ["table", "column", "type", "required", "search", "choices", "description"],
          [[name, c, t.__name__, "y" if m["required"] else "", "y" if m["search"] else "", " / ".join(m["enum"] or []),
            m["desc"]]
           for name in TABLES for c, t, m in columns(name)])
    return len(rows)


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:[.+#-][a-z0-9]+)*|[가-힣]+", text.lower())


class Index:
    """표 하나의 낱말 검색. search 는 표의 줄 dict 에 점수(score)를 붙여 돌려준다."""

    def __init__(self, table):
        self.docs = read(table)
        self.bm25 = BM25Okapi([tokens(search_text(table, d)) or ["_"] for d in self.docs])

    def search(self, query, k=8):
        scores = self.bm25.get_scores(tokens(query))
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [{**self.docs[i], "score": round(float(scores[i]), 2)} for i in top if scores[i] > 0]


@lru_cache(maxsize=None)
def index(table):
    """한 번 만들어 두고 다시 쓴다. 표를 다시 쓴 쪽이 index.cache_clear() 를 부른다."""
    return Index(table)


def report():
    """표마다 줄 수와 칸별로 채워진 비율. 아직 가공하지 않은 칸이 0% 로 보인다."""
    for name in TABLES:
        rows = read(name)
        filled = ", ".join(f"{c} {sum(r[c] not in (None, '', []) for r in rows) / len(rows):.0%}"
                           for c, _, _ in columns(name)[1:]) if rows else ""
        print(f"{name} {len(rows)}줄 · {filled}")


if __name__ == "__main__":
    report()
