"""GitHub 저장소 목록 모으기: 주제 목록 → data/github_repos/ 의 조각 파일(jsonl).

공식 검색 API(api.github.com/search/repositories)만 쓴다. 조건은 stars:>=200 pushed:>=2023-01-01 archived:false.
한 검색은 1000개까지만 주므로, 1000개 이상이면 만든 날짜 구간을 반으로 쪼개 1000개 아래가 될 때까지 나눈다.
조각 하나 = 주제 하나의 날짜 구간 하나. 끝난 조각은 done.jsonl 에 적어 다시 돌리면 건너뛴다.
GITHUB_TOKEN 이 있으면 분당 30번, 없으면 10번 (.env 에서도 읽는다). 토큰 값은 출력하지 않는다.
쓰기: python -m m2_project.repos collect [주제...] / stats / reorganize
조각은 주제의 분야에 따라 data/github_repos/ai/ 또는 cloud/ 에 둔다. done.jsonl 은 바로 아래 하나.
"""
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from m2_project.guard import refuse_if_running
from shared import config

DIR = config.ROOT / "data" / "github_repos"
API = "https://api.github.com/search/repositories"
UA = "Mozilla/5.0 (research collector)"
CUTOFF = "2023-01-01"
MIN_STARS = 200
FIRST_DAY = date(2008, 1, 1)
CAP = 1000
PER_PAGE = 100
AI_TOPICS = [
    "machine-learning", "deep-learning", "artificial-intelligence", "llm", "large-language-models", "generative-ai",
    "diffusion-models", "stable-diffusion", "computer-vision", "object-detection", "nlp", "natural-language-processing",
    "speech", "speech-recognition", "text-to-speech", "reinforcement-learning", "multimodal", "vision-language",
    "rag", "ai-agents", "chatbot", "prompt-engineering", "fine-tuning", "pytorch", "tensorflow", "transformers",
    "langchain", "vector-database", "data-science",
]
CLOUD_TOPICS = [
    "data-engineering", "data-pipeline", "airflow", "spark", "mlops", "llmops", "model-serving", "kubeflow",
    "feature-store", "kubernetes", "docker", "cloud", "cloud-native", "aws", "aws-lambda", "serverless", "terraform",
    "distributed-training", "ray", "gpu",
]
TOPICS = AI_TOPICS + CLOUD_TOPICS
FIELD_OF_TOPIC = {**{t: "ai" for t in AI_TOPICS}, **{t: "cloud" for t in CLOUD_TOPICS}}
FIELD_DIRS = ("ai", "cloud")


def field_of(topic):
    """주제 → 'ai' | 'cloud'. 표에 없으면 KeyError."""
    return FIELD_OF_TOPIC[topic]


def shard_path(node):
    """조각 이름 '<주제>__<구간>' → 파일 경로 (<분야>/ 아래)."""
    return DIR / field_of(node.split("__")[0]) / f"{node}.jsonl"


def parse(item, slice_name):
    """검색 결과 항목 하나 → 우리가 쓰는 칸만 남긴 사전."""
    return {
        "full_name": item["full_name"], "url": item["html_url"], "description": item.get("description"),
        "topics": item.get("topics") or [], "stars": item["stargazers_count"], "forks": item["forks_count"],
        "pushed_at": item["pushed_at"], "created_at": item["created_at"],
        "license": (item.get("license") or {}).get("spdx_id"), "language": item.get("language"),
        "archived": item["archived"], "slices": [slice_name],
    }


def split_range(a, b):
    """날짜 구간 (a, b) → 반으로 나눈 두 구간. 하루짜리면 None."""
    if a >= b:
        return None
    mid = a + (b - a) // 2
    return (a, mid), (mid + timedelta(days=1), b)


def query(topic, a, b):
    return f"topic:{topic} stars:>={MIN_STARS} pushed:>={CUTOFF} archived:false created:{a}..{b}"


def node_name(topic, a, b):
    return f"{topic}__{a}_{b}"


def merge(shard_rows):
    """조각들의 행 → full_name 으로 합친 사전. 겹친 저장소는 slices 를 모두 남긴다."""
    out = {}
    for row in shard_rows:
        got = out.setdefault(row["full_name"], row)
        if got is not row:
            got["slices"] = sorted(set(got["slices"]) | set(row["slices"]))
    return out


class Client:
    def __init__(self):
        self.token = config.get("GITHUB_TOKEN")
        self.gap = 60 / (30 if self.token else 10) + 0.5
        self.last = 0.0
        self.calls = 0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "application/vnd.github+json"})
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def search(self, q, page):
        """검색 한 쪽 → (전체 개수, 항목들). 403/429 면 풀리는 때까지 자고 다시 한다."""
        for _ in range(6):
            time.sleep(max(0.0, self.last + self.gap - time.time()))
            r = self.session.get(API, params={"q": q, "per_page": PER_PAGE, "page": page, "sort": "stars"}, timeout=60)
            self.last = time.time()
            self.calls += 1
            if r.status_code in (403, 429):
                wait = int(r.headers.get("retry-after") or max(0, int(r.headers.get("x-ratelimit-reset", 0)) - time.time()) + 2)
                print(f"  한도 도달, {min(max(wait, 5), 3700)}초 쉼", flush=True)
                time.sleep(min(max(wait, 5), 3700))
                continue
            r.raise_for_status()
            d = r.json()
            return d["total_count"], d["items"]
        raise RuntimeError("rate limit 가 계속됨")


