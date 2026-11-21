# m3_materials/data

| 자리 | 무엇 |
| --- | --- |
| `blog_bank.jsonl` | 회사 기술 블로그 글 1,485개 (제목, 주소, 요약 200자) |
| `course_bank.json`, `tutorial_bank.json` | 대학 강의와 학회 튜토리얼 목록 |
| `bank_additions/materials_new.jsonl` | 손으로 모은 보강 133행. **아직 은행 표에 얹는 코드가 없다** |
| `bank_additions/gap_materials.csv` | 은행에 없던 역량 5개를 채우려고 모은 자료 60행. `pick.py` 가 불러올 때 합친다 (출처는 아래) |
| `bank_additions/learn_more.csv` | 허용 라이선스 저장소의 레슨·랩·노트북·문서 튜토리얼 5,555행. `collect_more.py` 가 모으고 `pick.py` 가 불러올 때 합친다 (출처는 아래) |
| `bank_additions/materials_minutes_sample.jsonl` | 자료 50개의 공부 시간 표본 |

이 파일들로 만든 표는 `../../data/banks/materials.csv`(교육자료 은행 9,723행, `minutes`·`concepts` 칸은 아직 비어 있다)와 `questions.csv`(면접 질문 은행 1,164문항, 답 글이 교육자료 은행에 들어간다)다.

## 은행 표 materials 출처 (data/banks/materials.csv)

`python -m m3_materials.bank build` 가 아래 공개 목록에서 자료를 모아 한 파일로 만든다. 줄마다 출처(`source`), 원래 저장소(`repo`), 라이선스(`license`)를 남긴다.
제목, 주소, 한 줄 설명만 옮기고 자료 본문은 옮기지 않는다. 같은 주소는 먼저 나온 하나만 둔다. 라이선스 파일이 없거나 비영리·카피레프트인 목록은 넣지 않았다.

| source | 저장소 | 라이선스 | 자료 수 |
| --- | --- | --- | --- |
| interview-answers | 질문 은행의 답 글 링크 (제목, 주소, 그 글이 답하는 은행 질문) | Apache-2.0, Outcome School | 186 |
| llm-apps | https://github.com/Shubhamsaboo/awesome-llm-apps | Apache-2.0 | 123 |
| llm-course | https://github.com/mlabonne/llm-course | Apache-2.0 | 132 |
| applied-ml | https://github.com/eugeneyan/applied-ml | MIT | 525 |
| awesome-llm | https://github.com/Hannibal046/Awesome-LLM | CC0-1.0 | 325 |
| diffusion | https://github.com/diff-usion/Awesome-Diffusion-Models | MIT | 2674 |
| llm-resources | https://github.com/WangRongsheng/awesome-LLM-resources | Apache-2.0 | 562 |
| llm-strawberry | https://github.com/hijkzzz/Awesome-LLM-Strawberry | Apache-2.0 | 220 |
| llm-reasoning | https://github.com/atfortes/Awesome-LLM-Reasoning | MIT | 133 |
| world-models | https://github.com/knightnemo/Awesome-World-Models | BSD-3-Clause | 555 |
| ai-agents-2026 | https://github.com/caramaschiHG/awesome-ai-agents-2026 | CC0-1.0 | 254 |
| ai-agents-list | https://github.com/jim-schwoebel/awesome_ai_agents | Apache-2.0 | 1533 |
| embodied | https://github.com/zchoi/Awesome-Embodied-Robotics-and-Agent | Apache-2.0 | 158 |
| rag | https://github.com/Danielskry/Awesome-RAG | CC0-1.0 | 107 |
| agent-papers | https://github.com/tmgthb/Autonomous-Agents | MIT | 459 |
| game-ai | https://github.com/datamllab/awesome-game-ai | MIT | 9 |
| tool-learning | https://github.com/thunlp/ToolLearningPapers | Apache-2.0 | 48 |

넣지 않은 목록: aikorea/awesome-rl, terryum/awesome-deep-learning-papers 등 라이선스 파일이 없는 목록, e2b-dev/awesome-ai-agents(CC BY-NC-SA), xlite-dev/Awesome-LLM-Inference(GPL-3.0), NirDiamant/RAG_Techniques(별도 약관), slavakurilyak/awesome-ai-agents(본문이 마크다운 링크가 아니라 읽지 못함).

