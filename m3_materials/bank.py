"""교육자료 은행과 면접 질문 은행을 만들어 표(shared.schema 의 materials, questions)에 넣는다. 표는 data/banks/*.csv.

질문 은행 (둘 다 Apache-2.0, Outcome School. 질문 문장과 답 글 링크를 그대로 옮긴다):
  company : github.com/pallavi-shekhar/ai-engineering-interview-questions-company-wise  (회사 35곳, 주제별)
  topic   : github.com/amitshekhariitbhu/ai-engineering-interview-questions             (주제 14개)
교육자료 은행: 스타가 많은 공개 학습 자료 목록(awesome 목록 등, LISTS), 학회 튜토리얼, 대학 강의, 회사 기술 블로그, 질문 은행의 답 글 링크.
  본문은 옮기지 않고 제목, 주소, 한 줄 설명만 쓴다. 답 글은 그 글이 답하는 은행 질문을 설명 대신 쓴다.
  라이선스 파일이 없거나 비영리·카피레프트인 목록은 넣지 않는다.
목록 README 읽기(parse_list)는 프로젝트 은행(m2_project/bank.py)도 쓴다.
출처와 라이선스는 m3_materials/data/README.md.

  python -m m3_materials.bank blogs      # 회사 기술 블로그 글 목록 → m3_materials/data/blog_bank.jsonl (몇 분 걸린다)
  python -m m3_materials.bank build      # 질문 은행 → 교육자료 은행을 다시 만들어 표에 넣는다
  python -m m3_materials.bank materials  # 교육자료 은행만 다시 만든다
"""
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

from shared import config, schema, web

SOURCES = {"company": "pallavi-shekhar/ai-engineering-interview-questions-company-wise",
           "topic": "amitshekhariitbhu/ai-engineering-interview-questions"}
LISTS = {
    "llm-apps": ("Shubhamsaboo/awesome-llm-apps", "Apache-2.0", ()),
    "llm-course": ("mlabonne/llm-course", "Apache-2.0", ()),
    "applied-ml": ("eugeneyan/applied-ml", "MIT", ()),
    "awesome-llm": ("Hannibal046/Awesome-LLM", "CC0-1.0", ("LLM Leaderboard",)),
    "diffusion": ("diff-usion/Awesome-Diffusion-Models", "MIT", ()),
    "llm-resources": ("WangRongsheng/awesome-LLM-resources", "Apache-2.0", ()),
    "llm-strawberry": ("hijkzzz/Awesome-LLM-Strawberry", "Apache-2.0", ()),
    "llm-reasoning": ("atfortes/Awesome-LLM-Reasoning", "MIT", ()),
    "world-models": ("knightnemo/Awesome-World-Models", "BSD-3-Clause", ()),
    "ai-agents-2026": ("caramaschiHG/awesome-ai-agents-2026", "CC0-1.0", ()),
    "ai-agents-list": ("jim-schwoebel/awesome_ai_agents", "Apache-2.0", ()),
    "embodied": ("zchoi/Awesome-Embodied-Robotics-and-Agent", "Apache-2.0", ()),
    "rag": ("Danielskry/Awesome-RAG", "CC0-1.0", ()),
    "agent-papers": ("tmgthb/Autonomous-Agents", "MIT", ()),
    "game-ai": ("datamllab/awesome-game-ai", "MIT", ()),
    "tool-learning": ("thunlp/ToolLearningPapers", "Apache-2.0", ()),
}
_SKIP = ("Table of Content", "Contents", "News", "Citation", "Acknowledg", "Contribut", "Star History", "Overview",
         "Aim of the Project", "License", "Notebooks")