def read_done():
    path = DIR / "done.jsonl"
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s] if path.exists() else []
    return {r["node"]: r for r in rows}


def mark(node, status, total, n=0):
    with (DIR / "done.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"node": node, "status": status, "total": total, "saved": n}) + "\n")


def collect_topic(client, topic, done):
    """한 주제 → 날짜 구간을 쪼개며 조각 파일을 쓴다. 실패한 조각은 건너뛰고 실패 목록에 담는다."""
    failed, stack = [], [(FIRST_DAY, date.today())]
    while stack:
        a, b = stack.pop()
        node = node_name(topic, a, b)
        if node in done:
            if done[node]["status"] == "split":
                stack += list(split_range(a, b))
            continue
        try:
            total, items = client.search(query(topic, a, b), 1)
            if total >= CAP and (halves := split_range(a, b)):
                mark(node, "split", total)
                stack += list(halves)
                continue
            for p in range(2, -(-min(total, CAP) // PER_PAGE) + 1):
                items += client.search(query(topic, a, b), p)[1]
        except Exception as e:
            print(f"  실패 {node}: {type(e).__name__} {e}", flush=True)
            failed.append(node)
            continue
        rows = [parse(i, topic) for i in items]
        path = shard_path(node)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        mark(node, "done", total, len(rows))
        print(f"  {node}: {len(rows)}/{total}" + ("  (1000 한도에 걸림)" if total >= CAP else ""), flush=True)
    return failed


def collect(topics=None):
    DIR.mkdir(parents=True, exist_ok=True)
    client, failed = Client(), []
    print("토큰:", "있음" if client.token else "없음 (분당 10번)", flush=True)
    for t in topics or TOPICS:
        print(t, flush=True)
        failed += collect_topic(client, t, read_done())
    print(f"검색 {client.calls}번, 실패 {len(failed)}: {failed}")


def shard_files():
    """조각 파일 전부: 옛 위치(바로 아래) + ai/ + cloud/."""
    return sorted([*DIR.glob("*__*.jsonl"), *(p for d in FIELD_DIRS for p in (DIR / d).glob("*__*.jsonl"))])


def load(field=None):
    """모든 조각 → {full_name: 저장소}. 한 저장소가 ai·cloud 주제에 다 걸리면 두 폴더의 조각에 각각 있고,
    여기서 하나로 합쳐 slices 와 fields(걸린 분야 목록, 예 ["ai", "cloud"]) 를 단다. field 를 주면 그 분야에 걸린 것만."""
    repos = merge(json.loads(s) for p in shard_files() for s in p.read_text(encoding="utf-8").splitlines() if s)
    for r in repos.values():
        r["fields"] = sorted({field_of(t) for t in r["slices"]})
    return {k: r for k, r in repos.items() if field is None or field in r["fields"]}


def reorganize():
    """옛 위치의 조각을 <분야>/ 로 옮긴다 (done.jsonl 은 그대로: 조각 이름이 주제에서 분야를 정하므로 고칠 것이 없다). → 옮긴 개수"""
    refuse_if_running("m2_project.repos", "reorganize")
    moved = 0
    for p in sorted(DIR.glob("*__*.jsonl")):
        dest = DIR / field_of(p.name.split("__")[0]) / p.name
        dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"{dest} 가 이미 있다. 손으로 확인")
        p.replace(dest)
        moved += 1
    print(f"reorganize: {moved}개 조각 이동")
    return moved


def dedupe():
    """조각 → repos.jsonl (저장소 하나에 한 줄, 별 많은 순). 조각은 모으기 기록이라 그대로 둔다. → 줄 수"""
    refuse_if_running("m2_project.repos", "dedupe")
    rows = sorted(load().values(), key=lambda r: -r["stars"])
    (DIR / "repos.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"dedupe: {len(rows)}개 → {DIR / 'repos.jsonl'}")
    return len(rows)


def stats():
    repos, done = load(), read_done()
    per = {}
    for r in repos.values():
        for s in r["slices"]:
            per[s] = per.get(s, 0) + 1
    print(f"합계(중복 제거) {len(repos)}, 조각 {sum(v['status'] == 'done' for v in done.values())}, 쪼갠 것 {sum(v['status'] == 'split' for v in done.values())}")
    print("| 주제 | 분야 | 저장소 수 |\n|---|---|---|")
    for t in TOPICS:
        print(f"| {t} | {field_of(t)} | {per.get(t, 0)} |")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["stats"]
    {"collect": lambda: collect(rest), "reorganize": reorganize, "dedupe": dedupe}.get(cmd, stats)()
