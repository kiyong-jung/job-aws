# frontend-design 스킬 기반 규칙표 (Claude.ai 풍 채용공고 분석 데모)
출처: anthropics/skills/skills/frontend-design/SKILL.md (파일 1개 + LICENSE, 참조 파일 없음). 인용은 원문 영어.
## 0. 가장 중요한 전제
- 브리프가 방향을 정하면 따른다: "the brief's own words always win, including when it asks for one of these looks." 우리 브리프는 "Claude.ai 처럼 보이고 느껴지게"이므로 Claude.ai 의 크림 배경·세리프·테라코타 포인트는 의도된 선택으로 허용. 단 스킬은 그 조합을 AI 티의 1번 특징으로 꼽으므로(크림 #F4F1EA + 세리프 + #D97757) "복제"가 아니라 "근접 재현"으로 하고 나머지 축(표·하이라이트 연결)에서 개성을 낸다.
- "Spend your boldness in one place." 기억에 남는 한 요소 = 하이라이트 <-> 표 행 연결. 나머지는 조용하게.
## 1. 서체
- 한 가족 또는 두 가족: "use one family or two, and if two, make them clearly distinct."
- 권장: 본문/UI 는 Pretendard Variable(한글+라틴 통합, 산세리프). 공고 원문 패널 본문만 세리프(Noto Serif KR 또는 Source Han Serif)로 하면 Claude.ai 아티팩트 느낌 + 두 가족이 확실히 구분됨. 코드/수치는 쓰지 말 것(모노 라벨은 AI 티).
- 크기: UI 14-15px, 채팅 본문 15-16px, 공고 본문 15-16px, 표 13-14px. 스케일은 1.125-1.2 비율로 4단계 이하.
- 행간: 한글은 라틴보다 크게. 산세리프 한글 1.6-1.7, 세리프 본문 1.75-1.85. 스킬: "give serif body text slightly more line-height than a sans-serif."
- 줄 길이: "Default to line lengths of less than 80 characters." 한글은 한 줄 35-45자 정도(공고 패널 max-width ~ 38em). 세리프는 조금 더 길어도 됨.
- 한글 줄바꿈: word-break: keep-all; overflow-wrap: anywhere; letter-spacing -0.01em 내외. 자간을 크게 벌리지 말 것.
- 피할 것(스킬 원문):
  - "Accenting just a single word or phrase in a headline"
  - "Using all caps for labels."
  - "Adding unnecessary typographic labels above content."
  -> 패널 제목은 문장형 한 줄("채용공고 원문"), 영문 대문자 eyebrow(JOB POSTING 등) 금지.
## 2. 색
- 먼저 토큰 정하기: "describe the core base palette as 4-6 named hex values." 예시(조정 가능):
  - paper #FAF9F5 (채팅 배경), panel #FFFFFF (아티팩트 패널), ink #1F1E1D, muted #6B6A66, line #E8E6DF, accent(AI/버튼) #C96442 계열 하나만.
- 순수 #000 대신 따뜻한 먹색. 스킬은 "tinted near-black (#0B0B0B, #111) standing in for black"를 AI 티로 지적하므로, 쓰려면 의도(따뜻한 ink)를 분명히 하고 대비 4.5:1 확인.
- 노란 하이라이트: 형광펜 느낌의 #FFE97A 40-60% 투명도(배경 뒤에 깔림, 글자색 유지). 활성/호버 때만 진한 #FFD43B. 다크모드면 #FFD43B 25% 알파.
- 역량 항목 색: 하이라이트는 노랑 하나로 통일하고, 구분은 색이 아니라 번호가 아닌 짧은 역량명 칩 + 얇은 좌측 막대 정도로. 무지개 카테고리 색 금지.
- 장식용 그라디언트 금지: "gradient washes as decoration" 은 SaaS 카드 키트의 징후.
## 3. 레이아웃과 간격
- 구조는 정보여야 함: "Structural devices like outlines, borders, numbering, eyebrows, dividers, labels, etc., encode useful information about the content rather than decorate it."
- 번호 01/02/03 은 순서가 있을 때만. 역량 표 행의 번호는 "공고 속 하이라이트 순서"와 연결될 때만 의미 있음(하이라이트 위 작은 번호 = 표 행 번호로 쓰면 정당).
- 2단: 좌측 채팅 약 38-42%(최대 ~560px, 대화는 가운데 정렬 컬럼 max 680px), 우측 아티팩트 패널 나머지. 패널은 흰 종이 + 1px line + 큰 radius 한 종류(12-16px)로 채팅과 구분. 하나의 반경만 모든 곳에 쓰지 말고 위계별로: 입력창 20px, 패널 14px, 칩 6px.
- 피할 것: "content chopped into identical rounded cards, one border-radius on everything... the same soft grey shadow (rgba(0,0,0,.1)) under each". 그림자 거의 없이 1px 선으로.
- 간격 4px 단위: 8/12/16/24/40. 패널 안쪽 패딩 24-32px, 문단 사이 1em. 정렬은 좌측 정렬(중앙정렬 금지, 한글 본문).
- 패널 헤더: 높이 ~48px, 파일명 + 상태 + 복사/닫기 아이콘. 아이콘 버튼만 쓰고 라벨 상단 장식 금지.
- CSS 특이도 주의: "easy to generate CSS classes that cancel each other out". 클래스 하나로 통일, 섹션 간 margin 을 한 방향(margin-block-start)으로만.
## 4. 모션 (이 데모의 핵심)
- 자동 모션은 아껴라: "Use non-user-triggered motion sparingly and deliberately, only to draw attention. A single orchestrated moment... lands better than scattered effects."
- 단 하나의 연출 = 하이라이트 순차 등장: 공고 본문이 뜬 뒤 형광펜이 왼쪽에서 오른쪽으로 칠해지듯(background-size 0 -> 100%, 450ms ease-out, 문장 간 250ms 간격) 문장별로 칠해지고, 칠해질 때 대응하는 표 행이 한 줄씩 추가됨.
- 금지: "fade-and-slide-up entrances on each section and hover transitions on every card are the generic default and read as AI-generated."
- 사용자 행동에 반응하는 모션은 환영: "Motion that answers a person's action (opening, expanding, confirming) is welcome when it shows what changed." -> 표 행 호버/클릭 시 해당 하이라이트가 진해지고 패널이 그 위치로 부드럽게 스크롤(scrollIntoView smooth), 반대도 동일.
- prefers-reduced-motion 이면 칠하기 애니메이션 제거하고 즉시 표시.
## 5. 하이라이트 <-> 표 매핑 (스킬 원칙 적용)
- 연결은 "의미 있는 구조"여야 함: 양방향 호버 연동(같은 data-id), 활성 시 하이라이트 진하게 + 행 배경 노랑 틴트 + 좌측 3px 노랑 막대. 선(SVG 연결선)은 패널 사이가 멀어 지저분해지므로 기본은 연동 강조, 선택적으로 클릭 시만 얇은 곡선.
- 하이라이트 끝에 작은 숫자 위첨자(1,2,3)와 표 첫 열 같은 숫자로 매칭(순서가 실제 의미일 때). 표에는 "역량명 | 근거 문장 요약 | 수준" 정도만, 열 라벨은 문장형 소문자/한글.
- 키보드 접근: 하이라이트는 <mark tabindex=0>, 포커스 링 보이게. 노랑만으로 전달하지 말고 밑줄/번호 병행(색각 이상 대비).
## 6. 아티팩트 패널 특화
- 스킬에 아티팩트 전용 규칙은 없음. 아래는 스킬 원칙을 적용한 제안.
- 입력 3종(파일 드롭/붙여넣기/URL)은 빈 패널이 곧 초대: "An empty screen is an invitation to act." 점선 드롭존에 "공고 파일을 놓거나 URL 을 붙여넣으세요" 한 줄. 실패/빈 상태는 이유와 해결 방법을 적고 사과하지 않음.
- 상태 문구 일관: 같은 동작은 같은 이름("분석 시작" -> "분석 시작됨"). 버튼은 동사형("공고 불러오기", "하이라이트 보기"), "제출/확인" 금지.
- 채팅 진행 표시는 시스템 구조가 아니라 사용자 언어로: "지원 자격 문장 찾는 중", "역량 5개 정리 중". 단계가 정말 순서면 체크 목록으로 표시.
- 패널 상단 탭("원문 / 역량표")은 보조. 기본은 원문과 표를 같이 보이게(상하 분할 또는 표를 패널 하단 고정) — 매핑이 한눈에 보이는 게 핵심.
## 7. 피할 AI 티 체크리스트 (스킬 원문 5항목)
1. 크림 배경 + 고대비 세리프 + 테라코타 포인트 (우리는 Claude.ai 풍이라 의도적 허용이지만 한 요소 이상 겹치지 말 것)
2. 검정 배경 + 형광 단일 포인트
3. 헤어라인 신문 레이아웃, radius 0
4. 동일 둥근 카드 + 동일 그림자 + 그라디언트
5. 템플릿 장식: 대문자 eyebrow, 가운뎃점 연결 메타("A · B · C"), "WORD — fragment" 라벨, 모노 작은 라벨, 링크 끝 "->"
- 또 피함: 히어로에 "큰 숫자 + 작은 라벨 + 그라디언트"(기본 처리).
## 8. 품질 하한과 과정
- "responsive down to mobile, visible keyboard focus, reduced motion respected, visually accessible, harmonious color palettes." 모바일에서는 패널이 채팅 아래/전체화면 시트로.
- 과정: 토큰(색·서체·레이아웃·원칙) 계획 -> 브리프와 대조해 기본값이면 수정 -> 구현 -> 스크린샷으로 자기 비평. "remove one accessory": 구현 후 장식 하나 제거.
- 문구는 설계의 일부: 능동태, 문장형 대소문자(한글은 해당 없음), 군더더기 없음. 실제 한국어 채용공고 샘플 문구를 써서 시연(자리 채우기 lorem 금지).
