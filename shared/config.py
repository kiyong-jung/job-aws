"""설정. code/ 와 그 위 두 폴더(해커톤/, 그 위)의 .env 를 읽는다. 가까운 폴더의 값이 먼 폴더의 값을 덮고, 환경 변수가 모두를 덮는다.
.env 는 git 에 올리지 않는다. 칸 목록은 .env.example 에 있다."""
import os
from pathlib import Path

ROOT = Path(os.getenv("CURRI_ROOT") or Path(__file__).resolve().parents[1])
# 데이터의 자리. 경로는 여기서만 정한다
BANKS = ROOT / "data" / "banks"   # 은행 표. 여러 모듈과 팀원이 함께 읽어 한곳에 둔다. 엑셀로 열린다
COMPETENCY_DATA = ROOT / "m1_competency" / "data"   # 공고 원본(postings/), 이력서 원본, NCS 목록
PROJECT_DATA = ROOT / "m2_project" / "data"   # 손 정답(cases/), 프로젝트 은행 보강, 팀 조건
MATERIALS_DATA = ROOT / "m3_materials" / "data"   # 교육자료 은행의 원천 파일과 보강
OUTPUTS = Path(os.getenv("OUTPUTS_DIR") or ROOT / "outputs")


def _env_file(path):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return dict((k.strip(), v.strip())
                for k, v in (s.split("=", 1) for s in lines if "=" in s and not s.startswith("#")))


_ENV = {}
for _dir in (ROOT,):
    _ENV.update({k: v for k, v in _env_file(_dir / ".env").items() if v})
_ENV.update(os.environ)


def get(key, default=None):
    return _ENV.get(key) or default


AWS_REGION = get("AWS_REGION", "ap-northeast-2")
AWS_PROFILE = get("AWS_PROFILE")
MODEL_ID = get("MODEL_ID", "global.anthropic.claude-sonnet-4-6")
EMBED_MODEL_ID = get("EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBED_DIMS = int(get("EMBED_DIMS", "512"))
BEDROCK_MOCK = get("BEDROCK_MOCK", "1") == "1"
# 같은 요청의 답을 outputs/cache/ 에 두고 다시 쓴다. 같은 요청을 다시 돌리면 비용이 들지 않는다
BEDROCK_CACHE = get("BEDROCK_CACHE", "1") == "1"
# 키가 있으면 Anthropic API, 없으면 Bedrock Converse 로 같은 요청을 보낸다
ANTHROPIC_API_KEY = get("ANTHROPIC_API_KEY")
# 실험과 개발 중의 모델 호출은 BizRouter 로 보낸다 (사용자 지시 2026-11-15, 한도 30만원). Bedrock 으로 돌리려면 LLM_BACKEND=bedrock
BIZROUTER_API_KEY = get("BIZROUTER_API_KEY")
BIZROUTER_BASE = get("BIZROUTER_BASE", "https://bizrouter.ai/api/v1")
BIZROUTER_EMBED_MODEL = get("BIZROUTER_EMBED_MODEL", "openai/text-embedding-3-small")
LLM_BACKEND = get("LLM_BACKEND", "bizrouter" if BIZROUTER_API_KEY else "anthropic" if ANTHROPIC_API_KEY else "bedrock")
LLM_MODEL = get("LLM_MODEL", "claude-opus-5-5")


def outputs_dir():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    return OUTPUTS
