# m4 주차 학습 계획

m2 의 응용 프로젝트와 m3 의 교육자료를 받아 12주 계획으로 놓는다. 계획은 `generator/` 의 라운드랩 커리큘럼 생성기가 짠다.
생성기는 팀원 가온의 저장소 [gaori2952/Round_labcurriculum](https://github.com/gaori2952/Round_labcurriculum) 을 그대로 옮긴 것이다 (판 3b11559). 생성기 사용법은 `generator/README.md`.

```bash
.venv/bin/python -m m4_weekly.run aws_fde --hours 7       # → outputs/weekly/aws_fde.7/curriculum.md
```

- `run.py` 는 앞 단계 결과를 생성기의 입력 CSV 두 개(선정 프로젝트, 선정 교육자료)로 바꾸고(`demo/design/make_team_csv.py`) 생성기를 돌린다.
- 생성기는 Python 규칙만으로 시간을 재고 선수 관계 차례로 주에 놓는다. 모델을 부르지 않는다 (`--bedrock-model` 을 줄 때만 선수학습 분석에 모델을 쓴다).
- 결과의 `status` 가 `needs_review` 인 것은 팀 CSV 로 만든 결과의 정상 상태다 (사람이 한 번 보라는 표시).
