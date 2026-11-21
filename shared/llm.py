"""모델 부르기 전부. ask_json 은 JSON 스키마를 받아 그 모양의 dict 를 돌려준다. 임베딩은 embed_bizrouter, embed_titan.

bizrouter : LLM_BACKEND 의 기본값. OpenAI 호환 라우터로 같은 Claude 모델을 부르고, 쓴 원화를 outputs/spend_krw.tsv 에 남긴다.
anthropic : Anthropic API (기본 claude-opus-5-5). 구조화 출력(output_config.format)으로 JSON 을 보장하고,
            안전 분류기가 거절하면 서버가 다른 모델로 다시 돌리는 fallbacks="default" 를 켠다.
bedrock   : 모델 이름에 "anthropic." 이 들어 있으면 (예: global.anthropic.claude-sonnet-4-6) Bedrock Converse 로 부른다.
            답 모양은 지시문 끝에 붙인 스키마로 맞춘다 (_plain). 키가 없을 때도 이 경로다.
쓴 돈은 호출마다 outputs/spend.tsv 에 남긴다. 끝까지 답하지 못한 호출이 쓴 토큰도 남긴다.
Bedrock 이 BEDROCK_BUDGET 에 닿으면 같은 판의 Anthropic 모델로 넘어가고, Anthropic API 는 직접 부르든 넘어가든 ANTHROPIC_BUDGET 에 닿으면 멈춘다.
prefix 를 주면 그 글을 요청 맨 앞에 두고 캐시 표시를 붙인다. 여러 요청이 같은 긴 글(커리큘럼, 답 글)을 읽을 때 값이 싸진다.
같은 요청은 outputs/cache/ 의 저장본을 쓰고 사용량을 0 으로 센다 (cached). 열쇠는 물음 전체라 코드를 옮겨도 저장본이 맞는다.
"""
import hashlib
import json
import math
import re
import threading
from datetime import datetime
from functools import lru_cache

from . import config

USD_PER_MTOK = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50),
         # Bedrock 은 Anthropic 공개 단가로 어림한다. 실제 청구는 AWS 결제 화면에서 확인한다
         "global.anthropic.claude-sonnet-4-6": (3.0, 15.0),
         "global.anthropic.claude-haiku-4-5-20251001-v1:0": (1.0, 5.0),
         "global.anthropic.claude-opus-4-6-v1": (5.0, 25.0),
         "claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5": (1.0, 5.0), "claude-opus-4-6": (5.0, 25.0)}
SAME_ON_ANTHROPIC = {"global.anthropic.claude-sonnet-4-6": "claude-sonnet-4-6",
                     "global.anthropic.claude-haiku-4-5-20251001-v1:0": "claude-haiku-4-5",
                     "global.anthropic.claude-opus-4-6-v1": "claude-opus-4-6"}
CACHE_READ, CACHE_WRITE = 0.1, 1.25
USAGE = {"calls": 0, "cached": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "usd": 0.0}
_client = None
BEDROCK_BUDGET = float(config.get("BEDROCK_BUDGET", "147"))   # 사용자 한도 150달러
ANTHROPIC_BUDGET = float(config.get("ANTHROPIC_BUDGET", "110"))   # 잔액 150달러에서 30달러 넘게 남긴다
_lock, _spent = threading.Lock(), {}
BIZROUTER_MODEL = {"global.anthropic.claude-sonnet-4-6": "anthropic/claude-sonnet-4.6",
                   "claude-sonnet-4-6": "anthropic/claude-sonnet-4.6",
                   "global.anthropic.claude-haiku-4-5-20251001-v1:0": "anthropic/claude-haiku-4.5",
                   "claude-haiku-4-5": "anthropic/claude-haiku-4.5",
                   "global.anthropic.claude-opus-4-6-v1": "anthropic/claude-opus-4.6",
                   "claude-opus-4-6": "anthropic/claude-opus-4.6",
                   "claude-opus-5-5": "anthropic/claude-opus-5.5", "claude-sonnet-5-5": "anthropic/claude-sonnet-5.5",
                   "claude-haiku-5-5": "anthropic/claude-haiku-5.5"}
BIZROUTER_BUDGET = float(config.get("BIZROUTER_BUDGET_KRW", "395000"))   # 사용자 한도 40만원 (2026-11-17 30만원에서 올림). 마지막 호출의 몫 5천원을 남기고 멈춘다
KRW_PER_USD = 1440   # Haiku 4.5 한 번(입력 28, 출력 7토큰)에 0.0908원이 청구된 데서 거꾸로 셈한 값


