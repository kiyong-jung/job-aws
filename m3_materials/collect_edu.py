"""교육자료 DB 수집: GitHub 공개 저장소에서 AI·Cloud 교육자료를 모아 m3_materials/data/edu_bank.csv 로 만든다.

출처는 두 종류다.
  강의 저장소  저장소 자체가 교재. 레슨 폴더의 README, 강의 챕터 파일, 실습 노트북 하나를 자료 한 건으로 뽑는다
  목록 저장소  강의·튜토리얼 링크 모음. README 의 [제목](주소) - 설명 줄을 절 제목과 함께 뽑는다

라이선스가 MIT, MIT-0, Apache-2.0, BSD, CC0, CC-BY-4.0 인 저장소만 쓴다 (SOURCES 의 license 칸).
교육용 자료만 저장한다. 강의 저장소의 레슨은 모두 교육용이고, 목록의 링크는 kind.judge 규칙으로 교육용만 남긴다
(도구 저장소, 제품 홈페이지, 제목만 있는 링크는 버린다).
본문은 저장하지 않고 제목, 주소, 요약(첫 문단 300자 이내)만 저장한다.

실행 (저장소 맨 위에서):
  python m3_materials/collect_edu.py --work /tmp/edu_src        # 저장소를 받아 두고 추출
  python m3_materials/collect_edu.py --work /tmp/edu_src --no-clone
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kind import judge  # noqa: E402  목록 링크 판별 규칙

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "진욱" / "data" / "edu_bank.csv"
NOTICE = ROOT / "진욱" / "data" / "edu_bank_NOTICE.md"

# repo, branch, domain, license, mode, type, sparse 경로
#   mode  lesson: 폴더 README 하나가 레슨 / file: md·mdx 파일 하나가 레슨 / nb: 노트북 하나가 레슨 / list: 링크 목록
C = "강의 레슨"
NB = "실습 노트북"
LAB = "워크숍 랩"
DOC = "공식 문서 튜토리얼"
SOURCES = [
    # AI 강의
    ("microsoft/generative-ai-for-beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/AI-For-Beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/ML-For-Beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/ai-agents-for-beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/mcp-for-beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/Data-Science-For-Beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/edgeai-for-beginners", "main", "ai", "MIT", "lesson", C, None),
    ("microsoft/Generative-AI-for-beginners-java", "main", "ai", "MIT", "lesson", C, None),
    ("huggingface/course", "main", "ai", "Apache-2.0", "file", C, ["/chapters/en/"]),  # LLM Course 본문
    ("huggingface/agents-course", "main", "ai", "Apache-2.0", "file", C, None),
    ("huggingface/mcp-course", "main", "ai", "Apache-2.0", "file", C, None),
    ("huggingface/smol-course", "main", "ai", "Apache-2.0", "file", C, None),
    ("huggingface/diffusion-models-class", "main", "ai", "Apache-2.0", "lesson", C, None),
    ("huggingface/deep-rl-class", "main", "ai", "Apache-2.0", "file", C, None),
    ("huggingface/audio-transformers-course", "main", "ai", "Apache-2.0", "file", C, None),
    ("huggingface/computer-vision-course", "main", "ai", "MIT", "file", C, None),
    ("karpathy/nn-zero-to-hero", "master", "ai", "MIT", "nb", C, None),
    ("rasbt/LLMs-from-scratch", "main", "ai", "Apache-2.0", "lesson", C, None),
    ("GokuMohandas/Made-With-ML", "main", "ai", "MIT", "nb", C, None),
    ("langchain-ai/langchain-academy", "main", "ai", "MIT", "nb", C, None),
    ("ray-project/ray-educational-materials", "main", "ai", "Apache-2.0", "nb", C, None),
    ("dair-ai/Prompt-Engineering-Guide", "main", "ai", "MIT", "file", DOC, ["/pages/"]),
    ("pytorch/tutorials", "main", "ai", "BSD-3-Clause", "gallery", DOC,
     ["/beginner_source/**/*.py", "/beginner_source/**/*.rst", "/intermediate_source/**/*.py",
      "/intermediate_source/**/*.rst", "/advanced_source/**/*.py", "/advanced_source/**/*.rst",
      "/recipes_source/**/*.py", "/recipes_source/**/*.rst"]),
    ("tensorflow/docs", "master", "ai", "Apache-2.0", "nb", DOC, ["/site/en/tutorials/**/*.ipynb", "/site/en/guide/**/*.ipynb"]),
    ("keras-team/keras-io", "master", "ai", "Apache-2.0", "gallery", NB, ["/examples/**/*.py"]),
    ("microsoft/PhiCookbook", "main", "ai", "MIT", "file", C, ["/md/**/*.md"]),
    # AI 실습
    ("huggingface/notebooks", "main", "ai", "Apache-2.0", "nb", NB, ["/examples/*.ipynb", "/peft/*.ipynb", "/diffusers/*.ipynb"]),
    ("mistralai/cookbook", "main", "ai", "MIT", "nb", NB, None),
    ("meta-llama/llama-cookbook", "main", "ai", "MIT", "nb", NB, ["*.ipynb", "README.md"]),
    ("huggingface/cookbook", "main", "ai", "Apache-2.0", "nb", NB, ["/notebooks/en/"]),
    ("openai/openai-cookbook", "main", "ai", "MIT", "nb", NB, ["/examples/"]),
    ("anthropics/anthropic-cookbook", "main", "ai", "MIT", "nb", NB, None),
    ("google-gemini/cookbook", "main", "ai", "Apache-2.0", "nb", NB, None),
    ("NVIDIA/GenerativeAIExamples", "main", "ai", "Apache-2.0", "nb", NB, None),
    ("pinecone-io/examples", "main", "ai", "MIT", "nb", NB, None),
    # Cloud × AI
    ("aws-samples/amazon-bedrock-workshop", "main", "cloud", "MIT-0", "nb", LAB, None),
    ("aws/amazon-sagemaker-examples", "main", "cloud", "Apache-2.0", "nb", NB, ["*.ipynb", "README.md"]),
    ("GoogleCloudPlatform/generative-ai", "main", "cloud", "Apache-2.0", "nb", NB, ["*.ipynb", "README.md"]),
    ("GoogleCloudPlatform/training-data-analyst", "master", "cloud", "Apache-2.0", "nb", NB, ["/courses/machine_learning/"]),
    ("GoogleCloudPlatform/mlops-on-gcp", "master", "cloud", "Apache-2.0", "nb", NB, None),
    # Cloud 기본
    ("MicrosoftLearning/mslearn-ai-studio", "main", "cloud", "MIT", "file", LAB, None),
    ("MicrosoftLearning/mslearn-ai-language", "main", "cloud", "MIT", "file", LAB, None),
    ("MicrosoftLearning/mslearn-ai-vision", "main", "cloud", "MIT", "file", LAB, None),
    ("MicrosoftLearning/AZ-104-MicrosoftAzureAdministrator", "master", "cloud", "MIT", "file", LAB, None),
    ("MicrosoftLearning/AZ-204-DevelopingSolutionsforMicrosoftAzure", "master", "cloud", "MIT", "file", LAB, None),
    ("aws-samples/eks-workshop-v2", "main", "cloud", "Apache-2.0", "file", LAB, ["/website/docs/"]),
    ("aws-samples/aws-serverless-workshops", "master", "cloud", "Apache-2.0", "lesson", LAB, None),
    ("aws-samples/aws-cdk-intro-workshop", "master", "cloud", "MIT-0", "file", LAB, None),
    ("kubernetes/website", "main", "cloud", "CC-BY-4.0", "file", DOC,
     ["/content/en/docs/tutorials/", "/content/en/docs/tasks/", "/content/en/docs/concepts/"]),
    ("docker/docs", "main", "cloud", "Apache-2.0", "file", DOC, ["/content/get-started/", "/content/guides/"]),
    # 목록
    ("dair-ai/ML-YouTube-Courses", "main", "ai", "CC0", "list", None, ["README.md"]),
    ("academic/awesome-datascience", "live", "ai", "MIT", "list", None, ["README.md"]),
    ("donnemartin/awesome-aws", "master", "cloud", "CC-BY-4.0", "list", None, ["README.md"]),
    ("milanm/DevOps-Roadmap", "master", "cloud", "Apache-2.0", "list", None, ["README.md"]),
    ("veggiemonk/awesome-docker", "master", "cloud", "Apache-2.0", "list", None, ["README.md"]),
    ("shuaibiyy/awesome-terraform", "master", "cloud", "CC0", "list", None, ["README.md"]),
]

SKIP_NAMES = {"contributing", "code_of_conduct", "security", "support", "changelog", "license", "agents",
              "comment", "translations", "pull_request_template", "issue_template", "governance", "maintainers",
              "authors", "notice", "quiz", "quizzes", "solution", "solutions", "assignment", "glossary",
              "troubleshooting", "_toctree", "toc", "readme-template", "discord101", "credits", "faq",
              "certification", "conclusion", "communication", "setup", "installation", "contributors"}
SKIP_DIRS = re.compile(r"(^|/)(solutions?|quiz-app|quiz|translations?|translated_images|i18n|images?|assets?|"
                       r"etc|sketchnotes|\.github|node_modules|tests?|data|docs/_|archive|deprecated|legacy)(/|$)",
                       re.I)
COURSE_LISTS = {"dair-ai/ML-YouTube-Courses"}   # 링크가 전부 강의인 목록
FIELDS = ["id", "domain", "type", "title", "url", "site_url", "course", "course_url", "topic", "summary",
          "source", "license", "minutes", "level", "covers"]


# ---------- 받기 ----------

def clone(repo, branch, paths, work: Path):
    d = work / repo.replace("/", "__")
    if (d / ".git").exists():
        return d
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", "-b", branch,
                    f"https://github.com/{repo}", str(d)], check=True, timeout=900)
    pats = paths or ["*.md", "*.mdx", "*.ipynb"]
    pats += ["!**/translations/**", "!**/translated_images/**", "!**/i18n/**", "!**/node_modules/**"]
    subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", "--no-cone", *pats], check=True, timeout=900)
    return d


# ---------- 글 다듬기 ----------

def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)              # 이미지
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)           # 링크 → 글
    s = re.sub(r"<[^>]+>", " ", s)                            # html
    s = re.sub(r"\{[^{}]*\}", " ", s)                          # mdx 표현식
    s = re.sub(r"[*_`#>|]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


JUNK = re.compile(r"^\.\. |^\*\*Author|CI test result|Open in Colab|Run in Google Colab|View on GitHub|^import |nbsp|Join .*Discord|"
                  r"Given the dynamic nature|View on TensorFlow|View source on GitHub|Kernel Python|opening this Notebook on colab|"
                  r"^Introduction General Setup|import from|grid-item|Copyright|Licensed under|This notebook's CI|Author:|Date created", re.I)


def split_front(text):
    """--- yaml --- 또는 +++ toml +++ 머리말을 떼어 낸다. 'key: >-' 처럼 다음 줄로 이어지는 값도 읽는다."""
    m = re.match(r"^(---|\+\+\+)\s*\n(.*?)\n\1\s*\n", text, re.S)
    if not m:
        return {}, text
    front, key = {}, None
    for line in m.group(2).splitlines():
        kv = re.match(r"^([A-Za-z_]+)\s*[:=]\s*(.*)$", line)
        if kv:
            key, v = kv.group(1).lower(), kv.group(2).strip().strip("'\"")
            front[key] = "" if v in (">-", ">", "|", "|-") else v
        elif key and line.startswith((" ", "\t")):
            front[key] = (front[key] + " " + line.strip()).strip()
    return front, text[m.end():]


def title_and_summary(text):
    """첫 제목과 그 뒤 첫 설명 문단(300자 이내)."""
    front, body = split_front(text)
    title = front.get("title") or front.get("linktitle") or ""
    summary = front.get("description") or front.get("summary") or ""
    hdr = dict(re.findall(r"^(Title|Description):\s*(.+)$", body[:1500], re.M))   # keras.io 예제 머리
    title = title or hdr.get("Title", "")
    summary = summary or hdr.get("Description", "")
    paras = re.split(r"\n\s*\n", body)
    for p in paras:
        p = p.strip()
        if not p or p.startswith("```") or JUNK.search(p[:200]) or JUNK.search(clean(p)[:200]):
            continue
        rst = re.match(r"^(.+)\n([=\-~*^#])\2{3,}\s*$", p, re.M)            # rst 제목 (pytorch)
        if rst and not title:
            title = clean(rst.group(1))
            continue
        h = re.match(r"^#{1,3}\s+(.+)", p)
        if h and not title:
            title = clean(h.group(1).splitlines()[0])
            rest = p[h.end():].strip()
            if rest and not summary:
                p = rest
            else:
                continue
        if not summary and not p.startswith(("#", "|", "<img", "![", "[![")):
            c = clean(p)
            if len(c) >= 60:
                summary = c
        if title and summary:
            break
    title = re.sub(r"\[\[[^\]]*\]\]", "", clean(title)).strip()
    return title, summary[:300]


def gallery_text(path: Path):
    """sphinx-gallery .py 의 맨 앞 docstring, 또는 .rst 본문."""
    t = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".rst":
        return t
    for q in ('"""', "'''"):                                  # 첫 docstring (정규식 대신 위치로 찾는다)
        i = t.find(q, 0, 3000)
        if i >= 0:
            j = t.find(q, i + 3)
            return t[i + 3:j] if j > 0 else ""
    return ""


