# GitHub 저장소 목록

프로젝트 샘플을 웹 검색 없이 찾기 위한 로컬 목록. 조각 파일(`*.jsonl`)은 git 에 올리지 않고 `python -m m2_project.repos collect` 로 다시 만든다.

- 출처: GitHub 검색 API (`api.github.com/search/repositories`) 만. 저장소마다 따로 부르지 않는다.
- 조건: `stars:>=200 pushed:>=2023-01-01 archived:false`, 주제는 `topic:<이름>`.
- 1000개 한도: 한 검색이 1000개 이상이면 만든 날짜(`created:`) 구간을 반으로 쪼개 1000개 아래가 될 때까지 나눈다.
- 칸: full_name, url, description, topics, stars, forks, pushed_at, created_at, license(spdx), language, archived, slices(걸린 주제 목록).
- 폴더: `ai/` (주제가 AI·ML 쪽: machine-learning, llm, pytorch, data-science 등 29개), `cloud/` (클라우드·인프라·MLOps 쪽: kubernetes, docker, aws, serverless, mlops, ray, gpu, spark, airflow 등 20개). 주제가 어느 분야인지는 `repos.py` 의 `AI_TOPICS`·`CLOUD_TOPICS` 에서 정한다.
- 파일: `<분야>/<주제>__<시작일>_<끝일>.jsonl` 한 조각, `done.jsonl` 은 바로 아래 하나(끝난/쪼갠 조각 장부. 조각 이름에서 분야가 정해지므로 폴더를 옮겨도 고칠 것이 없다). 읽기는 `m2_project.repos.load(field=None)` (full_name 으로 중복 제거, slices 합침).
- 두 분야에 걸린 저장소: 조각은 주제 하나의 검색 결과라 같은 저장소가 `ai/` 와 `cloud/` 의 조각에 각각 들어 있다(복사본). `load()` 가 하나로 합치고 `fields`(예 `["ai", "cloud"]`)를 단다. `load("cloud")` 는 cloud 에 한 번이라도 걸린 것 전부, 겹친 것도 포함한다.
- 옮기기: 옛 위치(바로 아래)의 조각은 `python -m m2_project.repos reorganize` 가 `ai/`·`cloud/` 로 옮긴다. `collect` 가 도는 동안은 스스로 멈춘다. 옮기기 전에도 `load()` 는 옛 위치를 함께 읽는다.
- 다시 돌리기: 같은 명령을 또 실행하면 끝난 조각은 건너뛴다. 토큰은 `GITHUB_TOKEN` (환경 변수 또는 .env), 없으면 분당 10번.
- 주제: 아래 표.

수집일, 개수는 `python -m m2_project.repos stats` 결과를 아래에 옮겨 적는다.

## 결과

(수집 진행 중. 끝나면 채움)
