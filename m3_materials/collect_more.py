"""교육자료 더 모으기: 허용 라이선스 GitHub 저장소의 레슨·랩·노트북·문서 튜토리얼 → data/bank_additions/learn_more.csv.

진욱 수집기(m3_materials/collect_edu.py, 읽기만)의 추출 규칙을 그대로 불러 쓴다. 제목, 주소, 첫 문단 요약(300자 이내)만 남기고 본문은 옮기지 않는다.
라이선스는 MIT, MIT-0, Apache-2.0, BSD-3-Clause, CC0-1.0, CC-BY-3.0/4.0 만. --licenses 가 GitHub 이 읽은 라이선스와 표를 맞춰 본다.
받기: 트리만 먼저 받고(blob 없이), 고른 파일만 sparse checkout 으로 받는다. 받은 파일은 읽기만 하고 실행하지 않는다.
거름: 노트북 모음의 폴더 README(노트북 없는 앱·틀)는 버린다 (pick.teaches 3번과 같은 규칙). 요약이 없거나 정리·준비 쪽 제목도 버린다.

  python -I m3_materials/collect_more.py --work <빈 scratch 폴더> [--plan] [--licenses]
  (--plan: 트리만 받아 고를 파일 수만 센다. 한 곳이라도 받지 못하면 csv 를 쓰지 않는다.)
"""
import argparse
import csv
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect_edu as je  # noqa: E402  진욱 수집기의 제목·요약 추출과 레슨 규칙

# 첫 문단이 상용구면 다음 문단을 요약으로 쓰도록 진욱 규칙(JUNK)에 더한다. 11/19 원천별 표본 5줄씩을 보고 고름.
je.JUNK = re.compile(je.JUNK.pattern + r"|tested (with|on|using|in)|Compatibility Notice|SageMaker Distribution Image|"
                     r"(set|select|choose) (the )?kernel|should work well with|Run the following (setup )?cell|"
                     r"Ask Anton|New here\?|retained purely for archival|Unless required by applicable law|"
                     r"^\W*Note:? Please|should take approximately|In order to benefit from this|was authored|"
                     r"authored by|(revised|updated) version of (a )?notebook", re.I)
_title_and_summary = je.title_and_summary