### 학회 튜토리얼, 대학 강의, 기술 블로그 (2026-11-08 추가)

| source | 어디서 | 자료 수 |
| --- | --- | --- |
| tutorial | ACL, EMNLP, NAACL, EACL, NeurIPS, ICML, CVPR, ECCV, ICCV, KDD, SIGIR 2024~2026 공식 튜토리얼 페이지 (`m3_materials/data/tutorial_bank.json`). AAAI 는 robots.txt 의 요청 간격(12시간) 때문에, ICLR 은 튜토리얼이 없어 빠졌다 | 362 |
| course | 대학 공식 강의 페이지와 YouTube 강의 재생목록 (`m3_materials/data/course_bank.json`). YouTube 는 robots.txt 가 허용하는 공개 페이지만 한 번씩 읽었다 | 93 |
| blog:* | 회사 기술·연구 블로그의 공개 RSS·사이트맵 (`m3_materials/data/blog_bank.jsonl`). 제목, 주소, 요약 200자만 쓴다. Upstage 는 robots.txt 가 수집을 막아 넣지 않았다 | 1265 |

블로그별: kakao 150, line 150, lg-ai-research 150, google-research 150, huggingface 150, openai 150, microsoft-research 100, nvidia 100, toss 20, naver-d2 20, aws-ml 20, woowahan 10, daangn 10, moloco 10, hyperconnect 10, aws-korea 10, netflix 10, pinterest 10, naver-cloud 10, coupang 10, meta-engineering 9, sk-devocean 6

### 보강 자료 (bank_additions/gap_materials.csv, 2026-11-19)

`m3_materials/data/edu_bank_NOTICE.md` 와 같은 규칙을 따른다. 제목, 주소, 첫 문단 요약(300자 이내)만 저장하고 본문은 옮기지 않는다.
요약은 그 쪽의 첫 문단·소개 글에서 따왔다. 강의 PDF 는 첫 쪽의 개요와 목차 줄에서 따왔다. 저작권이 있는 쪽(NVIDIA 문서, 블로그, 강의 자료)도 제목·주소·짧은 요약만 넣었다.

모으기: 2026-11-19. UA `Mozilla/5.0 (research collector)`, robots.txt 확인, 호스트당 1.1초 간격, TLS 검사 켬. 받은 파일은 scratch 폴더에만 두었고 실행하지 않았다.
만든 스크립트: `진욱/m3수정_기용/research/bank_add/make_additions.py` (줄 목록 → csv). id 는 `ADD` + 주소 sha1 앞 8자리, bank 칸은 `추가`.
`target_case`·`target_cid` 칸은 기록용이다. 판정기에는 제목·주제·요약만 넘긴다.

| 원천 | 자료 수 | 대상 역량 | 라이선스 (넣은 범위) |
|---|---|---|---|
| docs.isaacsim.omniverse.nvidia.com, docs.nvidia.com, developer.nvidia.com | 12 | naver C04 3, C19 9 | NVIDIA 문서 약관 (제목·주소·요약만) |
| pytorch/tutorials (docs.pytorch.org) | 3 | naver C04 | BSD-3-Clause |
| jax-ml/scaling-book | 2 | naver C04 | MIT |
| apache/spark 문서 | 1 | naver C04 | Apache-2.0 |
| dask/dask 문서 | 1 | naver C04 | BSD-3-Clause |
| horace.io, baseten.co, lmsys.org 블로그 | 3 | naver C04 2, KK01-C21 1 | 각 블로그 저작권 (제목·주소·요약만) |
| isaac-sim/IsaacLab 문서 | 1 | naver C19 | BSD-3-Clause |
| isaac-sim/IsaacSim (GitHub) | 1 | naver C19 | Apache-2.0 (링크와 제목만) |
| THUDM/slime (GitHub, thudm.github.io/slime) | 11 | KK01-C21 | Apache-2.0 |
| Stanford CS231A 강의 쪽·노트 | 4 | K804 C06 2, C18 2 | 각 강의 제공처 |
| TUM Multiple View Geometry 강의 쪽·장 PDF | 4 | K804 C06 3, C18 1 | 각 강의 제공처 |
| CMU 16-385, CMU 16-822 (geometric3d.github.io) | 3 | K804 C06 2, C18 1 | 각 강의 제공처 |
| Middlebury CS1053, UMN CSci 5980 강의 쪽 | 2 | K804 C06 | 각 강의 제공처 |
| colmap/colmap 문서 | 1 | K804 C06 | BSD-3-Clause (링크와 제목만) |
| kornia/kornia 문서 | 4 | K804 C06 1, C18 3 | Apache-2.0 |
| facebookresearch/pytorch3d 튜토리얼 | 2 | K804 C06 1, C18 1 | BSD-3-Clause (링크와 제목만) |
| isl-org/Open3D 문서 | 3 | K804 C18 | MIT (링크와 제목만) |
| mint-lab/3dv_tutorial | 1 | K804 C18 | Beerware (링크와 제목만) |
| arXiv 1812.01537 (micro Lie theory) | 1 | K804 C18 | arXiv (링크와 제목만) |

