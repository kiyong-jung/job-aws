"""논문 서고의 읽기 함수: 작은 견본으로 확인한다. 네트워크는 쓰지 않는다."""
import pytest

from m2_project import library as L

ACL_BIB = '''@inproceedings{a-etal-2024-x,
    title = "{LLM}s for {P}arsing",
    author = "A, B",
    year = "2024",
    url = "https://aclanthology.org/2024.acl-long.5/",
    doi = "10.18653/v1/2024.acl-long.5",
    abstract = "We study parsing. Code at github.com/foo/bar.",
}
@inproceedings{a-etal-2024-w,
    title = "Workshop paper",
    year = "2024",
    url = "https://aclanthology.org/2024.wmt-1.5/",
    abstract = "skip me",
}
@inproceedings{a-etal-2023-f,
    title = "Findings one",
    year = "2023",
    url = "https://aclanthology.org/2023.findings-emnlp.9/",
    abstract = "Found.",
}
'''

DBLP = '''<dblp><inproceedings mdate="x" key="conf/aaai/A21"><author>A</author><title>Deep &eacute;tude of things.</title><year>2021</year><booktitle>AAAI</booktitle><ee>https://doi.org/10.1/x</ee></inproceedings><inproceedings mdate="x" key="conf/chi/B21">
<title>Late-breaking</title><year>2021</year><booktitle>CHI Extended Abstracts</booktitle>
</inproceedings>
<inproceedings mdate="x" key="conf/nips/C21"><title>T</title><year>2021</year><booktitle>NeurIPS</booktitle></inproceedings>
<inproceedings mdate="x" key="conf/asplos/D23"><title>Cloud thing.</title><year>2023</year><booktitle>ASPLOS (2)</booktitle></inproceedings>
</dblp>
'''


def test_acl_keeps_main_and_findings_only():
    rows = list(L.acl_rows(ACL_BIB.splitlines(True)))
    assert [(v, y) for v, y, _ in rows] == [("ACL", 2024), ("EMNLP-Findings", 2023)]
    assert rows[0][2]["title"] == "LLMs for Parsing"
    assert rows[0][2]["abstract"].startswith("We study parsing")


def test_dblp_reads_records_sharing_a_line_and_filters_booktitle():
    out = list(L.dblp_rows(DBLP.splitlines(True)))
    papers = [p for kind, _, _, p in out if kind == "논문"]
    assert [p["title"] for p in papers] == ["Deep étude of things", "Cloud thing"]
    assert papers[0]["abstract"] is None and papers[0]["doi"] == "10.1/x" and papers[1]["venue"] == "ASPLOS"
    assert [(k, v) for k, v, _, _ in out if k == "확인"] == [("확인", "nips")]


def test_list_parsers():
    nips = '<a title="paper title" href="/paper_files/paper/2024/hash/ab-Abstract-Conference.html">A &amp; B</a>'
    assert L.nips_list(nips, 2024)[0]["title"] == "A & B"
    cvf = '<dt class="ptitle"><br><a href="/content/CVPR2024/html/x_paper.html">T</a></dt>'
    assert L.cvf_list(cvf, "CVPR", 2024)[0]["url"].endswith("/content/CVPR2024/html/x_paper.html")
    eccv = '<!-- ECCV 2024 -->\n<dt class="ptitle">\n<br>\n<a href=papers/e/4.php>\nT2</a>'
    assert L.eccv_list(eccv)[2024][0]["url"] == "https://www.ecva.net/papers/e/4.php"
    assert L.abstract_of('<div id="abstract">\n Hi <b>there</b>\n</div>', L.CVF_ABS) == "Hi there"


def test_github_in_abstract():
    assert L.github_in("Code: https://github.com/foo/bar.") == "https://github.com/foo/bar"
    assert L.github_in("see github.com/a/b.git, ok") == "https://github.com/a/b"
    assert L.github_in("no link") is None


def test_code_links_marks_abstract_hits_only_to_T(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "PAPERS", tmp_path)
    monkeypatch.setattr(L, "REPOS", tmp_path / "none")
    monkeypatch.setattr(L, "pwc_index", lambda: ({}, {}))
    rows = [L.paper("ICLR", 2024, "One", "u", "Code at github.com/a/b."), L.paper("ICLR", 2024, "Two", "u", "nothing")]
    L.write_shard(L.shard("ICLR", 2024), rows)
    L.code_links()
    got = L.read_shard(L.shard("ICLR", 2024))
    assert [(r["has_code"], r["code_url"], r["code_source"]) for r in got] == \
        [("T", "https://github.com/a/b", "abstract"), ("F", "", "")]


USENIX_PAGE = '''<article id="node-1" class="node node-session view-mode-schedule"><h2>Correctness</h2>
<article id="node-2" class="node node-paper view-mode-schedule"><h2>
<a href="/conference/osdi20/presentation/boos">Theseus: an OS</a></h2>
<div class="field field-name-field-paper-description-long field-type-text-long"><p>First para.</p><p>Second &amp; last.</p></div></div></article>
<article id="node-3" class="node node-paper view-mode-schedule"><h2>
<a href="/conference/osdi20/presentation/two">Second</a></h2><div class="x"></div></article>'''


def test_usenix_list_reads_title_abstract_and_pdf():
    rows = L.usenix_list(USENIX_PAGE, "OSDI", 2020)
    assert [r["title"] for r in rows] == ["Theseus: an OS", "Second"]
    assert rows[0]["abstract"] == "First para. Second & last."
    assert rows[1]["abstract"] == ""
    assert rows[0]["pdf_url"] == "https://www.usenix.org/system/files/osdi20-boos.pdf"
    assert rows[0]["url"] == "https://www.usenix.org/conference/osdi20/presentation/boos"


