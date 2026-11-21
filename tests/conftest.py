import os
import sys
import tempfile
from pathlib import Path

import pytest

# 테스트는 항상 모의 모드와 임시 outputs 로 돈다. .env 에 키가 있어도 실제 API 를 부르지 않는다
os.environ["BEDROCK_MOCK"] = "1"
os.environ["OUTPUTS_DIR"] = tempfile.mkdtemp(prefix="curri-test-")
os.environ["BEDROCK_CACHE"] = "0"
os.environ["LLM_BACKEND"] = "bedrock"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    from shared import schema
    monkeypatch.setattr(schema, "DIR", tmp_path)
