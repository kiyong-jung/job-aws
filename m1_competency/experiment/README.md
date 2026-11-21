# m1 추출·평가 실험

공고를 문장(S01~)으로 나누고 모델·방법별로 역량을 뽑아, 사람이 만든 정답과 견준다.

```bash
pip install -r requirements.txt          # pandas, boto3, openai, python-dotenv
cp ../../.env .env                       # Bedrock(AWS) 또는 OPENAI_API_KEY
python run_experiment.py                 # 공고 × 모델 × 방법 × 반복 → outputs/results_<날짜>.csv (설정은 파일 맨 위)
python score.py outputs/results_<날짜>.csv
```

| 파일 | 하는 일 |
|---|---|
| `prep_posting.py` | 새 공고를 `[구역]` 아래 한 줄 한 항목으로 정리 |
| `agree.py` | 사람 둘이 따로 만든 정답 → 일치도(κ, 엄격·관대 F1) |
| `run_experiment.py` | 추출 실행. 같은 요청은 `cache/` 에 두고 다시 부르지 않는다 |
| `score.py` | 엄격·관대 정밀도·재현율·F1, 누락·지어냄·쪼갬 |
| `repro.py` | 보조: 같은 입력을 다시 뽑아 흔들림을 재고, AI 채점과 사람 판정의 일치율을 함께 적는다 |

폴더: `postings/` 정리한 공고, `gold/` 사람 정답, `prompts/` 지시문, `standards/` NCS 능력단위 목록, `src/` 문장 나누기·모델 부르기·이름 비교.

평가 원칙
- 정답은 AI 가 아니라 사람 둘이 따로 만들고 합의한다 (SkillSpan, NAACL 2022).
- 재현율과 정밀도를 엄격·관대 두 기준으로 함께 본다. 사람끼리도 엄격 F1 이 0.5 대다.
- 짝 맞추기 판단은 사람이 하고, AI 채점은 사람 판정과의 일치율을 함께 적는 보조로만 쓴다.