BLOG_BANK = config.MATERIALS_DATA / "blog_bank.jsonl"
COURSES = config.MATERIALS_DATA / "course_bank.json"
TUTORIALS = config.MATERIALS_DATA / "tutorial_bank.json"
# Upstage 는 robots.txt 가 수집을 막아 넣지 않는다
BLOGS = {
    "toss": ("Toss", "rss", "https://toss.tech/rss.xml", None),
    "naver-d2": ("NAVER", "rss", "https://d2.naver.com/d2.atom", None),
    "naver-cloud": ("NAVER Cloud", "rss", "https://medium.com/feed/naver-cloud-platform", None),
    "kakao": ("Kakao", "sitemap", "https://tech.kakao.com/sitemap.xml", r"tech\.kakao\.com/posts/\d+"),
    "line": ("LINE (LY)", "sitemap", "https://techblog.lycorp.co.jp/sitemap-index.xml",
             r"techblog\.lycorp\.co\.jp/ko/[^/]+/?$"),
    "woowahan": ("우아한형제들", "rss", "https://techblog.woowahan.com/feed/", None),
    "daangn": ("당근", "rss", "https://medium.com/feed/daangn", None),
    "coupang": ("Coupang", "rss", "https://medium.com/feed/coupang-engineering", None),
    "moloco": ("Moloco", "rss", "https://medium.com/feed/@moloco", None),
    "hyperconnect": ("Hyperconnect", "rss", "https://hyperconnect.github.io/feed.xml", None),
    "sk-devocean": ("SK DEVOCEAN", "rss", "https://devocean.sk.com/blog/rss.do", None),
    "lg-ai-research": ("LG AI Research", "sitemap", "https://www.lgresearch.ai/sitemap.xml",
                       r"lgresearch\.ai/blog/view\?seq=\d+"),
    "aws-ml": ("AWS", "wp", "https://aws.amazon.com/blogs/machine-learning/feed/", None),
    "aws-korea": ("AWS Korea", "wp", "https://aws.amazon.com/ko/blogs/tech/feed/", None),
    "microsoft-research": ("Microsoft Research", "wp", "https://www.microsoft.com/en-us/research/feed/", None),
    "google-research": ("Google Research", "sitemap", "https://research.google/sitemap.xml",
                        r"research\.google/blog/[^/]+/?$"),
    "meta-engineering": ("Meta", "rss", "https://engineering.fb.com/feed/", None),
    "nvidia": ("NVIDIA", "rss", "https://developer.nvidia.com/blog/feed", None),
    "huggingface": ("Hugging Face", "rss", "https://huggingface.co/blog/feed.xml", None),
    "openai": ("OpenAI", "rss", "https://openai.com/news/rss.xml", None),
    "netflix": ("Netflix", "rss", "https://netflixtechblog.com/feed", None),
    "pinterest": ("Pinterest", "rss", "https://medium.com/feed/pinterest-engineering", None),
}
_GENERIC = {"paper", "code", "article", "video", "project", "project page", "website", "blog", "github", "pdf", "arxiv",
            "demo", "slides", "dataset", "link", "homepage"}
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BADGE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\(([^)]+)\)")


def parse(markdown, source):
    """질문 README → questions 표의 줄 (원천 칸 빼고). 질문은 맨 앞 '- ' 줄, 바로 밑 '  - Asked at:' / '  - Answer:' 줄이 붙는다."""
    out, group, h3, h4, on = [], "", "", "", False
    for line in markdown.splitlines():
        if line.startswith("## "):
            group, h3, h4 = line[3:].strip(), "", ""
            on = on or group.startswith("Common Questions")
        elif line.startswith("### "):
            h3, h4 = line[4:].strip(), ""
            on = (on or h3 == "LLM Fundamentals") and h3 != "License"
        elif line.startswith("#### "):
            h4 = line[5:].strip()
        elif on and line.startswith("- "):
            company = h3 if source == "company" and not group.startswith("Common") else ""
            text = line[2:].strip()
            out.append({"id": schema.stable_id("Q", schema.norm(text)), "source": source, "text": text,
                        "topic": h4 or h3, "company": company, "asked_at": [], "answers": []})
        elif on and out and line.startswith("  - Asked at:"):
            out[-1]["asked_at"] = [t for t, _ in _LINK.findall(line)]
        elif on and out and line.startswith("  - Answer:"):
            out[-1]["answers"] = [{"title": t, "url": u} for t, u in _LINK.findall(line) if u.startswith("http")]
    return out


