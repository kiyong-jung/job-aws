# JOB AWS · 채용 공고 한 건으로 한 학기 커리큘럼 만들기

채용 공고를 넣으면, 그 공고가 원하는 역량을 뽑고, 그 역량을 기르는 프로젝트와 교육자료를 골라 12주 계획으로 놓는다.
단계마다 "공고의 어느 문장 때문에 이것을 골랐나"를 근거 문장으로 남긴다.

**데모:** https://kiyong-jung.github.io/job-aws/ (예시 공고 두 건, 저장된 결과를 다시 보여 준다)

```
공고 ─▶ m1 역량 뽑기 ─┬─▶ m2 프로젝트 고르기 ─┬─▶ m4 12주 계획 ─▶ 데모 화면
                      └─▶ m3 교육자료 고르기 ─┘
```

| 단계 | 하는 일 | 받는 것 → 내는 것 |
|---|---|---|
| m1 역량 뽑기 | 공고를 문장으로 나누고, 역량마다 필수·우대와 근거 문장 번호를 단다 | 공고 글 → 역량 목록 |
| m2 프로젝트 고르기 | 논문 90,239편·GitHub 저장소 21,514개에서 낱말 검색(BM25)으로 1,000개, 뜻 검색(Cohere Rerank)으로 100개를 고르고, AI 판정으로 필수 역량을 가장 많이 다루는 1위를 고른다. 1위가 못 다루는 역량은 다른 프로젝트의 방식을 빌려 채운 응용 프로젝트로 만든다 | 역량 → 1위와 응용 프로젝트 |
| m3 교육자료 고르기 | 교육자료 14,385개에서 같은 방식(BM25 → Rerank → AI 판정)으로 도구·지식 역량을 가르치는 자료를 핵심 1~2개, 보조 3~4개 고른다 | 역량 → 교육자료 |
| m4 12주 계획 | 프로젝트 일과 교육자료를 선수 관계 차례로 주당 시간 안에 놓는다 | 프로젝트 + 교육자료 → 주별 계획 |
| 데모 | 위 결과를 단계마다 근거 문장과 함께 보여 준다 | 예시 공고 → 화면 |

## 빠른 시작

Python 3.12 를 쓴다.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                                   # 모델을 새로 부를 때만 키를 채운다
PYTHONPATH=. .venv/bin/python -m pytest -q              # 시험. 모델과 네트워크를 부르지 않는다
PYTHONPATH=. .venv/bin/python -m demo --port 8770       # 데모: http://127.0.0.1:8770
```

데모는 예시 공고 두 건(AWS Forward Deployed Engineer, 네이버클라우드 ML 엔지니어 체험형 인턴)의 저장된 결과를 다시 보여 준다. 키가 없어도 돈다.
같은 데모를 서버 없는 정적 사이트로 만들려면 `PYTHONPATH=. .venv/bin/python -m demo.export_static site` (GitHub Pages 는 `.github/workflows/pages.yml` 이 main 에 올릴 때마다 만든다).

## 단계별로 돌리기

모든 명령은 레포 맨 위에서 `PYTHONPATH=.` 를 붙여 돌린다. 예시 공고 이름은 `aws_fde`, `naver_ml_intern` 이다.
예시 두 건의 m1·m2·m3 결과는 `m1_competency/data/results/`, `outputs/` 에 들어 있어, m4 와 데모는 모델을 부르지 않고 돈다.

```bash
.venv/bin/python -m m4_weekly.run aws_fde --hours 7              # m4: 12주 계획 (모델 없음)
.venv/bin/python -m m3_materials.pick aws_fde                     # m3: 교육자료 고르기 (모델을 부른다)
.venv/bin/python -m m2_project aws_fde --local                    # m2: 프로젝트 고르기와 응용 (모델을 부른다, 논문 DB 필요)
.venv/bin/python -m m1_competency.extract 공고.txt               # m1: 공고 글 파일 → 역량 (모델을 부른다)
```

- m1 의 추출·평가 실험(사람 정답과 견준 정밀도·재현율, 사람 둘의 일치도)은 `m1_competency/experiment/` 에 있다. 그 폴더의 README 를 본다.
- 모델 호출은 `shared/llm.py` 한 곳에서 한다. `.env` 에 `ANTHROPIC_API_KEY` 가 있으면 Anthropic API, 없으면 AWS Bedrock(`AWS_PROFILE`)으로 부른다. 같은 물음의 답은 `outputs/cache/` 에 저장해 다시 부르지 않는다.
- m2 의 AI 판정은 예시 한 건에 3,500원 안팎이 들었다 (Bedrock 기준). 큰 실행 전에는 한 건으로 먼저 비용을 본다.

## 데이터

| 데이터 | 자리 | 만드는 법 · 출처 |
|---|---|---|
| 채용 공고 원문 | 넣지 않음 | 회사의 저작물이라 싣지 않는다. `python -m m1_competency.collect fetch <회사>` 로 회사 채용 사이트에서 직접 모은다 (회사 목록은 `m1_competency/data/companies.json`) |
| 논문 목록 | `data/papers/` | git 에 없다. `python -m m2_project.library papers` 로 다시 모은다 (2020~2026 탑티어 AI·시스템 학회 본회의 논문. 출처와 이용 조건은 `data/papers/README.md`) |
| GitHub 저장소 목록 | `data/github_repos/` | git 에 없다. `python -m m2_project.repos collect` 로 다시 모은다 (별 200개 이상, `GITHUB_TOKEN` 있으면 빠르다) |
| 면접 질문·교육자료·프로젝트 표 | `data/banks/` | 칸 설명은 `data/banks/_schema.csv` |
| 교육자료 은행 | `m3_materials/data/edu_bank.csv` | 공개 강의 저장소에서 제목·주소·첫 문단 요약만 모았다. 저장소와 라이선스는 `edu_bank_NOTICE.md` |
| 12주 계획 생성기 | `m4_weekly/generator/` | 팀원 가온의 [gaori2952/Round_labcurriculum](https://github.com/gaori2952/Round_labcurriculum) 을 옮겨 넣었다 |

수집기는 robots.txt 를 따르고 한 호스트에 초당 한 번만 묻는다 (`shared/web.py`).

## 폴더

```
shared/          설정(.env 읽기), 모델 부르기와 비용 장부, 표 읽기·쓰기, 웹에서 받기
m1_competency/   공고 → 역량. experiment/ 는 추출·평가 실험, data/results/ 는 예시 두 건의 결과
m2_project/      프로젝트 DB 만들기(library, repos), 찾기(local), 판정(pick), 응용(adapt)
m3_materials/    교육자료 은행 만들기(bank, collect_more), 고르기(pick)
m4_weekly/       12주 계획 (생성기 실행)
demo/            화면 서버(server.py, pipeline.py), 화면(static/), 저장된 예시 결과(data/), 저장본 만들기(design/)
tests/           모듈마다 시험 하나. 모델과 네트워크를 부르지 않는다
outputs/         실행 결과. 예시 두 건의 결과만 올려 두었다
```

## 라이선스

코드는 [Apache License 2.0](LICENSE) 으로 공개한다. 데이터 파일은 각 출처의 이용 조건을 따른다 (출처는 위 표의 README 들에 있다).
데모 화면의 글꼴 Pretendard 는 SIL Open Font License 1.1 이다 (`demo/static/fonts/OFL-Pretendard.txt`).