def notebook_text(path: Path):
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    cells = nb.get("cells") or (nb.get("worksheets") or [{}])[0].get("cells", [])
    md = ["".join(c.get("source", "")) for c in cells if c.get("cell_type") == "markdown"]
    return "\n\n".join(md[:6])


# ---------- 주소 ----------

def site_url(repo, rel: str):
    """공식 사이트 주소로 바꿀 수 있으면 바꾼다."""
    p = re.sub(r"(/?(index|_index|README))?\.(md|mdx)$", "", rel)
    if repo == "kubernetes/website" and p.startswith("content/en/"):
        return "https://kubernetes.io/" + p[len("content/en/"):] + "/"
    if repo == "docker/docs" and p.startswith("content/"):
        return "https://docs.docker.com/" + p[len("content/"):] + "/"
    if repo.startswith("huggingface/") and repo != "huggingface/cookbook":
        m = re.match(r"(chapters|units)/en/(.+)", p)
        if m:
            slug = {"course": "llm-course"}.get(repo.split("/")[1], repo.split("/")[1])
            return f"https://huggingface.co/learn/{slug}/{m.group(2)}"
    if repo == "huggingface/cookbook" and rel.startswith("notebooks/en/"):
        return "https://huggingface.co/learn/cookbook/" + Path(rel).stem
    if repo == "pytorch/tutorials":
        m = re.match(r"(beginner|intermediate|advanced|recipes)_source/(.+)\.(py|rst)$", rel)
        if m:
            return f"https://pytorch.org/tutorials/{m.group(1)}/{m.group(2)}.html"
    if repo == "tensorflow/docs" and rel.startswith("site/en/"):
        return "https://www.tensorflow.org/" + re.sub(r"\.ipynb$", "", rel[len("site/en/"):])
    if repo == "keras-team/keras-io":
        m = re.match(r"examples/([^/]+)/([^/]+)\.py$", rel)
        if m:
            return f"https://keras.io/examples/{m.group(1)}/{m.group(2)}/"
    if repo == "dair-ai/Prompt-Engineering-Guide" and p.startswith("pages/"):
        return "https://www.promptingguide.ai/" + re.sub(r"\.en$", "", p[len("pages/"):])
    return ""


