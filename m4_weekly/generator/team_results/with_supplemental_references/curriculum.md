# genkit-ai/genkit 기반 프로토타입 구현과 검증 — 주차별 커리큘럼

**상태:** `needs_review` | **기간:** 12주 × 7.0시간/주

**목표:** 원본 프로젝트의 기능 한 가지를 구현하고 재현 가능한 검증 결과를 만든다.

## 생성 흐름

선정 프로젝트 CSV + 선정 교육자료 CSV → 작업·역량 확인 → 핵심/참고 교육자료 매칭 → 학습·작업 순서 정렬 → 주차 배분 → 검증

## 배정 결과

- 포함 작업: P01, P02, P03, P04, P05, P06
- 프로젝트 구현: 70.0시간 / 학습: 10.5시간
- 선택 교육자료: LRN624bcb0ae0, LRN6a568bbf93, E365c3dd16b, E03732779fa, E564ad08f67, E2a4fa23ce7
- 제외된 확장 작업: 없음

## 작업안과 시간 추정

CSV의 차용 역량과 자료 인용문을 바탕으로 만든 축소 실습안입니다. P번호는 생성기가 제안한 작업이며, 원본 W번호는 출처 참조로 보존했습니다.
구현 추정은 예제·설계 5시간, 기능 하나 구현 16시간, 재현 검증 7시간, 독립 확장 기능당 14시간입니다. 학습 추정은 관련 부분 한 번 읽기 60분, 튜토리얼 90분, 노트북 실습 120분, 워크숍 실습 180분입니다. 정확한 수강 구간과 시간은 확인이 필요합니다.

## 팀 추천 교육자료

- 핵심 · [Evaluate your ADK agent using Vertex AI Gen AI Evaluation service](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaluating_adk_agent.ipynb) · C21 파운데이션 모델 개념 및 활용 이해: 일부; C43 Eval 프레임워크 활용: 있음; C44 에이전트 툴링 활용: 일부
- 핵심 · [Production Architecture](https://github.com/crewAIInc/crewAI/blob/main/docs/edge/en/concepts/production-architecture.mdx) · C21 파운데이션 모델 개념 및 활용 이해: 일부; C44 에이전트 툴링 활용: 있음
- 보조 · [Recommended Technologies](https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/UI-UX/recommended-technologies.md) · C51 React: 있음; C52 TypeScript: 있음
- 보조 · [Module: Build a Multi-Region Serverless Application for Resilience and High Availability](https://github.com/aws-samples/aws-serverless-workshops/tree/master/MultiRegion) · C57 AWS 서비스 활용: 있음; C58 분산 시스템 개념 이해: 일부
- 보조 · [Learn Go with Tests](https://quii.gitbook.io/learn-go-with-tests) · C54 Go: 있음
- 보조 · [Evaluate and Optimize Prompt Template Design for Better Results](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaltask_approach/prompt_engineering_gen_ai_evaluation_service_sdk.ipynb) · C43 Eval 프레임워크 활용: 있음; C53 Python: 일부

## 주차별 계획

### 1주차 — 6시간 50분 (주당 상한 7.0시간)

주간 목표 · Production Architecture / genkit-ai/genkit 예제를 실행하고 최소 기능의 입력·출력 정의 (준비: 추천 교육자료에 없는 C01 AI 기반 프로덕션 시스템 설계 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) / Recommended Technologies
학습 110분 · 구현 300분 · 실제 학습 비중 26.8% (권장 학습 비중 60%)

- **학습** (1시간 30분): [Production Architecture](https://github.com/crewAIInc/crewAI/blob/main/docs/edge/en/concepts/production-architecture.mdx) — 역량 입문-C21, C44
  - 학습 구간 · The Architecture → The Flow Class → Crews as Units of Work
  - P01 작업 전 선수학습 · Flow가 상태를 받아 Crew에 넘기는 예제를 읽고, 프로젝트에서 호출 흐름과 도구의 책임을 한 장에 정리합니다. · 근거 C21: Best practices for building production-ready AI applications with CrewAI; C44: Fast and Flexible Multi-Agent Automation Framework · concepts · Best practices for building production-ready AI applications with CrewAI
- **구현** (5시간): P01 · genkit-ai/genkit 예제를 실행하고 최소 기능의 입력·출력 정의 (준비: 추천 교육자료에 없는 C01 AI 기반 프로덕션 시스템 설계 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) → 산출물: 예제 실행 기록과 기능 명세 1장
  - 선행 작업 · 선행 작업 지정 없음
  - 필요한 선수지식 · 입문-C21, C44
  - 완료 기준 · 같은 입력으로 예제를 재실행하고 예상 출력과 비교한다.
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C01 AI 기반 프로덕션 시스템 설계; C21 파운데이션 모델 개념 및 활용 이해
- **학습** (20분): [Recommended Technologies](https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/UI-UX/recommended-technologies.md) — 역량 C51, C52
  - 학습 구간 · TypeScript → Guidance on types and interfaces
  - P02 작업 전 선수학습 · 타입과 인터페이스 예제를 비교하고, 프로젝트의 입력·응답 구조를 TypeScript 타입으로 정의합니다. · 근거 C51: React - Quick note on create-react-app - Documentation & Using older React coding patterns - Best Practices to Organize; C52: TypeScript - Guidance on types and interfaces

### 2주차 — 6시간 50분 (주당 상한 7.0시간)

주간 목표 · Recommended Technologies / 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)
학습 40분 · 구현 370분 · 실제 학습 비중 9.8% (권장 학습 비중 60%)

- **학습** (40분): [Recommended Technologies](https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/UI-UX/recommended-technologies.md) — 역량 C51, C52
  - 학습 구간 · TypeScript → Guidance on types and interfaces
  - P02 작업 전 선수학습 · 타입과 인터페이스 예제를 비교하고, 프로젝트의 입력·응답 구조를 TypeScript 타입으로 정의합니다. · 근거 C51: React - Quick note on create-react-app - Documentation & Using older React coding patterns - Best Practices to Organize; C52: TypeScript - Guidance on types and interfaces
- **구현** (6시간 10분): P02 · 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) (이어 진행)
  - 선행 작업 · P01
  - 필요한 선수지식 · 입문-C21, C44, C52
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C14 검색 파이프라인(RAG) 설계 및 개발; C45 RAG 파이프라인 구축 및 운영; C42 AI 에이전트 개발

### 3주차 — 6시간 50분 (주당 상한 7.0시간)

주간 목표 · 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)
학습 0분 · 구현 410분 · 실제 학습 비중 0.0% (권장 학습 비중 60%)

- **구현** (6시간 50분): P02 · 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) (이어 진행)
  - 선행 작업 · P01
  - 필요한 선수지식 · 입문-C21, C44, C52
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C14 검색 파이프라인(RAG) 설계 및 개발; C45 RAG 파이프라인 구축 및 운영; C42 AI 에이전트 개발