def kind_of(url):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "영상"
    if any(k in u for k in ("arxiv.org", "openreview.net", "aclanthology", ".pdf", "proceedings", "papers.nips")):
        return "논문"
    return "저장소" if "github.com" in u else "글"


def _plain(s):
    s = _BADGE.sub("", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[\s*\]\([^)]*\)", "", s)
    s = _LINK.sub(lambda m: m.group(1), s)
    return re.sub(r"\s+", " ", re.sub(r"[*_`|]|<br\s*/?>|\[⭐️\]", " ", s)).strip(" -:·,")


def _code(urls):
    """논문 줄에 함께 붙은 공식 코드 저장소 (주 주소가 논문이고 GitHub 링크가 따로 있을 때)."""
    return (next((u for u in urls[1:] if re.match(r"https?://github\.com/[^/]+/[^/#?]+", u)), None)
            if kind_of(urls[0]) == "논문" else None)


def parse_list(markdown, skip=(), repo=None):
    """학습 자료 목록 README → [{title, url, topic, text}].
    한 줄 항목: 목록 줄(-, *, 1.), 표 줄(|), 링크로 시작하는 줄. 굵은 글씨나 첫 링크가 제목, 배지 링크나 첫 링크의 주소가 주소다.
    두 줄 항목: 제목만 있는 줄(**제목**) 다음 세 줄 안에 링크가 나오면 그 링크를 주소로 붙인다 (논문 목록에 흔하다).
    목차, 소식, 인용 같은 절은 건너뛰고, 저장소 안을 가리키는 상대 주소는 repo 의 GitHub 주소로 바꾼다."""
    out, heads, pending = [], {}, None

    def links(s):
        us = _BADGE.findall(s) or [u for t, u in _LINK.findall(s) if not t.startswith("!")]
        return [u if u.startswith("http") else f"https://github.com/{repo}/tree/HEAD/{u.lstrip('./')}" for u in us
                if (u.startswith("http") or (repo and not u.startswith(("#", "mailto:"))))
                and "img.shields.io" not in u]
    for line in markdown.splitlines():
        m = re.match(r"^(#{2,4})\s+(.*)", line)
        if m:
            depth, pending = len(m.group(1)), None
            heads = {d: h for d, h in heads.items() if d < depth}
            heads[depth] = _plain(m.group(2))
            continue
        s = line.strip()
        if any(h.startswith(x) for h in heads.values() for x in _SKIP + tuple(skip)) or re.match(r"^\|[\s:|-]+\|?$", s):
            continue
        topic = " > ".join(heads[d] for d in sorted(heads))
        urls = links(s)
        if pending and urls:
            out.append({**pending, "url": urls[0], "code": _code(urls),
                        "text": (pending["text"] + " " + _plain(s))[:400].strip()})
            pending = None
            continue
        if pending:
            pending["left"] -= 1
            pending = pending if pending["left"] > 0 else None
        item = re.match(r"^(?:[-*]|\d+\.)\s+|^\||^\[|^\*\*", s)
        bold = re.search(r"\*\*([^*]{4,})\*\*", s)
        if not item:
            continue
        if not urls:
            if bold:
                pending = {"title": _plain(bold.group(1)), "topic": topic, "text": _plain(s.replace(bold.group(0), "")),
                           "left": 3}
            continue
        first = _LINK.search(_BADGE.sub("", s))
        title = _plain(bold.group(1) if bold else first.group(1) if first else "")
        if len(title) < 3 or title.strip("[]() ").lower() in _GENERIC:
            continue
        rest = _plain(s.replace(bold.group(0), "") if bold else _LINK.sub("", s, count=1))
        out.append({"title": title, "url": urls[0], "code": _code(urls), "topic": topic, "text": rest[:400]})
    for r in out:
        r.pop("left", None)
    return out


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def build():
    """질문 은행 → 교육자료 은행. 프로젝트 은행은 이 표의 논문 행을 읽으므로 그다음에 python -m m2_project.bank projects 로 다시 만든다."""
    rows = {}
    for source, repo in SOURCES.items():
        got = parse(web.readme(repo), source)
        for q in got:
            rows.setdefault(q["id"], {**q, "license": "Apache-2.0", "source_url": f"https://github.com/{repo}"})
        print(f"질문 {source}: {len(got)}문항")
    print(f"→ questions 표 {schema.write('questions', rows.values(), replace=True)}문항 (같은 문장 제거 후)")
    build_materials()



