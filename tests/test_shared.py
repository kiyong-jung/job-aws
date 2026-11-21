"""shared: 모델 부르기의 지출 장부와 한도, 은행 표의 스키마와 검색, 코드 전체의 정의되지 않은 이름."""
import builtins
import symtable

import pytest

from shared import config, llm, schema

SCHEMA = llm.obj({"x": llm.STR})

MILLION = {"input": 1_000_000, "output": 0, "cache_read": 0, "cache_write": 0}



@pytest.fixture
def ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path)
    monkeypatch.setattr(config, "BEDROCK_MOCK", False)
    monkeypatch.setattr(config, "BEDROCK_CACHE", False)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-fake")
    monkeypatch.setattr(llm, "_spent", {})
    monkeypatch.setattr(llm, "USAGE", dict(llm.USAGE, usd=0.0))
    sent = []
    monkeypatch.setattr(llm, "_anthropic",
                        lambda *a, **k: sent.append("direct") or {"data": {"x": "ok"}, "usage": dict(MILLION)})
    monkeypatch.setattr(llm, "_to_bedrock",
                        lambda model: lambda *a: sent.append("bedrock") or ('{"x": "ok"}', dict(MILLION), False))
    return tmp_path / "spend.tsv", sent



def test_direct_anthropic_calls_stop_at_the_anthropic_budget(ledger, monkeypatch):
    ledger, sent = ledger
    monkeypatch.setattr(config, "LLM_BACKEND", "anthropic")
    ledger.write_text(f"t\tclaude-opus-5-5\t{llm.ANTHROPIC_BUDGET}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Anthropic"):
        llm.ask_json("u", "s", SCHEMA, model="claude-opus-5-5")
    assert sent == []



def test_a_failed_call_still_books_the_tokens_it_used(ledger, monkeypatch):
    monkeypatch.setattr(llm, "_to_bedrock", lambda model: lambda *a: ("not json", dict(MILLION), False))
    with pytest.raises(RuntimeError, match="JSON"):
        llm.ask_json("u", "s", SCHEMA, model="global.anthropic.claude-sonnet-4-6")
    assert llm.spent()["bedrock"] == pytest.approx(9.0) and llm.cost() == 9.0      # 세 번 × 입력 100만 토큰 × 3달러
    monkeypatch.setattr(llm, "_to_bedrock", lambda model: lambda *a: ("{", dict(MILLION), True))
    with pytest.raises(RuntimeError, match="max_tokens"):
        llm.ask_json("u", "s", SCHEMA, model="global.anthropic.claude-sonnet-4-6")
    assert llm.spent()["bedrock"] == pytest.approx(12.0)



def test_a_bedrock_call_counts_its_won_for_the_m2_spend_cap(ledger, monkeypatch):
    monkeypatch.setattr(llm, "USAGE", dict(llm.USAGE, krw=0.0))
    llm.ask_json("u", "s", SCHEMA, model="global.anthropic.claude-sonnet-4-6")
    assert llm.USAGE["krw"] == pytest.approx(3.0 * llm.KRW_PER_USD)      # 입력 100만 토큰 × 3달러



def test_a_broken_ledger_line_keeps_every_call_stopped(ledger):
    ledger, sent = ledger
    ledger.write_text("broken line\nt\tglobal.anthropic.claude-sonnet-4-6\t500\n", encoding="utf-8")
    for _ in range(2):
        with pytest.raises(ValueError, match="spend.tsv"):
            llm.ask_json("u", "s", SCHEMA, model="global.anthropic.claude-sonnet-4-6")
    assert sent == []



def test_keyword_search_over_the_real_project_bank_ranks_the_named_project_first():
    hits = schema.index("projects").search("speech recognition whisper", k=3)
    assert hits[0]["title"] == "openai/whisper"
    assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)



def test_every_stored_row_fits_its_schema():
    for table in schema.TABLES:
        rows = schema.read(table)
        if table in ("postings", "posting_lines") and not rows:      # 공개판: 공고 원문은 싣지 않는다 (fetch 로 모은 뒤에 본다)
            continue
        assert rows, table
        assert [r["id"] for r in rows if schema.validate(table, r)] == [], table



def test_write_rejects_bad_rows_and_round_trips_lists(tmp_db):
    row = {"id": "Q1", "text": "What is KV cache?", "topic": "LLM", "source": "topic", "source_url": "https://x",
           "license": "MIT",
           "asked_at": ["OpenAI"], "answers": [{"title": "t", "url": "u"}]}
    with pytest.raises(ValueError, match="source"):
        schema.write("questions", [{**row, "source": "blog"}])
    with pytest.raises(ValueError, match="id"):
        schema.write("questions", [row, row])
    schema.write("questions", [row])
    assert schema.read("questions") == [{**row, "company": None, "intent": None, "concepts": None}]


def test_no_module_uses_a_name_it_never_defines_or_imports():
    """모의 모드 테스트가 지나지 않는 줄(웹 수집, 실제 모델 호출)의 빠진 가져오기까지 잡는다."""
    missing = []
    for path in sorted(p for d in ("shared", "m1_competency", "m2_project", "m3_materials")
                       for p in (config.ROOT / d).glob("*.py")):
        top = symtable.symtable(path.read_text(encoding="utf-8"), str(path), "exec")
        known = {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
        known |= set(dir(builtins)) | {"__file__"}
        tables = [top]
        while tables:
            t = tables.pop()
            tables += t.get_children()
            missing += [f"{path.name}: {s.get_name()}" for s in t.get_symbols()
                        if s.is_global() and s.is_referenced() and s.get_name() not in known]
    assert missing == []