def eid(url):
    return "E" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def humanize(s):
    return re.sub(r"^[\d._-]+", "", s).replace("-", " ").replace("_", " ").strip() or s


# ---------- 강의 저장소 ----------

def lessons(src, d: Path):
    repo, branch, domain, lic, mode, typ, _ = src
    base = f"https://github.com/{repo}"
    root_t, root_s = ("", "")
    if (d / "README.md").exists():
        root_t, root_s = title_and_summary((d / "README.md").read_text(encoding="utf-8", errors="replace"))
    course = root_t or repo.split("/")[1]
    rows = [{"id": eid(base), "domain": domain, "type": "강의 코스" if typ == C else "실습 모음",
             "title": course, "url": base, "course": "", "course_url": "",
             "topic": "", "summary": root_s, "source": repo, "license": lic}]

    exts = (".py", ".rst") if mode == "gallery" else (".md", ".mdx", ".ipynb")
    files = sorted(f for f in d.rglob("*") if f.is_file() and f.suffix in exts and ".git" not in f.parts)
    for f in files:
        rel = f.relative_to(d).as_posix()
        stem = f.stem.lower().replace(".en", "")
        if rel in ("README.md",) or stem in SKIP_NAMES or SKIP_DIRS.search(str(Path(rel).parent)) \
                or "template" in rel.lower() or stem in ("index", "__init__", "conf") and mode == "gallery":
            continue
        if re.search(r"\.(ja|zh|es|fr|de|pt|it|ru|tr|vi|id|ar|hi)\.(md|mdx)$|(^|/)(japanese|chinese|spanish|"
                     r"french|portuguese|german)/", rel):
            continue                                         # 번역본
        if mode == "lesson" and not (stem in ("readme", "index") and f.suffix == ".md"):
            continue
        if mode == "nb" and f.suffix != ".ipynb" and stem != "readme":
            continue
        if mode == "nb" and stem == "readme" and any(f.parent.glob("*.ipynb")):
            continue                                         # 노트북이 있으면 노트북이 레슨
        if mode == "file" and f.suffix == ".ipynb":
            continue
        text = (notebook_text(f) if f.suffix == ".ipynb" else gallery_text(f) if mode == "gallery"
                else f.read_text(encoding="utf-8", errors="replace"))
        if (len(text) < 300 and f.suffix not in (".ipynb", ".py")) or (f.suffix == ".ipynb" and f.stat().st_size < 2000):
            continue                                         # 내용이 거의 없는 파일
        title, summary = title_and_summary(text)
        if not title or len(title) < 3:
            title = humanize(f.parent.name if stem in ("readme", "index") else f.stem)
        url = f"{base}/tree/{branch}/{Path(rel).parent.as_posix()}" if stem == "readme" \
            else f"{base}/blob/{branch}/{rel}"
        rows.append({"id": eid(url), "domain": domain, "type": typ, "title": title[:200],
                     "url": url, "site_url": site_url(repo, rel), "course": course, "course_url": base,
                     "topic": humanize(Path(rel).parent.name) if Path(rel).parent.name else "",
                     "summary": summary, "source": repo, "license": lic})
    # 같은 저장소 안에서 겹치는 제목(Introduction, Overview, 같은 README 제목 등)은 폴더 이름을 붙여 구분한다
    seen = Counter(r["title"].lower() for r in rows[1:])
    for r in rows[1:]:
        if (seen[r["title"].lower()] > 1 or r["title"].lower() == course.lower()) and r["topic"]:
            r["title"] = f'{r["topic"]}: {r["title"]}'[:200]
    return rows