def parse_feed(xml_text):
    """RSS·Atom → [{title, url, text}]. 네임스페이스와 상관없이 item/entry 를 읽는다."""
    out = []
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:   # 본문에 XML 규칙을 어기는 글자가 섞인 피드는 항목만 정규식으로 읽는다
        for item in re.findall(r"<item>(.*?)</item>", xml_text, re.S):
            get = lambda tag: (re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", item, re.S)
                               or [None, ""])[1]
            if get("title") and get("link"):
                out.append({"title": web.strip_tags(get("title"), 300), "url": get("link").strip(),
                            "text": web.strip_tags(get("description") or get("content:encoded"))})
        return out
    for it in root.iter():
        if not it.tag.split("}")[-1] in ("item", "entry"):
            continue
        f = {c.tag.split("}")[-1]: c for c in it}
        link = f.get("link")
        url = ((link.text or "").strip() if link is not None and (link.text or "").strip()
               else (link.get("href") if link is not None else ""))
        desc = next((f[k].text for k in ("description", "summary", "encoded", "content") if k in f and f[k].text), "")
        if f.get("title") is not None and url:
            out.append({"title": web.strip_tags(f["title"].text, 300), "url": url, "text": web.strip_tags(desc)})
    return out


def _meta(url):
    page = web.fetch(url)
    pick = lambda key: (re.search(rf'<meta[^>]+(?:property|name)="{key}"[^>]+content="([^"]*)"', page) or [None, ""])[1]
    title = pick("og:title") or (re.search(r"<title>([^<]*)</title>", page) or [None, ""])[1]
    return {"title": web.strip_tags(title, 300), "url": url,
            "text": web.strip_tags(pick("og:description") or pick("description"))}


def _sitemap_urls(url, pattern):
    xml_text = web.fetch(url)
    locs = re.findall(r"<loc>([^<]+)</loc>", xml_text)
    if "<sitemapindex" in xml_text:
        return [u for child in locs for u in _sitemap_urls(child, pattern)]
    return [html.unescape(u) for u in locs if re.search(pattern, u)]