### 4주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) / 프로토타입의 성공·실패 사례를 재실행하고 사용법 작성 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 40%)

- **구현** (3시간): P02 · 검색 파이프라인(RAG) 설계 및 개발 기능 하나를 샘플 입력으로 구현 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) → 산출물: 실행 가능한 프로토타입과 입력 예제
  - 선행 작업 · P01
  - 필요한 선수지식 · 입문-C21, C44, C52
  - 완료 기준 · 정상 입력 2건과 빈 입력 1건의 결과를 기록한다.
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C14 검색 파이프라인(RAG) 설계 및 개발; C45 RAG 파이프라인 구축 및 운영; C42 AI 에이전트 개발
- **구현** (3시간 40분): P03 · 프로토타입의 성공·실패 사례를 재실행하고 사용법 작성 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) (이어 진행)
  - 선행 작업 · P02
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C14 검색 파이프라인(RAG) 설계 및 개발; C45 RAG 파이프라인 구축 및 운영; C42 AI 에이전트 개발

### 5주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 프로토타입의 성공·실패 사례를 재실행하고 사용법 작성 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) / 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 40%)

- **구현** (3시간 20분): P03 · 프로토타입의 성공·실패 사례를 재실행하고 사용법 작성 (준비: 추천 교육자료에 없는 C14 검색 파이프라인(RAG) 설계 및 개발, C45 RAG 파이프라인 구축 및 운영, C42 AI 에이전트 개발 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) → 산출물: 검증 스크립트, 결과표, 실행 안내서
  - 선행 작업 · P02
  - 완료 기준 · 새 환경에서 안내서대로 실행하고 테스트 결과를 재현한다.
  - 작업 근거 · genkit-ai/genkit · https://github.com/genkit-ai/genkit · C14 검색 파이프라인(RAG) 설계 및 개발; C45 RAG 파이프라인 구축 및 운영; C42 AI 에이전트 개발
- **구현** (3시간 20분): P04 · 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) (이어 진행)
  - 선행 작업 · P03
  - 작업 근거 · open-hand/choerodon · https://github.com/open-hand/choerodon · C31 CI/CD 파이프라인 구현 및 운영

### 6주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인)
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 40%)

- **구현** (6시간 40분): P04 · 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) (이어 진행)
  - 선행 작업 · P03
  - 작업 근거 · open-hand/choerodon · https://github.com/open-hand/choerodon · C31 CI/CD 파이프라인 구현 및 운영

