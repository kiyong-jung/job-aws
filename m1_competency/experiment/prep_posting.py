"""새 공고를 postings/ 에 넣기 전에 정리한다.

  python prep_posting.py --raw raw/catchtable.txt --out postings/catchtable_agent.txt
  python prep_posting.py --images raw/voyagerx1.png raw/voyagerx2.png --out postings/voyagerx_intern.txt
  python prep_posting.py --raw raw/krafton.txt --role "AI Research" --out postings/krafton_ai.txt
출력 파일을 눈으로 확인한 뒤 run_experiment.py 의 POSTINGS 에 추가한다. (raw/ 는 git 제외)
"""
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.normalize import format_posting, check

load_dotenv(Path(__file__).resolve().parent / ".env")
MODEL = "global.anthropic.claude-sonnet-4-6"

ap = argparse.ArgumentParser()
ap.add_argument("--raw"); ap.add_argument("--images", nargs="*", default=[])
ap.add_argument("--role", default=""); ap.add_argument("--out", required=True)
a = ap.parse_args()
raw = Path(a.raw).read_text(encoding="utf-8") if a.raw else ""
text = format_posting(MODEL, raw, a.images, a.role)
Path(a.out).write_text(text + "\n", encoding="utf-8")
print(text, "\n")
for m in check(text, raw):
    print(m)
print(f"\n저장: {a.out}" + ("  (이미지 입력은 원문 대조가 안 되니 원본과 눈으로 비교)" if a.images else ""))