def title_and_summary(text):
    """HTML 주석(라이선스 머리말)과 머리말 안의 목록 줄(ms.custom 꼬리표가 description 에 붙는다)을 지우고,
    rst 윗줄(=====)과 맨 앞 굵은 글씨 제목을 # 제목으로 바꿔 진욱 규칙에 넘긴다."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    front = re.match(r"(---\s*\n)(.*?)(\n---\s*\n)", text, re.S)
    if front:
        text = front[1] + re.sub(r"(?m)^\s+-\s.*\n?", "", front[2]) + front[3] + text[front.end():]
    text = re.sub(r"\A\s*([=\-~*^#])\1{3,}[ \t]*\n", "", text)
    text = re.sub(r"\A\s*\*\*([^*\n]{5,120})\*\*[ \t]*\n", r"# \1\n\n", text)
    return _title_and_summary(text)


je.title_and_summary = title_and_summary

OUT = HERE / "data" / "bank_additions" / "learn_more.csv"
FIELDS = ["id", "bank", "type", "title", "url", "topic", "summary", "source", "license", "minutes", "dup_ids",
          "target_case", "target_cid"]
LICENSES = {"MIT", "MIT-0", "Apache-2.0", "BSD-3-Clause", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0"}
EXTS = {"nb": (".ipynb",), "file": (".md", ".mdx"), "gallery": (".py",), "lesson": (".md",)}
AGENT_FILES = re.compile(r"(^|/)(CLAUDE|AGENTS|GEMINI|SKILL)\.md$|/release(s|-notes)?(/|\.md)", re.I)
LOCALE = re.compile(r"(^|/)(ko|ja|zh|zh-cn|zh-tw|zh-hans|es|fr|de|pt|pt-br|it|ru|tr|vi|id|ar|hi|bn|fa|pl|uk|he|th|"
                    r"translations?|translated_images|i18n|localized)(/|$)", re.I)
NOT_LESSON = re.compile(r"^(prerequisites?|pre-requisites|next steps|resources|references|acknowledg(e)?ments?|"
                        r"license|contributors?|faq|table of contents|code of conduct|security|support|contributing|"
                        r"thank you|conclusion|running the example|feedback or issues\?)$|"
                        r"\b(clean ?-?up|tear ?down|changelog|release (notes|process))\b", re.I)

L, LAB, NB, DOC, ART = "강의 레슨", "워크숍 랩", "실습 노트북", "공식 문서 튜토리얼", "글"
# 저장소, 가지, 라이선스, 방식, 유형, 받을 경로(glob), 뺄 경로(정규식)
#   방식 nb: 노트북 하나 / file: md·mdx 하나 / gallery: 예제 .py 의 docstring / lesson: 레슨 폴더 README 하나
SOURCES = [
    # AWS 실습·워크숍
    ("aws-samples/amazon-bedrock-samples", "main", "MIT-0", "nb", NB, ["*"], None),
    ("aws-samples/sample-gen-ai-evaluations-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/bedrock-multi-agents-collaboration-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/amazon-bedrock-rag-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/bedrock-kb-rag-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/llm-apps-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/langgraph-agents-with-amazon-bedrock", "main", "MIT-0", "nb", NB, ["*"], None),
    ("aws-samples/prompt-engineering-with-anthropic-claude-v-3", "main", "MIT-0", "nb", L, ["*"], None),
    ("aws-samples/sample-getting-started-with-strands-agents-course", "main", "MIT-0", "nb", L, ["*"], None),
    ("aws-samples/amazon-sagemaker-immersion-day", "master", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/sagemaker-end-to-end-workshop", "main", "MIT-0", "nb", LAB, ["*"], r"/config/"),
    ("aws-samples/amazon-sagemaker-mlops-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/amazon-sagemaker-feature-store-end-to-end-workshop", "main", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/amazon-sagemaker-generativeai", "main", "MIT-0", "nb", NB, ["*"], r"/x_archive/"),
    ("aws-samples/sagemaker-genai-hosting-examples", "main", "MIT-0", "nb", NB, ["*"], r"^/01-models/"),
    ("aws-samples/aws-research-workshops", "mainline", "MIT-0", "nb", LAB, ["*"], None),
    ("aws-samples/asynchronous-messaging-workshop", "master", "MIT-0", "file", LAB, ["workshop/content/*_index*.md"],
     None),
    # Azure·Microsoft
    ("Azure/azureml-examples", "main", "MIT", "nb", NB, ["tutorials/*", "sdk/python/*"], None),
    ("Azure-Samples/AI-Gateway", "main", "MIT", "nb", LAB, ["labs/*"], r"/_deprecated/"),
    ("MicrosoftLearning/mslearn-ai-agents", "main", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/mslearn-ai-fundamentals", "main", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/mslearn-fabric", "main", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/mslearn-databricks", "main", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/mslearn-devops", "main", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/DP-900T00A-Azure-Data-Fundamentals", "master", "MIT", "file", LAB, ["Instructions/*"], None),
    ("MicrosoftLearning/dp-420-cosmos-db-dev", "main", "MIT", "file", LAB, ["instructions/*"], None),
    ("MicrosoftLearning/AZ-700-Designing-and-Implementing-Microsoft-Azure-Networking-Solutions", "master", "MIT",
     "file", LAB, ["Instructions/Exercises/*"], None),
    ("microsoft/Generative-AI-for-beginners-dotnet", "main", "MIT", "lesson", L, ["*"], r"/samples/"),
    ("microsoft/generative-ai-with-javascript", "main", "MIT", "lesson", L, ["lessons/*", "README.md"], None),
    ("microsoft/Web-Dev-For-Beginners", "main", "MIT", "lesson", L, ["*"], None),
    ("microsoft/Security-101", "main", "CC0-1.0", "file", L, ["[0-9]*.md"], r"quiz"),
    ("microsoft/code-with-engineering-playbook", "main", "CC-BY-4.0", "file", ART, ["docs/*"], None),
    ("MicrosoftDocs/azure-docs", "main", "CC-BY-4.0", "file", DOC,
     ["articles/*/tutorial-*.md", "articles/*/quickstart-*.md"],
     r"/articles/(migrate|backup|site-recovery|energy-data-services|operator-service-manager|azure-vmware|"
     r"firmware-analysis|update-manager|resource-mover|lab-services|data-manager-for-agri|azure-maps|"
     r"microsoft-discovery|azure-compute-fleet|automanage|azure-change-tracking-inventory|artifact-signing)/"),
    # Google Cloud
    ("GoogleCloudPlatform/vertex-ai-samples", "main", "Apache-2.0", "nb", NB,
     ["notebooks/official/*", "notebooks/community/*"], r"/community/(model_garden|gapic|migration)/"),
    ("GoogleCloudPlatform/asl-ml-immersion", "main", "Apache-2.0", "nb", NB, ["*/notebooks/*"], None),
    # Hugging Face 문서 (참조 API 쪽은 뺀다)
    ("huggingface/transformers", "main", "Apache-2.0", "file", DOC, ["docs/source/en/*"],
     r"/(model_doc|main_classes|internal|reference)/"),
    ("huggingface/diffusers", "main", "Apache-2.0", "file", DOC, ["docs/source/en/*"], r"/api/"),
    ("huggingface/peft", "main", "Apache-2.0", "file", DOC, ["docs/source/*"], r"/package_reference/"),
    ("huggingface/trl", "main", "Apache-2.0", "file", DOC, ["docs/source/*"], None),
    ("huggingface/accelerate", "main", "Apache-2.0", "file", DOC, ["docs/source/*"], r"/package_reference/"),
    ("huggingface/datasets", "main", "Apache-2.0", "file", DOC, ["docs/source/*"], r"/package_reference/"),
    ("huggingface/smolagents", "main", "Apache-2.0", "file", DOC, ["docs/source/en/*"], r"/reference/"),
    ("huggingface/evaluate", "main", "Apache-2.0", "file", DOC, ["docs/source/*"], r"/package_reference/"),
    # LLM·에이전트·평가·MLOps 도구의 튜토리얼
    ("langchain-ai/langgraph", "main", "MIT", "nb", NB, ["docs/docs/*", "examples/*"], None),
    ("run-llama/llama_index", "main", "MIT", "nb", NB, ["docs/examples/*"],
     r"/examples/(vector_stores|llm|embeddings|data_connectors|multi_modal|observability|tools|managed|llama_hub|"
     r"chat_store|docstore|cookbooks|llama_dataset|benchmarks|instrumentation)/"),
    ("vibrantlabsai/ragas", "main", "Apache-2.0", "file", DOC, ["docs/*"], r"/references?/"),
    ("confident-ai/deepeval", "main", "Apache-2.0", "file", DOC, ["docs/content/*"], r"/(changelog|integrations)/"),
    ("openai/openai-agents-python", "main", "MIT", "file", DOC, ["docs/*"], r"/ref/"),
    ("pydantic/pydantic-ai", "main", "MIT", "file", DOC, ["docs/*"], r"/(api|comparisons)/"),
    ("crewAIInc/crewAI", "main", "MIT", "file", DOC, ["docs/edge/en/*"], r"/(api-reference|enterprise|tools)/"),
    ("mlflow/mlflow", "master", "Apache-2.0", "file", DOC, ["docs/docs/*"],
     r"/(api_reference|integrations|self-hosting)/"),
    ("microsoft/autogen", "main", "CC-BY-4.0", "nb", NB, ["python/docs/src/*"], None),
    # ML 기초
    ("scikit-learn/scikit-learn", "main", "BSD-3-Clause", "gallery", NB, ["examples/*"], r"/release_highlights/"),
    ("ageron/handson-ml3", "main", "Apache-2.0", "nb", NB, ["*"], None),
    ("jax-ml/jax", "main", "Apache-2.0", "nb", DOC, ["docs/*"], r"/jep/"),
    # 소프트웨어 공학
    ("github/docs", "main", "CC-BY-4.0", "file", DOC, ["content/actions/*", "content/pull-requests/*",
     "content/get-started/start-your-journey/*", "content/get-started/using-git/*",
     "content/get-started/git-basics/*"], None),
    ("google/eng-practices", "master", "CC-BY-3.0", "file", ART, ["review/*"], None),
    ("reactjs/react.dev", "main", "CC-BY-4.0", "file", DOC, ["src/content/learn/*"], None),
    ("microsoft/TypeScript-Website", "v2", "CC-BY-4.0", "file", DOC, ["packages/documentation/copy/en/*"], None),
    ("rust-lang/book", "main", "MIT", "file", L, ["src/ch*"], None),
    ("open-telemetry/opentelemetry.io", "main", "CC-BY-4.0", "file", DOC,
     ["content/en/docs/concepts/*", "content/en/docs/languages/*", "content/en/docs/collector/*"], None),
    ("istio/istio.io", "master", "Apache-2.0", "file", DOC, ["content/en/docs/tasks/*", "content/en/docs/concepts/*"],
     None),
]


def lrn_id(url):
    return "LRN" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def url_key(u):
    s = urlsplit(u.strip())
    return s.netloc.lower().removeprefix("www.") + s.path.rstrip("/")


def git(d, *args, stdin=None):
    return subprocess.run(["git", "-C", str(d), *args], input=stdin, capture_output=True, text=True, check=True,
                          timeout=1800).stdout


def tree(src, work: Path):
    """blob 없이 트리만 받는다. → (폴더, [경로]). 크기는 묻지 않는다 (-l 은 blob 을 하나씩 받는다)."""
    repo, branch = src[0], src[1]
    d = work / repo.replace("/", "__")
    if not (d / ".git").exists():
        subprocess.run(["git", "clone", "-q", "--no-checkout", "--depth", "1", "--filter=blob:none", "-b", branch,
                        f"https://github.com/{repo}", str(d)], check=True, timeout=1800)
        time.sleep(1.1)
    return d, [p for p in git(d, "ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0") if p]


def wanted(src, files):
    """받을 파일: 방식의 확장자, 받을 경로, 뺄 경로, 번역본. 맨 위 README 는 코스 이름에 쓴다."""
    _, _, _, mode, _, include, exclude = src
    pick = []
    for path in files:
        if path == "README.md":
            pick.append(path)
            continue
        if not path.lower().endswith(EXTS[mode]) or LOCALE.search(path) or AGENT_FILES.search(path) \
                or not any(fnmatch.fnmatch(path, g) for g in include) or (exclude and re.search(exclude, "/" + path)):
            continue
        if mode == "lesson" and Path(path).name.lower() != "readme.md":
            continue
        pick.append(path)
    return pick


def checkout(d: Path, paths):
    """고른 파일만 받는다. 같은 목록이면 다시 받지 않는다."""
    mark = d / ".git" / "learn_more_paths"
    listing = "\n".join(sorted(paths))
    if mark.exists() and mark.read_text("utf-8") == listing:
        return
    pats = "\n".join("/" + re.sub(r"([*?\[\]\\!#])", r"\\\1", p) for p in paths if "\n" not in p) + "\n"
    git(d, "sparse-checkout", "set", "--no-cone", "--stdin", stdin=pats)
    git(d, "checkout", "-q", "HEAD")
    mark.write_text(listing, "utf-8")
    time.sleep(1.1)


def rows_of(src, d: Path):
    """진욱 수집기의 lessons() 로 뽑고, 은행 꼴로 바꾸며 거른다."""
    repo, branch, lic, mode, typ = src[:5]
    got = je.lessons((repo, branch, "", lic, mode, typ, None), d)
    course, out = got[0]["title"], []
    for r in got[1:]:
        title, summary = r["title"].strip(), r["summary"].strip()
        bare = re.sub(r"^.*?: ", "", title)
        if ("/tree/" in r["url"] and typ in (NB, DOC, ART)) or len(summary) < 40 or NOT_LESSON.search(bare):
            continue
        topic = f'{course} · {r["topic"]}' if r["topic"] and r["topic"].lower() != course.lower() else course
        out.append({"id": lrn_id(r["url"]), "bank": "추가", "type": typ, "title": title, "url": r["url"],
                    "topic": topic[:200], "summary": summary, "source": repo, "license": lic,
                    "minutes": "", "dup_ids": "", "target_case": "", "target_cid": ""})
    return out


def check_licenses():
    bad = []
    for src in SOURCES:
        repo, lic = src[0], src[2]
        got = subprocess.run(["gh", "api", f"repos/{repo}/license", "--jq", ".license.spdx_id"],
                             capture_output=True, text=True).stdout.strip()
        ok = lic in LICENSES and (got == lic or got == "NOASSERTION")
        print(f"{'OK ' if ok else 'BAD'} {repo}: 표 {lic}, GitHub {got or '없음'}")
        bad += [] if ok else [repo]
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="저장소를 받을 빈 scratch 폴더")
    ap.add_argument("--plan", action="store_true", help="트리만 받고 고를 파일 수만 센다")
    ap.add_argument("--licenses", action="store_true", help="GitHub 이 읽은 라이선스와 표를 맞춰 본다")
    a = ap.parse_args()
    if a.licenses:
        sys.exit(1 if check_licenses() else 0)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    rows, seen, per, failed = [], set(), Counter(), []
    for src in SOURCES:
        try:
            d, files = tree(src, work)
            paths = wanted(src, files)
            if a.plan:
                print(f"{len(paths) - ('README.md' in paths):5d}  {src[0]}")
                continue
            checkout(d, paths)
            got = rows_of(src, d)
        except Exception as e:  # 한 저장소가 실패해도 나머지는 계속
            print(f"실패: {src[0]}: {e}")
            failed.append(src[0])
            continue
        for r in got:
            k = url_key(r["url"])
            t = (" ".join(re.findall(r"\w+", r["title"].lower())), r["source"], r["summary"])
            if k in seen or t in seen:
                continue
            seen |= {k, t}
            rows.append(r)
            per[src[0]] += 1
        print(f"{per[src[0]]:5d}  {src[0]}")
    if a.plan:
        return
    if failed:  # 받지 못한 원천이 있으면 은행이 줄어든 파일을 쓰지 않는다
        sys.exit(f"쓰지 않음: {len(failed)}곳 실패 {failed}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}줄 → {OUT}")
    print(json.dumps(Counter(r["type"] for r in rows), ensure_ascii=False))


if __name__ == "__main__":
    main()