@lru_cache
def _bedrock():
    import boto3
    from botocore.config import Config
    # 출력 8000토큰에 약 80초(약 100토큰/초)가 걸려 botocore 기본 읽기 제한 60초보다 길게 둔다
    return boto3.Session(profile_name=config.AWS_PROFILE, region_name=config.AWS_REGION).client(
        "bedrock-runtime", config=Config(read_timeout=300, retries={"max_attempts": 10, "mode": "adaptive"}))


def cached(kind, key_parts, make):
    """같은 key_parts 면 outputs/cache/<kind>/ 의 저장본을 돌려준다 → (값, 저장본인가). 저장에 실패해도 값은 돌려준다."""
    if not config.BEDROCK_CACHE:
        return make(), False
    key = hashlib.sha1(json.dumps(key_parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    path = config.OUTPUTS / "cache" / kind / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), True
    out = make()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass
    return out, False


def embed_titan(text):
    """문장 → 벡터 (Titan V2). 모의 모드는 글자 2·3-gram 해시 벡터."""
    dims = config.EMBED_DIMS
    if config.BEDROCK_MOCK:
        v, t = [0.0] * dims, f" {text.lower()} "
        for n in (2, 3):
            for i in range(len(t) - n + 1):
                v[int(hashlib.md5(t[i:i + n].encode("utf-8")).hexdigest(), 16) % dims] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]
    body = json.dumps({"inputText": text[:8000], "dimensions": dims, "normalize": True})

    def call():
        r = _bedrock().invoke_model(modelId=config.EMBED_MODEL_ID, body=body, contentType="application/json",
                                    accept="application/json")
        return json.loads(r["body"].read())["embedding"]
    return cached("embed", [config.EMBED_MODEL_ID, dims, text[:8000]], call)[0]