# ---------- 목록 저장소 ----------

LINK = re.compile(r"^\s*(?:[-*+]|🔗|\|)\s*(?:\*\*)?\[([^\]]+)\]\((https?://[^)\s]+)\)(?:\*\*)?\s*(?:[-–—:|]\s*)?(.*)$")
GENERIC = re.compile(r"^(link( to .*)?|lectures?|course|website|videos?|slides|playlist|"
                     r"tutorials?/recitations|course page|notes)$", re.I)
NOT_ITEM = re.compile(r"shields\.io|badge|img\.shields|/sponsors|twitter\.com|x\.com/|linkedin\.com|"
                      r"discord|slack\.com|#|mailto:|/(LICENSE|CONTRIBUTING)", re.I)


def host_type(url, title):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "영상"
    if re.search(r"coursera\.org|edx\.org|udacity\.com|udemy\.com|\.edu/|course|class|lecture|bootcamp|"
                 r"skillbuilder|learn\.microsoft|cloudskillsboost|kaggle\.com/learn|fast\.ai", u + " " + title.lower()):
        return "온라인 강의"
    if "arxiv.org" in u:
        return "논문"
    if "github.com" in u:
        return "저장소"
    if re.search(r"blog|medium\.com|engineering\.|tech\.", u):
        return "기술 블로그"
    return "글"