### 7주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) / Evaluate your ADK agent using Vertex AI Gen AI Evaluation service / 프로토타입 평가 질문과 채점 코드 연결
학습 120분 · 구현 280분 · 실제 학습 비중 30.0% (권장 학습 비중 40%)

- **구현** (4시간): P04 · 테스트 자동 실행과 실패 시 배포 중단 절차 구성 (준비: 추천 교육자료에 없는 C31 CI/CD 파이프라인 구현 및 운영 항목은 프로젝트 문서에서 관련 예제를 찾아 확인) → 산출물: CI 설정과 성공·실패 로그
  - 선행 작업 · P03
  - 완료 기준 · 실패하는 테스트를 넣고 다음 단계가 중단되는지 확인한다.
  - 작업 근거 · open-hand/choerodon · https://github.com/open-hand/choerodon · C31 CI/CD 파이프라인 구현 및 운영
- **학습** (2시간): [Evaluate your ADK agent using Vertex AI Gen AI Evaluation service](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaluating_adk_agent.ipynb) — 역량 입문-C21, C43, 입문-C44
  - 학습 구간 · Prepare Agent Evaluation dataset → Evaluate final response
  - P05 작업 전 선수학습 · 평가 입력과 응답 지표를 확인하고, 프로젝트 질문 한 건으로 같은 형식의 입력과 채점 기준을 만듭니다. · 근거 C21: Agent Development Kit (ADK in short) is a flexible and modular open source framework for developing and deploying AI agents.; C43: using Vertex AI Gen AI Evaluation provides a toolkit of quality controlled and explainable methods and metrics to evaluate any generat; C44: Agent Development Kit (ADK in short) is a flexible and modular open source framework for developing and deploying AI agents.
- **구현** (40분): P05 · 프로토타입 평가 질문과 채점 코드 연결 (이어 진행)
  - 선행 작업 · P03
  - 필요한 선수지식 · C43
  - 작업 근거 · FareedKhan-dev/production-grade-agentic-system · https://github.com/FareedKhan-dev/production-grade-agentic-system · C43 Eval 프레임워크 활용

### 8주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 프로토타입 평가 질문과 채점 코드 연결
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 40%)

- **구현** (6시간 40분): P05 · 프로토타입 평가 질문과 채점 코드 연결 (이어 진행)
  - 선행 작업 · P03
  - 필요한 선수지식 · C43
  - 작업 근거 · FareedKhan-dev/production-grade-agentic-system · https://github.com/FareedKhan-dev/production-grade-agentic-system · C43 Eval 프레임워크 활용

### 9주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · 프로토타입 평가 질문과 채점 코드 연결
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 25%)

- **구현** (6시간 40분): P05 · 프로토타입 평가 질문과 채점 코드 연결 → 산출물: 평가 질문 5개와 결과표
  - 선행 작업 · P03
  - 필요한 선수지식 · C43
  - 완료 기준 · 두 실행의 점수를 비교하고 실패 사례를 설명한다.
  - 작업 근거 · FareedKhan-dev/production-grade-agentic-system · https://github.com/FareedKhan-dev/production-grade-agentic-system · C43 Eval 프레임워크 활용

### 10주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · Evaluate and Optimize Prompt Template Design for Better Results / Module: Build a Multi-Region Serverless Application for Resilience and High Availability / AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검
학습 300분 · 구현 100분 · 실제 학습 비중 75.0% (권장 학습 비중 25%)

- **보완학습** (2시간): [Evaluate and Optimize Prompt Template Design for Better Results](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaltask_approach/prompt_engineering_gen_ai_evaluation_service_sdk.ipynb) — 역량 C43, 입문-C53
  - 학습 구간 · CSV 인용문 기준 학습 범위 · Generative AI on Google Cloud evaltask approach (원문 절 미확인)
  - P05 작업 완료 후 보완학습 · 표시된 범위에서 인용문과 관련된 내용을 찾고, 예제 한 건을 프로젝트에 적용할 방법을 기록합니다. · 근거 C43: use the Vertex AI Python SDK for Gen AI Evaluation Service for Prompt Engineering and Prompt Evaluation; C53: use the Vertex AI Python SDK for Gen AI Evaluation Service