합 60개: naver C04 12, C19 11, KK01-C21 12, K804 C06 12, C18 13.

#### 넣지 않은 것 (우회하지 않음)

- robots.txt 가 막음: robots.ox.ac.uk (Hartley·Zisserman 책 쪽), szeliski.org (Szeliski 책), learning3d.github.io (CMU 16-825), stanford.edu/class 아래 PDF 주소 (web.stanford.edu 주소로는 허용되어 그쪽을 씀), docs.ray.io.
- 403 응답: docs.opencv.org 튜토리얼 4개 (epipolar, depth map, calibration, pose).
- 404·시간 초과: cvg.ethz.ch 3D Vision 강의 쪽, 3d.bk.tudelft.nl GEO1016, CMU 16-385 lecture29a, PyTorch TensorBoard profiler 튜토리얼.
- 글을 뽑지 못함: TUM MVG 7장 PDF (본문 글자 없음), Isaac Sim Python Scripting 목차 쪽 (소개 문단 없음).
- 3D 가 아닌 2D 내용: CMU 16-385 lecture 7 (2D transformations).

### 더 모은 교육자료 (bank_additions/learn_more.csv, 2026-11-19)

`python -I m3_materials/collect_more.py --work <빈 scratch 폴더>` 가 아래 GitHub 공개 저장소에서 모은다. 모델 호출은 없다 (0원).
`m3_materials/data/edu_bank_NOTICE.md` 와 같은 규칙이다. 제목, 주소, 첫 문단 요약(300자 이내)만 저장하고 본문은 옮기지 않는다.
라이선스가 MIT, MIT-0, Apache-2.0, BSD-3-Clause, CC0-1.0, CC-BY-3.0/4.0 인 저장소만 쓴다. `--licenses` 가 GitHub 이 읽은 라이선스와 아래 표를 맞춰 본다 (11/19, 62곳 모두 맞음. eng-practices 는 LICENSE 파일이 CC-BY 3.0, rust-lang/book 은 LICENSE-MIT·LICENSE-APACHE 둘이라 GitHub 이 NOASSERTION 으로 읽는다).

- 받기: `git clone --depth 1 --filter=blob:none` 으로 트리만 받고, 고른 파일만 sparse checkout 으로 받는다. 저장소마다 1.1초 쉰다. 받은 파일은 scratch 폴더에만 두고 실행하지 않는다 (수집기는 `python -I` 로 돈다).
- 뽑기: 진욱 수집기의 `lessons()`·`title_and_summary()` 를 그대로 불러 쓴다. 앞에 글 다듬기 하나(HTML 주석 라이선스 머리말, 머리말의 꼬리표 목록, rst 윗줄 지우기)와 상용구 문단 건너뛰기(커널·호환 안내, 지은이 표시, 실습 소요 시간 등)를 얹었다.
- 거름: 노트북 모음의 폴더 README(노트북 없는 앱·틀)는 버린다 (`pick.teaches` 3번과 같은 규칙). 요약이 40자 아래인 줄, 정리(clean up)·준비물·다음 단계·변경 기록 같은 쪽, 참조 API·연동 목록·번역본·에이전트 지시 파일(CLAUDE.md 등)도 버린다.
- 주소는 GitHub 의 파일 주소다 (진욱 은행의 `url` 칸과 같다). id 는 `LRN` + 주소 sha1 앞 10자리, bank 칸은 `추가`.
- 결과: 5,555줄 (공식 문서 튜토리얼 2,837, 실습 노트북 1,865, 워크숍 랩 451, 글 202, 강의 레슨 200). `pick.bank()` 에서 겹침 제거 뒤 모두 남아 합친 은행이 8,877 → 14,432건이다.
- 검증: 합친 은행 수, 유형·원천별 수, 꼴 검사(id·유형·라이선스·요약 길이·주소), 무작위 30줄과 받은 파일 대조를 스크립트로 했다. 30줄 모두 받은 파일이 있고 제목이 그 파일의 것이며, 눈으로 보아 모두 가르치는 자료였다 (그중 4줄은 약함: 짧은 안내 쪽 1, 요약이 준비물 문단 1, 샌드박스 연동 안내 2). 은행 1만 넘음·라이선스·폴더 README 규칙은 `tests/test_m3_pick.py` 의 마지막 시험이 지킨다.