def links(src, d: Path):
    repo, branch, domain, lic, *_ = src
    text = (d / "README.md").read_text(encoding="utf-8", errors="replace")
    section, para, rows = "", "", []
    for line in text.splitlines():
        h = re.match(r"^#{1,4}\s+(.+)", line)
        if h:
            section, para = clean(h.group(1)), ""
            continue
        m = LINK.match(line)
        if not m:
            if len(line.strip()) > 60 and not line.lstrip().startswith(("-", "|", "<", "!")):
                para = para or clean(line)                   # 절 첫 설명 문단 (강의 목록용)
            continue
        if NOT_ITEM.search(m.group(2)) or f"github.com/{repo}" in m.group(2):
            continue
        title, url, desc = clean(m.group(1)), m.group(2).rstrip("/"), clean(m.group(3).rstrip("| \\"))[:300]
        if GENERIC.match(title):                              # "Link to Course" → 절 제목을 자료 이름으로
            title = section if title.lower().startswith(("link", "course")) else f"{section} ({title})"
            desc = desc or para[:300]
        typ = host_type(url, title)
        legacy = {"온라인 강의": "대학 강의"}.get(typ, typ)   # kind.judge 는 기용 유형 이름을 쓴다
        kind, reason = judge({"type": legacy, "title": title, "url": url, "summary": desc, "source": repo})
        if typ == "온라인 강의" or repo in COURSE_LISTS:
            kind = "교육용"
        if kind != "교육용":
            continue
        rows.append({"id": eid(url), "domain": domain, "type": typ, "title": title[:200],
                     "url": url, "topic": section, "summary": desc, "source": repo, "license": lic})
    return rows


