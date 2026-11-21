"""⑤ 12주 계획: 라운드랩 커리큘럼 생성기(github.com/gaori2952/Round_labcurriculum)를 공고·공부 시간마다 돌려 데모 저장본으로 둔다 (사용자 11/21).
  PYTHONPATH=. .venv/bin/python demo/design/build_curriculum.py <예시> <생성기 저장소 폴더>
→ demo/data/<예시>.curriculum.<주당 시간>.json (생성기의 curriculum.json 그대로, 주당 7·14·21시간 = 하루 1·2·3시간).
입력 CSV 는 make_team_csv.py 가 만든다. 생성기는 옵션 없이 돌린다 (Python 규칙만, AWS 호출 0회). 끝 코드 3 은 needs_review (팀 CSV 결과의 정상 상태)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from demo.design.make_team_csv import build as make_csv

DATA = Path(__file__).resolve().parents[1] / "data"
HOURS = (7, 14, 21)


def build(case, repo):
    commit = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%h %ci"], capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        team = Path(tmp) / "team"
        make_csv(case, team)
        for h in HOURS:
            out = Path(tmp) / f"out{h}"
            r = subprocess.run([sys.executable, "-E", "-s", "curriculum_generator.py", "--hours-per-week", str(h), "--team-folder", str(team), "--output-dir", str(out)],
                               cwd=repo, capture_output=True, text=True)
            if r.returncode not in (0, 3):
                raise SystemExit(f"{case} {h}시간: 생성기 실패 {r.returncode}\n{r.stderr[-800:]}")
            d = json.loads((out / "curriculum.json").read_text(encoding="utf-8"))
            d["generator_commit"] = commit
            (DATA / f"{case}.curriculum.{h}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(case, h, d["status"], f"{d['summary']['scheduled_hours']}시간 (공부 {d['summary']['learning_hours']} · 프로젝트 {d['summary']['implementation_hours']})")


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]))
