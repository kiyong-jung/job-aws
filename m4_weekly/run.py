"""m4 주차 계획: 라운드랩 커리큘럼 생성기(generator/)로 m2 응용 프로젝트와 m3 교육자료를 12주에 놓는다.
  .venv/bin/python -m m4_weekly.run <예시 이름> [--hours 7] [--out 폴더]
예시 이름은 aws_fde, naver_ml_intern. --hours 는 한 사람의 주당 시간 (7·14·21 = 하루 1·2·3시간).
읽는 것: outputs/project/<예시>.local.json·.adapt.json (m2), outputs/materials/<예시>.json (m3). 모델을 부르지 않는다 (Python 규칙만).
끝나면 <out>/curriculum.md (주마다 배울 것·만들 것·산출물) 와 curriculum.json."""
import argparse
import subprocess
import sys
from pathlib import Path

from demo.design.make_team_csv import build as make_csv
from shared import config

GEN = Path(__file__).resolve().parent / "generator"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case")
    ap.add_argument("--hours", type=float, default=7)
    ap.add_argument("--out")
    a = ap.parse_args()
    out = Path(a.out) if a.out else config.outputs_dir() / "weekly" / f"{a.case}.{a.hours:g}"
    make_csv(a.case, out / "team")
    r = subprocess.run([sys.executable, "-E", "-s", "curriculum_generator.py", "--hours-per-week", str(a.hours),
                        "--team-folder", str((out / "team").resolve()), "--output-dir", str(out.resolve())], cwd=GEN)
    if r.returncode not in (0, 3):      # 3 = needs_review: 팀 CSV 로 만든 결과의 정상 상태
        raise SystemExit(f"생성기 실패 (끝 코드 {r.returncode})")
    print(out / "curriculum.md")


if __name__ == "__main__":
    main()