def test_venue_to_field():
    assert [L.field_of(v) for v in ("ACL-Findings", "ICML", "CHI", "OSDI", "MLSys", "ASPLOS", "SIGCOMM", "ATC")] == \
        ["ai", "ai", "ai", "cloud", "cloud", "cloud", "cloud", "cloud"]
    with pytest.raises(KeyError):
        L.field_of("UNKNOWN")


def test_shard_prefers_field_folder_but_finds_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "PAPERS", tmp_path)
    assert L.shard("OSDI", 2021) == tmp_path / "cloud" / "OSDI_2021.jsonl"
    (tmp_path / "ACL_2024.jsonl").write_text("")
    assert L.shard("ACL", 2024) == tmp_path / "ACL_2024.jsonl"


def test_reorganize_moves_shards_by_field_and_keeps_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "PAPERS", tmp_path)
    (tmp_path / "_raw").mkdir()
    (tmp_path / "_raw" / "x_1.jsonl").write_text("raw")
    L.write_shard(tmp_path / "ACL-Findings_2023.jsonl", [L.paper("ACL-Findings", 2023, "a", "u")])
    L.write_shard(tmp_path / "SOSP_2021.jsonl", [L.paper("SOSP", 2021, "b", "u"), L.paper("SOSP", 2021, "c", "u")])
    before = sum(len(L.read_shard(p)) for p in L.all_shards())
    assert L.reorganize() == 2
    assert (tmp_path / "ai" / "ACL-Findings_2023.jsonl").exists() and (tmp_path / "cloud" / "SOSP_2021.jsonl").exists()
    assert not list(tmp_path.glob("*_*.jsonl")) and (tmp_path / "_raw" / "x_1.jsonl").read_text() == "raw"
    assert sum(len(L.read_shard(p)) for p in L.all_shards()) == before == 3
    assert L.reorganize() == 0


def test_pdf_url_rules():
    r = lambda v, u, **k: {"venue": v, "url": u, "arxiv": None, **k}
    assert L.pdf_url_of(r("ACL", "https://aclanthology.org/2024.acl-long.5/")) == "https://aclanthology.org/2024.acl-long.5.pdf"
    assert L.pdf_url_of(r("ICML", "https://proceedings.mlr.press/v162/abbas22a.html")) == "https://proceedings.mlr.press/v162/abbas22a/abbas22a.pdf"
    assert L.pdf_url_of(r("NeurIPS", "https://papers.nips.cc/paper_files/paper/2024/hash/ab-Abstract-Conference.html")) == \
        "https://papers.nips.cc/paper_files/paper/2024/file/ab-Paper-Conference.pdf"
    assert L.pdf_url_of(r("CVPR", "https://openaccess.thecvf.com/content/CVPR2024/html/x_paper.html")) == \
        "https://openaccess.thecvf.com/content/CVPR2024/papers/x_paper.pdf"
    assert L.pdf_url_of(r("ECCV", "https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/4_ECCV_2024_paper.php")) == \
        "https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/4_ECCV_2024_paper.pdf"
    assert L.pdf_url_of(r("IJCAI", "https://doi.org/10.24963/ijcai.2023/708")) == "https://www.ijcai.org/proceedings/2023/0708.pdf"
    assert L.pdf_url_of(r("NSDI", "https://www.usenix.org/conference/nsdi22/presentation/foo")) == "https://www.usenix.org/system/files/nsdi22-foo.pdf"
    assert L.pdf_url_of(r("KDD", "https://doi.org/10.1145/1")) == ""
    assert L.pdf_url_of(r("KDD", "https://doi.org/10.1145/1", arxiv="2101.00001")) == "https://arxiv.org/pdf/2101.00001"


def test_prune_keeps_pdf_rows_and_removes_others(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "PAPERS", tmp_path)
    monkeypatch.setattr(L, "refuse_if_running", lambda *a: None)
    rows = [L.paper("KDD", 2022, "has arxiv", "https://doi.org/10.1145/1", arxiv="2201.00001"),
            L.paper("KDD", 2022, "no pdf", "https://doi.org/10.1145/2"),
            L.paper("ACL", 2022, "official", "https://aclanthology.org/2022.acl-long.1/")]
    L.write_shard(tmp_path / "ai" / "KDD_2022.jsonl", rows[:2])
    L.write_shard(tmp_path / "ai" / "ACL_2022.jsonl", rows[2:])
    result = L.prune()
    assert result == {"KDD_2022": (2, 1), "ACL_2022": (1, 1)}
    kept = L.read_shard(tmp_path / "ai" / "KDD_2022.jsonl")
    assert [r["title"] for r in kept] == ["has arxiv"] and kept[0]["pdf_url"] == "https://arxiv.org/pdf/2201.00001"
    assert L.prune() == {"KDD_2022": (1, 1), "ACL_2022": (1, 1)}


def test_mlsys_list_uses_mlsys_host():
    page = '<a title="paper title" href="/paper_files/paper/2024/hash/ab-Abstract-Conference.html">T</a>'
    r = L.nips_list(page, 2024, "MLSys", "https://proceedings.mlsys.org")[0]
    assert r["venue"] == "MLSys" and r["url"].startswith("https://proceedings.mlsys.org/paper_files/")
    assert r["abstract"] is None
