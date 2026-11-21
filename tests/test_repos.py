import json
from datetime import date

from m2_project import repos

ITEM = {"full_name": "a/b", "html_url": "https://github.com/a/b", "description": None, "topics": ["llm"],
        "stargazers_count": 300, "forks_count": 5, "pushed_at": "2024-01-02T00:00:00Z",
        "created_at": "2021-03-04T00:00:00Z", "license": {"spdx_id": "MIT"}, "language": "Python", "archived": False}


def test_parse_keeps_needed_fields():
    r = repos.parse(ITEM, "llm")
    assert r["license"] == "MIT" and r["stars"] == 300 and r["slices"] == ["llm"] and r["description"] is None
    assert repos.parse({**ITEM, "license": None, "topics": None}, "x")["license"] is None


def test_split_range_covers_without_overlap():
    a, b = date(2020, 1, 1), date(2020, 1, 10)
    (a1, b1), (a2, b2) = repos.split_range(a, b)
    assert (a1, b2) == (a, b) and a2 - b1 == (date(2020, 1, 2) - date(2020, 1, 1))
    assert repos.split_range(a, a) is None


def test_merge_keeps_all_slices():
    rows = [repos.parse(ITEM, "llm"), repos.parse(ITEM, "rag"), repos.parse({**ITEM, "full_name": "c/d"}, "llm")]
    m = repos.merge(rows)
    assert len(m) == 2 and m["a/b"]["slices"] == ["llm", "rag"]


def test_query_has_cutoff():
    q = repos.query("llm", date(2020, 1, 1), date(2020, 2, 1))
    assert "stars:>=200" in q and "pushed:>=2023-01-01" in q and "created:2020-01-01..2020-02-01" in q


def test_topic_to_field():
    assert [repos.field_of(t) for t in ("llm", "pytorch", "kubernetes", "mlops", "ray")] == ["ai", "ai", "cloud", "cloud", "cloud"]
    assert set(repos.TOPICS) == set(repos.FIELD_OF_TOPIC) and len(repos.TOPICS) == 49
    assert repos.shard_path("kubernetes__2020-01-01_2020-02-01").parent.name == "cloud"


def _write(path, rows):
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_reorganize_moves_by_topic_and_load_sets_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(repos, "DIR", tmp_path)
    monkeypatch.setattr(repos, "refuse_if_running", lambda *a: None)
    both = repos.parse(ITEM, "llm")
    _write(tmp_path / "llm__2008-01-01_2026-01-01.jsonl", [both, repos.parse({**ITEM, "full_name": "c/d"}, "llm")])
    _write(tmp_path / "docker__2008-01-01_2026-01-01.jsonl", [repos.parse(ITEM, "docker")])
    (tmp_path / "done.jsonl").write_text("{}\n")
    before = repos.load()
    assert repos.reorganize() == 2
    assert (tmp_path / "ai" / "llm__2008-01-01_2026-01-01.jsonl").exists()
    assert (tmp_path / "cloud" / "docker__2008-01-01_2026-01-01.jsonl").exists()
    assert (tmp_path / "done.jsonl").exists() and not list(tmp_path.glob("*__*.jsonl"))
    after = repos.load()
    assert set(after) == set(before) == {"a/b", "c/d"}
    assert after["a/b"]["fields"] == ["ai", "cloud"] and after["c/d"]["fields"] == ["ai"]
    assert set(repos.load("cloud")) == {"a/b"} and set(repos.load("ai")) == {"a/b", "c/d"}


def test_dedupe_writes_one_line_per_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(repos, "DIR", tmp_path)
    monkeypatch.setattr(repos, "refuse_if_running", lambda *a: None)
    _write(tmp_path / "llm__2008-01-01_2026-01-01.jsonl", [repos.parse(ITEM, "llm")])
    _write(tmp_path / "docker__2008-01-01_2026-01-01.jsonl", [repos.parse(ITEM, "docker")])
    assert repos.dedupe() == 1
    [row] = [json.loads(s) for s in (tmp_path / "repos.jsonl").read_text().splitlines()]
    assert row["slices"] == ["docker", "llm"] and row["fields"] == ["ai", "cloud"]