def parse_json(text):
    """모델 답에서 JSON 부분만 꺼낸다 (```json 감싸기 대응)."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("응답에서 JSON 을 찾지 못했다:\n" + text[:300])
    return json.loads(m.group(0))


class Failed(RuntimeError):
    """모델이 끝까지 답하지 못했다. 그래도 이미 쓴 토큰(usage)은 장부에 남긴다."""

    def __init__(self, message, usage):
        super().__init__(message)
        self.usage = usage


def spent():
    """지금까지 쓴 금액 {"bedrock": 달러, "anthropic": 달러}. 호출마다 outputs/spend.tsv 에 한 줄씩 남긴 것을 더한다.
    장부 파일이 바뀌었으면 다시 읽는다. 여러 실행이 함께 돌 때 서로 쓴 돈을 못 보면 예산 정지선을 넘는다.
    깨진 줄이 있으면 합계를 믿을 수 없으므로 ValueError 를 내고, 고칠 때까지 부를 때마다 다시 읽어 또 멈춘다."""
    path = config.OUTPUTS / "spend.tsv"
    with _lock:
        stamp = path.stat().st_mtime_ns if path.exists() else 0
        if not _spent or _spent.get("_stamp") != stamp:
            got = {"bedrock": 0.0, "anthropic": 0.0}
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines() if path.exists() else [], 1):
                try:
                    _, model, usd = line.split("\t")[:3]
                    got["bedrock" if "anthropic." in model else "anthropic"] += float(usd)
                except ValueError:
                    raise ValueError(f"{path} 의 {n}째 줄이 깨져 쓴 돈을 셀 수 없다. 고칠 때까지 모델을 부르지 않는다: {line[:80]!r}") from None
            _spent.update(got, _stamp=stamp)
        return {"bedrock": _spent["bedrock"], "anthropic": _spent["anthropic"]}


def spent_krw():
    """BizRouter 에 지금까지 쓴 원화. 호출마다 outputs/spend_krw.tsv 에 한 줄씩 남긴 것을 더한다."""
    path = config.OUTPUTS / "spend_krw.tsv"
    with _lock:
        return sum(float(line.split("\t")[2])
                   for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []))


def _record_krw(model, krw):
    with _lock:
        with (config.outputs_dir() / "spend_krw.tsv").open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{model}\t{krw:.4f}\n")


def _record(model, usd):
    with _lock:
        with (config.outputs_dir() / "spend.tsv").open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{model}\t{usd:.6f}\n")


def obj(props, required=None):
    """구조화 출력 스키마용 object (모든 칸 필수, 다른 칸 금지)."""
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


STR = {"type": "string"}


def cost():
    return round(USAGE["usd"], 3)


def ask_json(user, system, schema, effort="medium", max_tokens=16000, model=None, prefix=None):
    """한 번 묻고 스키마 모양의 dict 를 받는다. model 을 주면 그 호출만 다른 모델로 부른다 (비용은 모델별 단가로 센다)."""
    model = model or config.LLM_MODEL
    if config.LLM_BACKEND == "bizrouter":
        return _via_bizrouter(user, system, schema, max_tokens, model, prefix)
    on_aws = "anthropic." in model or config.LLM_BACKEND != "anthropic"
    if config.BEDROCK_MOCK and on_aws:
        raise RuntimeError("모의 모드에서는 LLM 을 부르지 않는다 (BEDROCK_MOCK=0 이거나 ANTHROPIC_API_KEY 가 있어야 한다)")
    key = ["bedrock" if on_aws else "anthropic", model, system, user, schema, effort,
           max_tokens] + ([prefix] if prefix else [])
    billed = [model]

    def call():
        if not on_aws:
            if spent()["anthropic"] >= ANTHROPIC_BUDGET:
                raise RuntimeError(f"Anthropic API 예산 {ANTHROPIC_BUDGET}달러를 다 썼다 (outputs/spend.tsv). 더 부르지 않는다")
            return _anthropic(user, system, schema, effort, max_tokens, model, prefix)
        if spent()["bedrock"] < BEDROCK_BUDGET:
            return _plain(_to_bedrock(model), user, system, schema, max_tokens, prefix)
        if model not in SAME_ON_ANTHROPIC or not config.ANTHROPIC_API_KEY or spent()["anthropic"] >= ANTHROPIC_BUDGET:
            raise RuntimeError(
                f"Bedrock 예산 {BEDROCK_BUDGET}달러를 다 썼고 Anthropic API 로도 이어 갈 수 없다 (outputs/spend.tsv). 더 부르지 않는다")
        billed[0] = SAME_ON_ANTHROPIC[model]
        return _plain(_to_anthropic(billed[0]), user, system, schema, max_tokens, prefix)

    USAGE["calls"] += 1
    try:
        out, hit = cached("llm", key, call)
    except Failed as e:
        _charge(billed[0], e.usage)
        raise
    USAGE["cached"] += hit
    if not hit:
        _charge(billed[0], out["usage"])
    return _shape(out["data"], schema)


def _via_bizrouter(user, system, schema, max_tokens, model, prefix):
    """같은 요청을 BizRouter 로 보낸다. 모델 이름은 BizRouter 의 이름으로 바꾸고, 지시문은 Bedrock 때와 같다 (_plain). effort 는 이 길에서 쓰이지 않는다."""
    mid = model if "/" in model else BIZROUTER_MODEL[model]

    def call():
        if spent_krw() >= BIZROUTER_BUDGET:
            raise RuntimeError(f"BizRouter 예산 {BIZROUTER_BUDGET:,.0f}원에 닿았다 (outputs/spend_krw.tsv). 더 부르지 않는다")
        return _plain(_to_bizrouter(mid, schema), user, system, schema, max_tokens, prefix)

    USAGE["calls"] += 1
    try:
        out, hit = cached("llm", ["bizrouter", mid, system, user, schema, max_tokens] + ([prefix] if prefix else []),
                          call)
    except Failed as e:
        _charge_krw(mid, e.usage)
        raise
    USAGE["cached"] += hit
    if not hit:
        _charge_krw(mid, out["usage"])
    return _shape(out["data"], schema)


def _charge_krw(model, usage):
    for k in ("input", "output", "cache_read", "cache_write"):
        USAGE[k] += usage.get(k, 0)
    krw = usage.get("krw", 0.0)
    USAGE["krw"] = USAGE.get("krw", 0.0) + krw
    USAGE["usd"] += krw / KRW_PER_USD
    _record_krw(model, krw)


def _bizrouter_post(path, body, tries=4):
    import time

    import requests
    for n in range(tries):
        try:
            r = requests.post(f"{config.BIZROUTER_BASE}/{path}", json=body, timeout=600,
                              headers={"Authorization": f"Bearer {config.BIZROUTER_API_KEY}"})
        except (requests.ConnectionError, requests.Timeout):
            if n == tries - 1:
                raise
            time.sleep(5 * (n + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504, 529) and n < tries - 1:
            time.sleep(5 * (n + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"BizRouter {path} 가 {r.status_code} 를 냈다: {r.text[:300]}")
        return r.json()


def _to_bizrouter(model, schema=None):
    """BizRouter 로 한 번 보내는 함수 → (답 글, 쓴 토큰과 원화, 잘렸는지). _plain 이 부른다. prefix 는 캐시 표시 없이 앞에 붙여 보낸다.
    schema 를 주면 구조화 출력(response_format)도 함께 건다. 지시문만으로는 Sonnet 4.6 이 긴 답에서 닫는 괄호가 하나 더 붙은 JSON 을 세 번 내리 냈다."""
    fmt = {"response_format": {"type": "json_schema",
                               "json_schema": {"name": "answer", "strict": True, "schema": schema}}} if schema else {}
    def send(system, prefix, ask, max_tokens, temperature):
        r = _bizrouter_post("chat/completions",
                            {"model": model, "max_tokens": max_tokens, "temperature": temperature, **fmt,
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": (prefix + "\n" if prefix else "") + ask}]})
        u, c = r.get("usage", {}), r["choices"][0]
        return (c["message"].get("content") or "",
                {"input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0),
                 "cache_read": u.get("cache_read_input_tokens", 0),
                 "cache_write": u.get("cache_creation_input_tokens", 0), "krw": float(u.get("cost") or 0)},
                c.get("finish_reason") == "length")
    return send


def embed_bizrouter(texts, dims=512):
    """글 여러 개 → 벡터 여러 개 (BizRouter 의 임베딩 모델). 글마다 저장본을 두고, 저장본이 없는 글만 100개씩 묶어 부른다."""
    model = config.BIZROUTER_EMBED_MODEL
    out, todo = {}, []
    for t in dict.fromkeys(texts):
        path = _embedding_path(model, dims, t)
        if config.BEDROCK_CACHE and path.exists():
            out[t] = json.loads(path.read_text(encoding="utf-8"))
        else:
            todo.append(t)
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        if spent_krw() >= BIZROUTER_BUDGET:
            raise RuntimeError(f"BizRouter 예산 {BIZROUTER_BUDGET:,.0f}원에 닿았다. 더 부르지 않는다")
        r = _bizrouter_post("embeddings", {"model": model, "input": [t[:8000] for t in batch], "dimensions": dims})
        _record_krw(model, float(r.get("usage", {}).get("cost") or 0))
        for t, d in zip(batch, sorted(r["data"], key=lambda d: d["index"])):
            out[t] = d["embedding"]
            path = _embedding_path(model, dims, t)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(d["embedding"]), encoding="utf-8")
    return [out[t] for t in texts]


def _embedding_path(model, dims, text):
    key = hashlib.sha1(json.dumps([model, dims, text[:8000]], ensure_ascii=False).encode()).hexdigest()
    return config.OUTPUTS / "cache" / "embed_bizrouter" / f"{key}.json"


def _charge(model, usage):
    u = {"cache_read": 0, "cache_write": 0, **usage}
    for k in ("input", "output", "cache_read", "cache_write"):
        USAGE[k] += u[k]
    pin, pout = USD_PER_MTOK.get(model, (0, 0))
    usd = ((u["input"] + u["cache_read"] * CACHE_READ + u["cache_write"] * CACHE_WRITE) * pin
           + u["output"] * pout) / 1e6
    USAGE["usd"] += usd
    USAGE["krw"] = USAGE.get("krw", 0.0) + usd * KRW_PER_USD   # m2 의 판정 비용 안전장치·응용 비용이 이 값을 본다 (BizRouter 길과 같은 칸)
    _record(model, usd)


def _escape_inner_quotes(text):
    """깨진 JSON 을 고친다. 문자열 값 안에 이스케이프 없이 들어간 큰따옴표를 \\" 로 바꾸고 (앞이 { [ , : 이거나 뒤가 : , } ] 인 따옴표만 JSON 의 것으로 본다),
    JSON 에 없는 이스케이프를 바로잡는다."""
    out = []
    for i, ch in enumerate(text):
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            before, after = text[:i].rstrip()[-1:], text[i + 1:].lstrip()[:1]
            if before not in "{[,:" and after not in ":,}]":
                out.append("\\")
        out.append(ch)
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", "".join(out))


def _shape(value, schema):
    """스키마가 목록·객체인 자리에 JSON 문자열이 오면 풀어 준다. 예전 Bedrock 도구 입력 방식으로 받은 저장본에 그런 답이 남아 있을 수 있다."""
    kind = schema.get("type")
    if kind in ("array", "object") and isinstance(value, str):
        value = json.loads(value)
    if kind == "object" and isinstance(value, dict):
        return {k: _shape(v, schema.get("properties", {}).get(k, {})) for k, v in value.items()}
    if kind == "array" and isinstance(value, list):
        return [_shape(v, schema.get("items", {})) for v in value]
    return value


def _anthropic(user, system, schema, effort, max_tokens, model, prefix=None):
    global _client
    import anthropic
    _client = _client or anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    with _client.beta.messages.stream(   # 답이 길면 10분을 넘을 수 있어 SDK 가 스트리밍을 요구한다
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user",
                       "content": ([{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}]
                                   if prefix else [])
                       + [{"type": "text", "text": user}]}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default") as stream:
        r = stream.get_final_message()
    usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens,
             "cache_read": r.usage.cache_read_input_tokens or 0,
             "cache_write": r.usage.cache_creation_input_tokens or 0}
    if r.stop_reason in ("refusal", "max_tokens"):
        raise Failed(f"LLM 이 끝까지 답하지 못했다: stop_reason={r.stop_reason}", usage)
    try:
        return {"data": json.loads(next(b.text for b in r.content if b.type == "text")), "usage": usage}
    except (StopIteration, ValueError) as e:
        raise Failed(f"LLM 의 답이 JSON 이 아니었다: {type(e).__name__}", usage) from e


def _to_bedrock(model):
    """Bedrock Converse 로 한 번 보내는 함수 → (답 글, 쓴 토큰, 잘렸는지)."""
    def send(system, prefix, ask, max_tokens, temperature):
        content = ([{"text": prefix}, {"cachePoint": {"type": "default"}}] if prefix else []) + [{"text": ask}]
        r = _bedrock().converse(modelId=model if "anthropic." in model else config.MODEL_ID, system=[{"text": system}],
                                messages=[{"role": "user", "content": content}],
                                inferenceConfig={"maxTokens": max_tokens, "temperature": temperature})
        u = r["usage"]
        return ("".join(b.get("text", "") for b in r["output"]["message"]["content"]),
                {"input": u.get("inputTokens", 0), "output": u.get("outputTokens", 0),
                 "cache_read": u.get("cacheReadInputTokens", 0), "cache_write": u.get("cacheWriteInputTokens", 0)},
                r["stopReason"] == "max_tokens")
    return send


def _to_anthropic(model):
    """Anthropic API 로 한 번 보내는 함수. Bedrock 때와 같은 지시문으로 부르고, 다른 모델로 넘어가는 기능은 쓰지 않는다.
    온도는 맞출 수 없다. Anthropic API 는 이 모델들에도 temperature 를 받지 않는다 (400 'temperature: Extra inputs are not permitted')."""
    def send(system, prefix, ask, max_tokens, temperature):
        global _client
        import anthropic
        _client = _client or anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
        content = ([{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}]
                   if prefix else []) + [{"type": "text", "text": ask}]
        with _client.messages.stream(model=model, max_tokens=max_tokens, system=system,
                                     messages=[{"role": "user", "content": content}]) as stream:
            r = stream.get_final_message()
        return ("".join(b.text for b in r.content if b.type == "text"),
                {"input": r.usage.input_tokens, "output": r.usage.output_tokens,
                 "cache_read": r.usage.cache_read_input_tokens or 0,
                 "cache_write": r.usage.cache_creation_input_tokens or 0},
                r.stop_reason == "max_tokens")
    return send


def _plain(send, user, system, schema, max_tokens, prefix=None):
    """스키마를 지시문 끝에 붙여 보내고 답에서 JSON 을 꺼낸다. send 는 _to_bedrock 이나 _to_anthropic 이 만든 함수다.
    도구 입력을 강제하는 방식은 인용문 속 따옴표를 잘못 이스케이프해 같은 요청이 세 번 깨졌으므로 쓰지 않는다.
    원문에 큰따옴표가 있으면 옮기다가 JSON 을 깨뜨리므로 작은따옴표로 바꿔 쓰게 한다.
    그래도 깨지면 저장하지 않고 두 번까지 다시 묻는다. 쓴 토큰은 모두 센다. 끝내 실패하면 그때까지 쓴 토큰을 Failed 에 실어 보낸다."""
    ask = (f"{user}\n\n다음 JSON 스키마를 따르는 JSON 하나만 출력한다. 설명이나 코드 블록 표시는 붙이지 않는다. "
           "문자열 값 안에는 큰따옴표를 쓰지 않는다. 원문을 옮길 때 원문의 큰따옴표는 작은따옴표로 바꾼다.\n" + json.dumps(schema, ensure_ascii=False))
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "krw": 0.0}
    for attempt in range(3):
        text, used, cut = send(system, prefix, ask, max_tokens, 0 if attempt == 0 else 0.3)
        for k in usage:
            usage[k] += used.get(k, 0)
        if cut:
            raise Failed("LLM 이 끝까지 답하지 못했다: stopReason=max_tokens", usage)
        for candidate in (text, _escape_inner_quotes(text)):
            try:
                return {"data": _shape(parse_json(candidate), schema), "usage": usage}
            except ValueError:
                continue
    raise Failed("모델의 답이 세 번 모두 JSON 이 아니었다", usage)
