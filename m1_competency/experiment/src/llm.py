"""Bedrock(Claude)과 OpenAI(GPT) 호출. 같은 요청은 cache/에 저장해 다시 돌리면 무료."""
import hashlib, json, os, time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _cache_path(model_id: str, prompt: str, run: int) -> Path:
    key = hashlib.sha256(f"{model_id}|{run}|{prompt}".encode()).hexdigest()[:24]
    return CACHE_DIR / f"{key}.json"


def call_model(cfg: dict, prompt: str, run: int = 1, temperature=None, max_tokens: int = 8000) -> dict:
    """cfg 예: {"provider": "bedrock", "id": "global.anthropic.claude-sonnet-4-6"}
    run 번호가 다르면 다른 호출로 취급(반복 실행용). 반환: text, seconds, input_tokens, output_tokens, cached
    """
    path = _cache_path(cfg["id"], prompt, run)
    if path.exists():
        out = json.loads(path.read_text(encoding="utf-8"))
        out["cached"] = True
        return out

    t0 = time.time()
    if cfg["provider"] == "bedrock":
        import boto3
        client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "ap-northeast-2"))
        inf = {"maxTokens": max_tokens}
        if temperature is not None:
            inf["temperature"] = temperature
        r = client.converse(modelId=cfg["id"],
                            messages=[{"role": "user", "content": [{"text": prompt}]}],
                            inferenceConfig=inf)
        text = "".join(c.get("text", "") for c in r["output"]["message"]["content"])
        tin, tout = r["usage"].get("inputTokens"), r["usage"].get("outputTokens")
    elif cfg["provider"] == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        kw = {} if temperature is None else {"temperature": temperature}
        r = client.chat.completions.create(model=cfg["id"],
                                           messages=[{"role": "user", "content": prompt}], **kw)
        text = r.choices[0].message.content
        tin, tout = r.usage.prompt_tokens, r.usage.completion_tokens
    else:
        raise ValueError(f"모르는 provider: {cfg['provider']}")

    out = {"text": text, "seconds": round(time.time() - t0, 1),
           "input_tokens": tin, "output_tokens": tout}
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    out["cached"] = False
    return out