# ---------- 실행 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/tmp/edu_src", help="저장소를 받아 둘 폴더 (git 에 올리지 않음)")
    ap.add_argument("--no-clone", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)

    rows, per_src = {}, Counter()
    for src in SOURCES:
        repo = src[0]
        d = work / repo.replace("/", "__")
        try:
            if not a.no_clone:
                clone(repo, src[1], list(src[6]) if src[6] else None, work)
            if not d.exists():
                print(f"건너뜀 (없음): {repo}")
                continue
            got = links(src, d) if src[4] == "list" else lessons(src, d)
        except Exception as e:  # 한 저장소가 실패해도 나머지는 계속
            print(f"실패: {repo}: {e}")
            continue
        for r in got:
            key = r["url"].lower().rstrip("/")
            if key not in rows:
                rows[key] = {k: r.get(k, "") for k in FIELDS}
                per_src[repo] += 1

    out = list(rows.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    by = Counter(r["domain"] for r in out)
    print(f"교육자료 {len(out)}건 → {OUT.relative_to(ROOT)}  (ai {by['ai']}, cloud {by['cloud']})")
    print("  유형별", Counter(r["type"] for r in out).most_common())

    lines = ["# 교육자료 DB 출처 (m3_materials/data/edu_bank.csv)", "",
             "`python m3_materials/collect_edu.py` 가 아래 GitHub 공개 저장소에서 모은다. 제목, 주소, 첫 문단 요약(300자 이내)만 "
             "저장하고 본문은 옮기지 않는다. 교육용 자료만 남긴다(목록 저장소의 도구·제품·제목만 있는 링크는 버린다). "
             "라이선스 파일이 없거나 비영리(NC)·동일조건(SA)·자체 약관인 저장소는 넣지 않았다.", "",
             "| 저장소 | 분야 | 방식 | 라이선스 | 자료 수 |", "| --- | --- | --- | --- | --- |"]
    for repo, _, dom, lic, mode, *_ in SOURCES:
        lines.append(f"| [{repo}](https://github.com/{repo}) | {dom} | {mode} | {lic} | {per_src[repo]} |")
    lines += ["", "넣지 않은 저장소: DataTalksClub zoomcamp 4종, Developer-Y/cs-video-courses, kelvins·visenger awesome-mlops "
              "(라이선스 파일 없음), anthropics/courses·ramitsurana/awesome-kubernetes (CC BY-NC), d2l-ai/d2l-en (CC BY-SA), "
              "NirDiamant 3종 (자체 약관), bregman-arie/devops-exercises (CC BY-NC-ND)."]
    NOTICE.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
