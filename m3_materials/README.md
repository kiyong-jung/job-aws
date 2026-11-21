# m3 교육자료 고르기

m1 역량 가운데 유형이 도구·지식인 것을 가르치는 교육자료를 고른다. 핵심 1~2개, 보조 3~4개. 수행·협업·태도 역량은 m2 프로젝트를 하며 배운다.

```bash
.venv/bin/python -m m3_materials.pick aws_fde       # → outputs/materials/<공고>.json (예시 두 건 결과는 이미 있다)
```

1. **은행.** 팀 표(`data/banks/materials.csv`), 공개 강의 저장소에서 모은 은행(`data/edu_bank.csv`), 보강(`data/bank_additions/`)을 합친다. 공부할 자료가 아닌 줄(따라 만들 논문·저장소, 제품 목록, 노트북 없는 폴더 README)은 거르고, 주소나 제목·요약이 같은 줄은 하나만 남긴다.
2. **후보.** 역량마다 영어 검색어 하나로 BM25 위 1,000개 → Cohere Rerank 3.5 로 뜻이 가까운 차례로 다시 세움 → 역량별 위 100개를 순위 합으로 모아 위 50개.
3. **판정.** 모델이 자료마다 역량별 있음·일부·없음과 근거 구절을 낸다. 구절이 자료 글에 없으면 한 단계 내린다.
4. **고르기.** 점수는 있음 1, 일부 0.5 에 무게(필수 1,000, 우대·나머지 1)를 곱한다. 핵심은 덜 덮인 역량을 가장 많이 채우는 자료부터, 보조는 아직 아무것도 못 덮은 역량을 새로 덮는 자료부터 고른다.

비용은 공고 한 건에 400~560원이었다 (Bedrock, 판정과 Rerank).

은행 다시 만들기
- `python -m m3_materials.bank build`: 공개 면접 질문 은행(Apache-2.0)과 공개 학습 자료 목록 → `data/banks/materials.csv`, `questions.csv`
- `python -I m3_materials/collect_edu.py --work <빈 폴더>`: 공개 강의 저장소 → `data/edu_bank.csv`
- `python -I m3_materials/collect_more.py --work <빈 폴더>`: 허용 라이선스 저장소의 레슨·랩·노트북 → `data/bank_additions/learn_more.csv`

모두 제목, 주소, 첫 문단 요약(300자 이내)만 남기고 본문은 옮기지 않는다. 출처와 라이선스는 `data/README.md`, `data/edu_bank_NOTICE.md`.
