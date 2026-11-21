"""모델에게 주는 지시문이 그대로인지 지킨다.

같은 지시문이면 outputs/cache 의 저장된 답을 다시 써서 돈이 들지 않는다. 글자 하나만 바뀌어도 저장본이 안 맞아 다시 돈이 든다.
지시문을 일부러 고쳤다면 아래 값을 새 값으로 바꾸고, 다시 돌리는 데 드는 돈을 먼저 어림한다.
"""
import hashlib
import importlib

import pytest

PINNED = [
    ("m1_competency.competencies", "REFINE_SYSTEM", "7ddc4bf53df98cfb"),
    ("m1_competency.competencies", "REFINE_PROMPT", "5e7b43bfdbf9586c"),
    ("m1_competency.extract", "EXTRACT_SYSTEM", "61630028a11a4333"),
    ("m2_project.search", "QUERY_SYSTEM", "34323e6225c68cf7"),
    ("m2_project.pick", "JUDGE_SYSTEM", "e5d2adc72218f2a7"),
]


@pytest.mark.parametrize("module, name, digest", PINNED)
def test_prompt_text_is_unchanged(module, name, digest):
    text = getattr(importlib.import_module(module), name)
    assert hashlib.sha256(text.encode()).hexdigest()[:16] == digest, f"{module}.{name} 이 바뀌었다. 저장된 답이 맞지 않아 다시 돌리면 돈이 든다"