- **학습** (3시간): [Module: Build a Multi-Region Serverless Application for Resilience and High Availability](https://github.com/aws-samples/aws-serverless-workshops/tree/master/MultiRegion) — 역량 C57, 입문-C58
  - 학습 구간 · CSV 인용문 기준 학습 범위 · Wild Rydes Serverless Workshops MultiRegion (원문 절 미확인)
  - P06 작업 전 선수학습 · 표시된 범위에서 인용문과 관련된 내용을 찾고, 예제 한 건을 프로젝트에 적용할 방법을 기록합니다. · 근거 C57: you will use Amazon API Gateway, AWS Lambda, Amazon DynamoDB and a variety of other AWS services; C58: build a Multi-Region Serverless Application for Resilience and High Availability
- **구현** (1시간 40분): P06 · AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검 (이어 진행)
  - 선행 작업 · P03
  - 필요한 선수지식 · C57
  - 작업 근거 · cloudcomponents/cdk-constructs · https://github.com/cloudcomponents/cdk-constructs · C57 AWS 서비스 활용

### 11주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검
학습 0분 · 구현 400분 · 실제 학습 비중 0.0% (권장 학습 비중 25%)

- **구현** (6시간 40분): P06 · AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검 (이어 진행)
  - 선행 작업 · P03
  - 필요한 선수지식 · C57
  - 작업 근거 · cloudcomponents/cdk-constructs · https://github.com/cloudcomponents/cdk-constructs · C57 AWS 서비스 활용

### 12주차 — 6시간 40분 (주당 상한 7.0시간)

주간 목표 · AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검 / Learn Go with Tests
학습 60분 · 구현 340분 · 실제 학습 비중 15.0% (권장 학습 비중 25%)

- **구현** (5시간 40분): P06 · AWS 배포 구성을 코드로 정의하고 생성된 템플릿 점검 → 산출물: 인프라 템플릿과 설정 검증 기록
  - 선행 작업 · P03
  - 필요한 선수지식 · C57
  - 완료 기준 · 템플릿 생성 성공과 필수 리소스의 존재를 확인한다.
  - 작업 근거 · cloudcomponents/cdk-constructs · https://github.com/cloudcomponents/cdk-constructs · C57 AWS 서비스 활용
- **보완학습** (1시간): [Learn Go with Tests](https://quii.gitbook.io/learn-go-with-tests) — 역량 C54
  - 학습 구간 · CSV 인용문 기준 학습 범위 · 2. Learn one programming language (원문 절 미확인)
  - 프로젝트 작업 완료 후 별도 보완학습 · 표시된 범위에서 인용문과 관련된 내용을 찾고, 예제 한 건을 프로젝트에 적용할 방법을 기록합니다. · 근거 C54: Learn Go with Tests

## 교육자료 연결 근거

| 자료/구간 | 구분 | 역량 | 학습시간 | 원본 근거 |
|---|---|---|---:|---|
| [Production Architecture](https://github.com/crewAIInc/crewAI/blob/main/docs/edge/en/concepts/production-architecture.mdx) | core | 입문-C21, C44 | 1시간 30분 | C21: Best practices for building production-ready AI applications with CrewAI; C44: Fast and Flexible Multi-Agent Automation Framework · concepts · Best practices for building production-ready AI applications with CrewAI |
| [Recommended Technologies](https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/UI-UX/recommended-technologies.md) | reference | C51, C52 | 1시간 | C51: React - Quick note on create-react-app - Documentation & Using older React coding patterns - Best Practices to Organize; C52: TypeScript - Guidance on types and interfaces |
| [Evaluate your ADK agent using Vertex AI Gen AI Evaluation service](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaluating_adk_agent.ipynb) | core | 입문-C21, C43, 입문-C44 | 2시간 | C21: Agent Development Kit (ADK in short) is a flexible and modular open source framework for developing and deploying AI agents.; C43: using Vertex AI Gen AI Evaluation provides a toolkit of quality controlled and explainable methods and metrics to evaluate any generat; C44: Agent Development Kit (ADK in short) is a flexible and modular open source framework for developing and deploying AI agents. |
| [Module: Build a Multi-Region Serverless Application for Resilience and High Availability](https://github.com/aws-samples/aws-serverless-workshops/tree/master/MultiRegion) | reference | C57, 입문-C58 | 3시간 | C57: you will use Amazon API Gateway, AWS Lambda, Amazon DynamoDB and a variety of other AWS services; C58: build a Multi-Region Serverless Application for Resilience and High Availability |
| [Evaluate and Optimize Prompt Template Design for Better Results](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/evaluation/evaltask_approach/prompt_engineering_gen_ai_evaluation_service_sdk.ipynb) | reference | C43, 입문-C53 | 2시간 | C43: use the Vertex AI Python SDK for Gen AI Evaluation Service for Prompt Engineering and Prompt Evaluation; C53: use the Vertex AI Python SDK for Gen AI Evaluation Service |
| [Learn Go with Tests](https://quii.gitbook.io/learn-go-with-tests) | reference | C54 | 1시간 | C54: Learn Go with Tests |

## 요청한 보조자료

- Evaluate and Optimize Prompt Template Design for Better Results (E564ad08f67) · P05 작업 완료 후 보완학습 · 2시간
- Learn Go with Tests (E2a4fa23ce7) · 프로젝트 작업 완료 후 별도 보완학습 · 1시간