def build_blogs(*only, cap=150, pause=0.4):
    """회사 기술 블로그 글 목록 → m3_materials/data/blog_bank.jsonl. 사이트마다 최대 cap 개, 요청 사이에 pause 초 쉰다.
    블로그 이름을 주면 그 블로그만 다시 받아 파일 안의 그 블로그 줄만 바꾼다."""
    old = [json.loads(x) for x in BLOG_BANK.open(encoding="utf-8")] if only and BLOG_BANK.exists() else []
    rows = [r for r in old if r["blog"] not in only]
    for key, (company, how, url, pattern) in BLOGS.items():
        if only and key not in only:
            continue
        got = []
        try:
            if how == "rss":
                got = parse_feed(web.fetch(url))
            elif how == "wp":
                for page in range(1, 11):
                    part = parse_feed(web.fetch(f"{url}?paged={page}"))
                    if not part:
                        break
                    got += part
                    time.sleep(pause)
            else:
                for u in sorted(set(_sitemap_urls(url, pattern)),
                                key=lambda u: [int(x) for x in re.findall(r"\d+", u)] or [0], reverse=True)[:cap]:
                    try:
                        got.append(_meta(u))
                    except OSError:
                        pass
                    time.sleep(pause)
        except (OSError, ET.ParseError) as e:
            print(f"블로그 {key}: 실패 {type(e).__name__} {str(e)[:80]}")
        got = [g for g in got if g["title"]][:cap]
        rows += [{"company": company, "blog": key, **g} for g in got]
        print(f"블로그 {key}: {len(got)}개")
    write_jsonl(BLOG_BANK, rows)
    print(f"→ {BLOG_BANK.relative_to(config.ROOT)} {len(rows)}개")


def build_materials():
    """교육자료 은행 → materials 표. 같은 주소는 먼저 나온 하나만 둔다. 튜토리얼·강의는 목록 쪽 주소를 같이 쓰기도 해서 제목까지 본다."""
    rows = {}

    def add(r):
        r["id"] = schema.stable_id("M", r["url"], r["title"] if r["source"] in ("tutorial", "course") else "")
        return rows.setdefault(r["id"], r) is r
    arts = {}
    for q in schema.read("questions"):
        for a in q["answers"] or []:
            arts.setdefault(a["url"], {"title": a["title"], "questions": []})["questions"].append(q["text"])
    for url, a in sorted(arts.items()):
        add({"source": "interview-answers", "type": kind_of(url), "title": a["title"], "url": url, "topic": "면접 질문 답",
             "summary": " ".join(a["questions"]), "license": "Apache-2.0 (링크와 제목만)"})
    for c in json.loads(COURSES.read_text(encoding="utf-8"))["courses"] if COURSES.exists() else []:
        add({"source": "course", "type": "대학 강의", "title": f'{c["university"]} {c["code"]} {c["title"]}',
             "url": c["url"],
             "topic": ", ".join(c.get("topics", [])), "summary": c.get("summary"), "extra_url": c.get("videos"),
             "license": "각 강의 제공처"})
    for u in json.loads(TUTORIALS.read_text(encoding="utf-8"))["tutorials"] if TUTORIALS.exists() else []:
        add({"source": "tutorial", "type": "학회 튜토리얼", "title": f'[{u["conference"]} {u["year"]}] {u["title"]}',
             "url": u["url"],
             "topic": f'{u["conference"]} 튜토리얼', "summary": u.get("summary"), "extra_url": u.get("site"),
             "license": "각 학회·발표자"})
    for r in (json.loads(x) for x in BLOG_BANK.open(encoding="utf-8")) if BLOG_BANK.exists() else []:
        add({"source": f"blog:{r['blog']}", "type": "기술 블로그", "title": r["title"], "url": r["url"],
             "topic": r["company"], "summary": r["text"], "license": "각 블로그 저작권 (제목·주소·요약만)"})
    for name, (repo, lic, skip) in LISTS.items():
        got = parse_list(web.readme(repo), skip, repo)
        new = [add({"source": name, "type": kind_of(r["url"]), "title": r["title"], "url": r["url"],
                    "topic": r["topic"], "summary": r["text"],
                    "code_url": r["code"], "license": lic, "source_url": f"https://github.com/{repo}"}) for r in got]
        print(f"자료 {name}: 목록 {len(got)}개 → 새 자료 {sum(new)}개")
    print(f"→ materials 표 {schema.write('materials', rows.values(), replace=True)}개 (같은 주소 제거 후)")
    schema.index.cache_clear()


if __name__ == "__main__":
    {"build": build, "materials": build_materials,
     "blogs": build_blogs}[sys.argv[1] if len(sys.argv) > 1 else "build"](*sys.argv[2:])
