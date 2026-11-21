"""프로젝트 DB 검색 (Vercel 용): 논문·저장소 111,753개를 SQLite 전문 검색(FTS5) 한 파일로. 메모리에 다 올리지 않는다
(BM25 피클은 1.5GB 를 써서 Vercel 무료 한도 2GB 에 빠듯하다). 순위 규칙은 m2_project.local.rank 와 같다:
검색어마다 위 DEPTH 개에 1/(순위+1) 을 더한다 (점수 크기가 아니라 순위만). 점수는 SQLite 의 bm25().
  만들기: PYTHONPATH=. python -m demo.search_db build <나올 파일.sqlite>     (outputs/project/local_bm25.pkl 에서, 모델 없음)
  쓰기:   SEARCH_DB=<파일> 이면 demo/live.py 가 이것으로 찾는다. <파일>.gz 만 있으면 처음 한 번 풀어 둔다 (/tmp)"""
import gzip
import os
import shutil
import sqlite3
import sys
import threading
from functools import lru_cache
from pathlib import Path

FIELDS = ("key", "kind", "title", "year", "venue", "url", "stars", "code_url", "text")
_lock = threading.Lock()


def path():
    p = os.environ.get("SEARCH_DB")
    if not p:
        return None
    p = Path(p)
    if not p.exists() and Path(str(p) + ".gz").exists():      # 처음 한 번 푼다 (Vercel: 레포의 .gz → /tmp)
        with _lock:
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".part")
                with gzip.open(str(p) + ".gz", "rb") as src, open(tmp, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                tmp.replace(p)
    if not p.exists():
        gz = Path(__file__).resolve().parents[1] / "data" / "search" / "projects.sqlite.gz"      # 레포에 실은 판
        if gz.exists():
            os.environ["SEARCH_DB"] = str(p)
            p.parent.mkdir(parents=True, exist_ok=True)
            with _lock, gzip.open(gz, "rb") as src, open(p, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
    return p if p.exists() else None


def conn():
    c = sqlite3.connect(f"file:{path()}?mode=ro", uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


class Bank:
    """bank[i] → 후보 한 건 (dict). i 는 SQLite 의 rowid. 읽은 것은 기억한다"""
    def __init__(self):
        self.c = conn()
        self.cache = {}

    def __getitem__(self, i):
        if i not in self.cache:
            r = self.c.execute(f"SELECT {', '.join(FIELDS)} FROM docs WHERE rowid = ?", (i,)).fetchone()
            d = {k: r[k] for k in FIELDS if r[k] not in (None, "")}
            if "stars" in d:
                d["stars"] = int(d["stars"])
            self.cache[i] = d
        return self.cache[i]

    def counts(self):
        return dict(self.c.execute("SELECT kind, count(*) FROM docs GROUP BY kind").fetchall())


def _match(q):
    from m2_project.local import tokens
    words = sorted(set(tokens(q)))
    return " OR ".join(f'"{w}"' for w in words) if words else None


def rank(bank, queries, depth=None):
    """{kind: [검색어]} → {rowid: 점수} (local.rank 와 같은 1/(순위+1) 합)"""
    from m2_project.local import DEPTH
    depth = depth or DEPTH
    score = {}
    for kind, qs in queries.items():
        for q in qs:
            m = _match(q)
            if not m:
                continue
            rows = bank.c.execute("SELECT rowid FROM fts WHERE fts MATCH ? AND kind = ? ORDER BY bm25(fts) LIMIT ?", (m, kind, depth)).fetchall()
            for r, (i,) in enumerate(rows):
                score[i] = score.get(i, 0) + 1 / (r + 1)
    return score


def build(out):
    import pickle
    root = Path(__file__).resolve().parents[1]
    bank = pickle.loads((root / "outputs" / "project" / "local_bm25.pkl").read_bytes())["bank"]
    out = Path(out)
    if out.exists():
        out.unlink()
    c = sqlite3.connect(out)
    c.execute(f"CREATE TABLE docs ({', '.join(f + ' TEXT' for f in FIELDS)})")
    c.execute("CREATE VIRTUAL TABLE fts USING fts5(title, text, kind UNINDEXED, content='docs', content_rowid='rowid', tokenize='unicode61')")
    c.executemany(f"INSERT INTO docs ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
                  ([str(b.get(f, "")) if b.get(f) is not None else "" for f in FIELDS] for b in bank))
    c.execute("INSERT INTO fts (rowid, title, text, kind) SELECT rowid, title, text, kind FROM docs")
    c.execute("INSERT INTO fts(fts) VALUES ('optimize')")
    c.commit()
    c.execute("VACUUM")
    c.close()
    with open(out, "rb") as src, gzip.open(str(out) + ".gz", "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    print(out, f"{out.stat().st_size / 1e6:.0f}MB", "gz", f"{Path(str(out) + '.gz').stat().st_size / 1e6:.0f}MB", "docs", len(bank))


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build(sys.argv[2])
