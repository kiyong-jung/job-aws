# m1_competency/data

| 자리 | 무엇 |
| --- | --- |
| `results/<예시>.json` | 예시 공고 두 건의 m1 결과 (공고 문장, 역량, 근거 문장 번호). 사람 정답과 견준 추출 실험에서 쓴 실행 결과다 |
| `companies.json` | 공고를 모을 회사 목록과 회사마다 모으는 방법 (`python -m m1_competency.collect fetch`) |
| `ncs_*.json` | NCS 능력단위 목록. 정보통신 대분류 1,254개(고용노동부고시 제2025-80호 별표), 인공지능·클라우드 세분류의 능력단위요소·수행준거. 이용 조건은 ncs.go.kr 과 공공데이터포털 표기를 따른다 |
| `resumes/` | 이력서 예시 (가상 인물) |

모은 채용 공고 원문은 회사의 저작물이라 넣지 않았다. `fetch` 로 직접 모으면 `postings.jsonl` 에 쌓이고, `python -m m1_competency.collect` 가 `data/banks/postings.csv`·`posting_lines.csv` 를 만든다.
구직 사이트(사람인, 잡코리아, 원티드, 링크드인 등)는 약관이 자동 수집을 막아 쓰지 않는다.
