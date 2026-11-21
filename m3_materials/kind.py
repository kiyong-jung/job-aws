"""링크 판별 규칙: 제목·주소·설명만 보고 교육용 / 참고용 / 제외 / 애매 를 가른다 (네트워크·LLM 없음).

  교육용  가르치려고 만든 자료 (강의, 튜토리얼, 가이드, 설명 글, 서베이)
  참고용  공부에 쓸 수는 있지만 가르치지는 않는 자료 (논문, 사례 블로그, 도구 저장소)
  제외    교육자료가 아닌 것 (제품 홈페이지, 홍보·뉴스, 행사, 리더보드, 목록 잔여물, 대상 밖 언어)
  애매    규칙으로 못 정한 것

규칙은 위에서부터 차례로 보고, 처음 걸린 규칙으로 정한다. collect_edu.py 가 목록 저장소의 링크에 쓴다.
"""
import re
from urllib.parse import urlparse

EDU = re.compile(
    r"tutorial|course|guide|how to|how-to|hands-on|step[- ]by[- ]step|walkthrough|cookbook|workshop|"
    r"lecture|from scratch|explained|introduction to|intro to|a gentle|primer|crash course|learn |"
    r"튜토리얼|강의|강좌|실습|가이드|입문|따라 ?하|만들어 ?보|구현해 ?보|알아보기|정리",
    re.I)
REPO_EDU = re.compile(r"tutorial|course|from scratch|educational|step[- ]by[- ]step|cookbook|lessons?|"
                      r"hands-on|learn(ing)? (to|how)|curriculum|튜토리얼|강의|실습", re.I)
SURVEY = re.compile(r"\b(survey|review|overview|tutorial|primer)\b", re.I)
NEWS = re.compile(
    r"\bannounc|\blaunch|\bexpands?\b|\bunveil|\bintroducing\b|\bpartner|\bnow available\b|"
    r"\bcustomers?\b|\bwelcome\b|\bacquir|\bfunding\b|\bjoins?\b|\buses? .{2,40} to\b|"
    r"\bawards?\b|\bfellows?(hip)?\b|open letter|\bcelebrat|year in review|\brecap\b|"
    r"출시|채용|해커톤|행사|컨퍼런스|밋업|수상|선정|인터뷰|MOU|협약", re.I)
EVENT = re.compile(r"sign up|register now|webinar|virtual event|📍", re.I)
BOARD = re.compile(r"leaderboard|arena\b|ranking of", re.I)
HAN = re.compile(r"[一-鿿]")
HANGUL = re.compile(r"[가-힣]")
LIST_JUNK = re.compile(r"contributing|license|code_of_conduct|readme\.md$", re.I)
SECTION_WORDS = {"pros", "cons", "overview", "location", "hitcount", "contents", "table of contents"}
CONTENT_HOSTS = ("github.com", "github.io", "arxiv.org", "huggingface.co", "youtube.com", "youtu.be",
                 "medium.com", ".edu", ".ac.kr", ".ac.uk", "readthedocs.io", "gitbook.io")


def is_root(url: str) -> bool:
    """제품·회사 홈페이지처럼 경로가 없는 주소인가."""
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.")
    return u.path.strip("/") == "" and not u.query and not any(host.endswith(h) for h in CONTENT_HOSTS)


def judge(m: dict) -> tuple[str, str]:
    t, title, url = m["type"], m["title"].strip(), m["url"]
    text = f'{title} {m["summary"]}'

    # 강의·학회 튜토리얼은 수집할 때 공식 페이지만 골랐으므로 먼저 교육용으로 둔다
    if t in ("대학 강의", "학회 튜토리얼"):
        return "교육용", t

    # 제외
    if len(title) < 3 or title.lower() in SECTION_WORDS or LIST_JUNK.search(url):
        return "제외", "목록 잔여물"
    if HAN.search(title) and not HANGUL.search(title):
        return "제외", "대상 밖 언어(중국어)"
    if EVENT.search(title) or (t == "글" and EVENT.search(m["summary"])):
        return "제외", "행사·등록"
    if BOARD.search(title):
        return "제외", "리더보드"
    if is_root(url):
        return "제외", "제품·회사 홈페이지"
    if t in ("기술 블로그", "글") and NEWS.search(title):
        return "제외", "홍보·뉴스"

    # 교육용
    if m["source"] == "interview-answers":
        return "교육용", "개념 설명 글(면접 답)"
    if t == "논문":
        return ("교육용", "서베이·튜토리얼 논문") if SURVEY.search(title) else ("참고용", "논문")
    if t == "저장소":
        if m["source"] == "llm-apps":
            return "참고용", "따라 만드는 템플릿(프로젝트 은행 쪽)"
        return ("교육용", "학습용 저장소") if REPO_EDU.search(text) else ("참고용", "도구 저장소")
    if EDU.search(text):
        return "교육용", "교육 키워드"

    # 참고용
    if t == "기술 블로그" or m["source"] == "applied-ml":
        return "참고용", "사례 블로그"
    return "애매", "신호 없음"