| 저장소 | 유형 | 라이선스 | 자료 수 |
| --- | --- | --- | --- |
| [aws-samples/amazon-bedrock-samples](https://github.com/aws-samples/amazon-bedrock-samples) | 실습 노트북 | MIT-0 | 285 |
| [aws-samples/sample-gen-ai-evaluations-workshop](https://github.com/aws-samples/sample-gen-ai-evaluations-workshop) | 워크숍 랩 | MIT-0 | 52 |
| [aws-samples/bedrock-multi-agents-collaboration-workshop](https://github.com/aws-samples/bedrock-multi-agents-collaboration-workshop) | 워크숍 랩 | MIT-0 | 5 |
| [aws-samples/amazon-bedrock-rag-workshop](https://github.com/aws-samples/amazon-bedrock-rag-workshop) | 워크숍 랩 | MIT-0 | 12 |
| [aws-samples/bedrock-kb-rag-workshop](https://github.com/aws-samples/bedrock-kb-rag-workshop) | 워크숍 랩 | MIT-0 | 2 |
| [aws-samples/llm-apps-workshop](https://github.com/aws-samples/llm-apps-workshop) | 워크숍 랩 | MIT-0 | 4 |
| [aws-samples/langgraph-agents-with-amazon-bedrock](https://github.com/aws-samples/langgraph-agents-with-amazon-bedrock) | 실습 노트북 | MIT-0 | 6 |
| [aws-samples/prompt-engineering-with-anthropic-claude-v-3](https://github.com/aws-samples/prompt-engineering-with-anthropic-claude-v-3) | 강의 레슨 | MIT-0 | 22 |
| [aws-samples/sample-getting-started-with-strands-agents-course](https://github.com/aws-samples/sample-getting-started-with-strands-agents-course) | 강의 레슨 | MIT-0 | 3 |
| [aws-samples/amazon-sagemaker-immersion-day](https://github.com/aws-samples/amazon-sagemaker-immersion-day) | 워크숍 랩 | MIT-0 | 15 |
| [aws-samples/sagemaker-end-to-end-workshop](https://github.com/aws-samples/sagemaker-end-to-end-workshop) | 워크숍 랩 | MIT-0 | 9 |
| [aws-samples/amazon-sagemaker-mlops-workshop](https://github.com/aws-samples/amazon-sagemaker-mlops-workshop) | 워크숍 랩 | MIT-0 | 6 |
| [aws-samples/amazon-sagemaker-feature-store-end-to-end-workshop](https://github.com/aws-samples/amazon-sagemaker-feature-store-end-to-end-workshop) | 워크숍 랩 | MIT-0 | 29 |
| [aws-samples/amazon-sagemaker-generativeai](https://github.com/aws-samples/amazon-sagemaker-generativeai) | 실습 노트북 | MIT-0 | 84 |
| [aws-samples/sagemaker-genai-hosting-examples](https://github.com/aws-samples/sagemaker-genai-hosting-examples) | 실습 노트북 | MIT-0 | 102 |
| [aws-samples/aws-research-workshops](https://github.com/aws-samples/aws-research-workshops) | 워크숍 랩 | MIT-0 | 9 |
| [aws-samples/asynchronous-messaging-workshop](https://github.com/aws-samples/asynchronous-messaging-workshop) | 워크숍 랩 | MIT-0 | 8 |
| [Azure/azureml-examples](https://github.com/Azure/azureml-examples) | 실습 노트북 | MIT | 348 |
| [Azure-Samples/AI-Gateway](https://github.com/Azure-Samples/AI-Gateway) | 워크숍 랩 | MIT | 54 |
| [MicrosoftLearning/mslearn-ai-agents](https://github.com/MicrosoftLearning/mslearn-ai-agents) | 워크숍 랩 | MIT | 36 |
| [MicrosoftLearning/mslearn-ai-fundamentals](https://github.com/MicrosoftLearning/mslearn-ai-fundamentals) | 워크숍 랩 | MIT | 8 |
| [MicrosoftLearning/mslearn-fabric](https://github.com/MicrosoftLearning/mslearn-fabric) | 워크숍 랩 | MIT | 48 |
| [MicrosoftLearning/mslearn-databricks](https://github.com/MicrosoftLearning/mslearn-databricks) | 워크숍 랩 | MIT | 30 |
| [MicrosoftLearning/mslearn-devops](https://github.com/MicrosoftLearning/mslearn-devops) | 워크숍 랩 | MIT | 33 |
| [MicrosoftLearning/DP-900T00A-Azure-Data-Fundamentals](https://github.com/MicrosoftLearning/DP-900T00A-Azure-Data-Fundamentals) | 워크숍 랩 | MIT | 7 |
| [MicrosoftLearning/dp-420-cosmos-db-dev](https://github.com/MicrosoftLearning/dp-420-cosmos-db-dev) | 워크숍 랩 | MIT | 67 |
| [MicrosoftLearning/AZ-700-Designing-and-Implementing-Microsoft-Azure-Networking-Solutions](https://github.com/MicrosoftLearning/AZ-700-Designing-and-Implementing-Microsoft-Azure-Networking-Solutions) | 워크숍 랩 | MIT | 17 |
| [microsoft/Generative-AI-for-beginners-dotnet](https://github.com/microsoft/Generative-AI-for-beginners-dotnet) | 강의 레슨 | MIT | 8 |
| [microsoft/generative-ai-with-javascript](https://github.com/microsoft/generative-ai-with-javascript) | 강의 레슨 | MIT | 8 |
| [microsoft/Web-Dev-For-Beginners](https://github.com/microsoft/Web-Dev-For-Beginners) | 강의 레슨 | MIT | 37 |
| [microsoft/Security-101](https://github.com/microsoft/Security-101) | 강의 레슨 | CC0-1.0 | 24 |
| [microsoft/code-with-engineering-playbook](https://github.com/microsoft/code-with-engineering-playbook) | 글 | CC-BY-4.0 | 189 |
| [MicrosoftDocs/azure-docs](https://github.com/MicrosoftDocs/azure-docs) | 공식 문서 튜토리얼 | CC-BY-4.0 | 712 |
| [GoogleCloudPlatform/vertex-ai-samples](https://github.com/GoogleCloudPlatform/vertex-ai-samples) | 실습 노트북 | Apache-2.0 | 375 |
| [GoogleCloudPlatform/asl-ml-immersion](https://github.com/GoogleCloudPlatform/asl-ml-immersion) | 실습 노트북 | Apache-2.0 | 78 |
| [huggingface/transformers](https://github.com/huggingface/transformers) | 공식 문서 튜토리얼 | Apache-2.0 | 188 |
| [huggingface/diffusers](https://github.com/huggingface/diffusers) | 공식 문서 튜토리얼 | Apache-2.0 | 100 |
| [huggingface/peft](https://github.com/huggingface/peft) | 공식 문서 튜토리얼 | Apache-2.0 | 16 |
| [huggingface/trl](https://github.com/huggingface/trl) | 공식 문서 튜토리얼 | Apache-2.0 | 51 |
| [huggingface/accelerate](https://github.com/huggingface/accelerate) | 공식 문서 튜토리얼 | Apache-2.0 | 42 |
| [huggingface/datasets](https://github.com/huggingface/datasets) | 공식 문서 튜토리얼 | Apache-2.0 | 56 |
| [huggingface/smolagents](https://github.com/huggingface/smolagents) | 공식 문서 튜토리얼 | Apache-2.0 | 16 |
| [huggingface/evaluate](https://github.com/huggingface/evaluate) | 공식 문서 튜토리얼 | Apache-2.0 | 12 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 실습 노트북 | MIT | 9 |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | 실습 노트북 | MIT | 243 |
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | 공식 문서 튜토리얼 | Apache-2.0 | 120 |
| [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | 공식 문서 튜토리얼 | Apache-2.0 | 211 |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 공식 문서 튜토리얼 | MIT | 34 |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 공식 문서 튜토리얼 | MIT | 257 |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 공식 문서 튜토리얼 | MIT | 110 |
| [mlflow/mlflow](https://github.com/mlflow/mlflow) | 공식 문서 튜토리얼 | Apache-2.0 | 222 |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 실습 노트북 | CC-BY-4.0 | 47 |
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 실습 노트북 | BSD-3-Clause | 261 |
| [ageron/handson-ml3](https://github.com/ageron/handson-ml3) | 실습 노트북 | Apache-2.0 | 27 |
| [jax-ml/jax](https://github.com/jax-ml/jax) | 공식 문서 튜토리얼 | Apache-2.0 | 32 |
| [github/docs](https://github.com/github/docs) | 공식 문서 튜토리얼 | CC-BY-4.0 | 300 |
| [google/eng-practices](https://github.com/google/eng-practices) | 글 | CC-BY-3.0 | 13 |
| [reactjs/react.dev](https://github.com/reactjs/react.dev) | 공식 문서 튜토리얼 | CC-BY-4.0 | 49 |
| [microsoft/TypeScript-Website](https://github.com/microsoft/TypeScript-Website) | 공식 문서 튜토리얼 | CC-BY-4.0 | 74 |
| [rust-lang/book](https://github.com/rust-lang/book) | 강의 레슨 | MIT 또는 Apache-2.0 | 98 |
| [open-telemetry/opentelemetry.io](https://github.com/open-telemetry/opentelemetry.io) | 공식 문서 튜토리얼 | CC-BY-4.0 | 168 |
| [istio/istio.io](https://github.com/istio/istio.io) | 공식 문서 튜토리얼 | Apache-2.0 | 67 |

#### 넣지 않은 것

- 라이선스 파일 없음: huggingface/blog, fastai/course22, mmcgrana/gobyexample (README 에만 CC-BY 3.0). fastai/fastbook 은 글의 재배포를 막는다.
- 이미 진욱 은행에 있음: amazon-bedrock-workshop, amazon-sagemaker-examples, GoogleCloudPlatform/generative-ai, eks-workshop-v2, aws-cdk-intro-workshop 등 (진욱 NOTICE 표).
- 가르치는 쪽이 거의 없음: aws-samples/java-on-aws (앱 README), awslabs/aws-well-architected-labs (본 랩은 저장소에서 빠지고 파트너 쪽만 남음), aws-samples/cfn101-workshop·aws-devops-end-to-end-workshop (내용 폴더가 없음).
- 한 원천 안에서 뺀 폴더: vertex-ai-samples 의 model_garden(모델마다 배포만 되풀이)·gapic·migration, sagemaker-genai-hosting-examples 의 01-models, llama_index 의 연동 노트북(vector_stores, llm, embeddings 등), mlflow 의 integrations·self-hosting, deepeval 의 changelog·integrations, crewAI 의 tools, scikit-learn 의 release_highlights, TypeScript 의 release-notes, azure-docs 의 운영 전용 서비스(migrate, backup, site-recovery 등 17곳).

## 은행 표 questions 출처 (data/banks/questions.csv)

질문 문장과 답 글 링크는 아래 두 저장소의 README 에서 옮겼다. 둘 다 Apache License 2.0 (Copyright (C) 2026 Outcome School) 이다.
`python -m m3_materials.bank build` 가 README 를 받아 질문마다 출처 저장소(`repo`)와 라이선스를 칸으로 남기고, 두 저장소에 똑같이 있는 문장은 한 번만 둔다.
질문 문장은 바꾸지 않았다. 답 글 본문은 옮기지 않고 제목과 주소만 쓴다.

- https://github.com/pallavi-shekhar/ai-engineering-interview-questions-company-wise
- https://github.com/amitshekhariitbhu/ai-engineering-interview-questions
- 라이선스 전문: https://www.apache.org/licenses/LICENSE-2.0
