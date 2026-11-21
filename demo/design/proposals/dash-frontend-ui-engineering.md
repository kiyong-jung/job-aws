# 숫자 카드·차트 카드 설계안 (frontend-ui-engineering 눈, 2026-11-18)

근거: `design/dash_brief.md`, `DESIGN_RULES.md`, `design/guides/frontend-ui-engineering.md`, 지금 코드(`main.js` 처리기, `chat.js headline`, `study.js`, `weeks.js`, `search.js`, `report.js`, `panel.js`, `css/*`), 참고 템플릿의 `_card.scss`·`_progress-bar.scss`·`home*Chart.js`·`preview/s_02.jpg` (읽기만). c1 고치기가 끝난 뒤 만든다.

## 한 줄 결론
- 작은 공용 모듈 하나(`static/js/cards.js`, 80줄 안)에 `statCard` · `chartCard` · `legend` 세 함수를 둔다. 순수 함수가 노드를 돌려주고, 사건이 올 때 그 노드의 글만 바꾼다.
- ApexCharts 는 들이지 않는다. 지금 그림 넷(②깔때기·후보 칸, ③덮기 띠, ④막대, ⑤16주 막대)은 HTML/CSS 칸이라 글이 DOM 에 있고, `link.js` 짝짓기와 `shots.py` 검사가 그 칸에 걸려 있다.
- 템플릿에서 가져오는 것은 짜임뿐: 아이콘 동그라미 + 이름표 + 큰 숫자, 제목 + 그림 + 범례, 둥근 테두리 카드, 16px 안쪽 여백. 그림자·색 여럿·증감 % 배지·작은 선 그래프·2초 선형 막대 움직임은 버린다.

## 1. `statCard` (답 맨 위 큰 숫자)
- 부르는 곳: `chat.headline(big, line, before, short)` 의 속을 이것으로 바꾼다. 부르는 쪽 여섯(①~⑥ 답)은 그대로.
- 꼴: `statCard({ icon, label, value, line, short })` → `<div class="stat" role="group" aria-label="{label} {value}">`
  - 왼쪽 32px 동그라미(`--sunk` 바탕, 먹 선 아이콘 18px, `icons.js` 의 것만, `aria-hidden`). 장식이 아니라 단계 표지: ① 형광펜, ② 찾기, ③ 묶기, ④ 책, ⑤ 달력, ⑥ 문서. 단계 길의 아이콘과 같은 것.
  - 오른쪽 위 이름표 13·500·먹(예 "찾은 역량"), 그 아래 값 20·600·`tabular-nums`(예 "29개"). 작은 회색 곁글 없음(U4-1).
  - 카드 아래 한 줄(15, 지금 `headline-line`)과 좁을 때 `short` 는 지금 규칙 그대로.
- 겉: 테두리·바탕 없음. 답 말풍선 안이라 상자를 또 두면 세 겹이 된다(S3). 높이는 지금 headline 과 같게(동그라미 32 ≤ 이름표+값 두 줄 높이) → 1440×900 한 화면 규칙을 깨지 않는다.
- 이름표는 값과 같은 말을 되풀이하지 않는다(S9): "29개 역량" → 이름표 "찾은 역량", 값 "29개".
- 하지 않는 것: 증감 배지, 세어 올라가는 숫자, 카드 여러 장 나란히(답마다 숫자 하나 규칙).

## 2. `chartCard` (오른쪽 칸 주 그림의 틀)
- 꼴: `chartCard({ title, body, legend })` → `<figure class="chart-card"><figcaption>제목</figcaption>{body}{legend}</figure>`.
- 쓰는 곳: 쪽마다 주 그림 하나(S1)에만: ② 후보 칸 판, ③ 덮기 띠, ④ 공부 시간 막대, ⑤ 16주 막대. 깔때기 띠·목록·1위 카드는 카드 밖.
- 겉: 1px `--line`, `--r-card` 12, 안쪽 16(390 에서 12), 그림자 없음. 쪽 자체는 상자가 아니므로 카드가 첫 겹, 안의 칸이 둘째 겹(S3 안).
- 제목 14·600·먹, 한 줄, 넘치면 말줄임 대신 짧은 제목(`title.short`, 서버가 준다).
- `legend(items)`: `<ul class="legend" role="list">` 13·먹. 항목 = 견본 모양 + 이름 (+ 서버가 준 수). 견본은 그림의 칠과 같은 클래스(`.key-swatch[data-level]`, 다 칠·반 칠·빈 테두리·빗금)를 다시 쓴다. 지금 `study.js` 묶음 머리, `weeks.js` 범례·넘침 범례, `search.js` 점수 범례가 저마다 만든 것을 이것 하나로.
- 범례 항목은 그 그림에 그 칠이 나온 뒤에만 붙는다(지금 ⑤ 넘침 범례 규칙을 공용 규칙으로: `legend.add(key)`).

## 3. ApexCharts 를 안 쓰는 까닭 (손 HTML/CSS 유지)
| 볼 것 | ApexCharts 3.41.0 (템플릿 `lib/apexcharts.min.js`) | 지금 손 그림 |
| --- | --- | --- |
| 크기 | 512,609 바이트 한 파일, 내려받기 없이 둬도 화면 js 전체보다 큼 | 더할 것 없음 |
| 움직임 | 자체 움직임(경로·높이 바꾸기, 기본 800ms 안팎). 끄면 사건마다 자라는 움직임도 직접 다시 짜야 함 → S6·S7과 부딪힘 | `animate()` 로 scaleX/scaleY 240ms, 사건마다 한 번 |
| 글 | SVG `<text>` 를 스스로 그림. 한글 줄바꿈·13 아래 금지·`keep-all`을 설정으로 다 막아야 함 | 글이 DOM, css 토큰 그대로 |
| 짝짓기 | 조각마다 `data-lid` 를 달 수 없어 `link.js`(막대 조각 ↔ 표 줄 ↔ 문장)가 깨짐 | 조각이 곧 노드 |
| 접근성 | 풀이가 마우스 올리기 툴팁 위주(가이드: hover 만으로 말하는 것은 위반) | `role=img` + `aria-label` 을 사건 값으로 |
| 검사 | `shots.py` 의 `.seg`·`.bars`·`.cap-line`·`.stop-n` 검사를 모두 다시 써야 함 | 그대로 |
- 그림 넷 모두 막대·칸이라 SVG 도 필요 없다. 선·넓이 차트가 필요한 날이 오면 그때 `static/vendor/apexcharts-3.41.0.min.js`(CDN 없이, sha256 을 `test_demo.py` 가 확인)로 넣는다. 지금 계획에는 없다.

## 4. 움직임 규칙
- 사건 하나 → 움직임 하나. 카드 두 함수는 스스로 움직이지 않는다. 안의 그림이 지금처럼 움직인다(④ 조각 scaleX, ⑤ 덩어리 scaleY, ② FLIP 560, 쪽 넘기기 280).
- `statCard` 는 답이 붙을 때 나타날 뿐(지금 `row-in` 과 같은 opacity·translateY 한 번). 값이 바뀌는 일은 안 바꾸기 때 끝 그림 다시 그리기뿐이고 그때는 움직이지 않는다.
- transform·opacity 만. 너비·높이·`d` 를 움직이지 않는다. 길이 값은 css 변수(`--w`, `--h`)로 한 번에 놓고 scale 로만 자란다.
- 지금 넷에 흩어진 "움직임 줄이기면 건너뜀 + 안 보이면 건너뜀" 을 `icons.js` 의 `play(node, frames, ms)` 하나로 모은다(`weeks.js grow`, `study.js`, `search.js`, `panel.js` 가 같은 검사를 따로 함).
- 버리는 템플릿 움직임: `animateBar`(2초 선형, 진입마다), 떠오르는 이름표, 깜빡이는 로더.

## 5. 카드마다 사건에서 받을 값 (화면이 셈하지 않는다)
| 카드 | 값 | 사건·필드 | 지금 화면이 셈하는 것 → 고칠 것 |
| --- | --- | --- | --- |
| ① 답 | 역량 수, 핵심 문장 수, 필수·우대 | `done.rows/marks/required/preferred` | 없음 |
| ② 답·깔때기 | DB 크기, 후보 1,000·100, 1위 점수 | `steps.db`, `pool`, `shortlist`, `tier` | `main.js:396`·`search.js:53` 이 `papers + repos` 를 더함 → 서버가 `db.total` 을 보낸다 |
| ③ 쪽 머리 | 역량 29개 중 25개, 9·7 | `project.done.before/after` | 없음 (assert 가 `build_data.py` 에) |
| ④ 답·막대 | 51시간, 84시간 중 N | `done.hours/line`, `item.row.total` | `study.js:115` 의 `?? s.hours + row.hours` 대신값 → `total` 없으면 사건 오류로 본다 |
| ⑤ 답·막대 | 프로젝트 일, 한도, 안에 드는 주 | `done.project/cap/over/weeks` | `main.js` 의 `weeks - over.length`, `weeks.js:131,144` 의 주별 합 → 서버가 `inside`, 주별 `study_hours`·`work_hours` 를 보낸다 |
| ⑥ 머리 | 실제 질문 수, 문장 수 | `done.real/rows`, `line` | 정리한 줄 수는 받은 `line` 사건 수(지어낸 값 아님, 둔다) |
- 받은 사건 개수 세기(묶음 안 수, 정리한 줄 수)는 허용, 시간·점수를 더하거나 빼는 것은 서버로. 이 선을 `cards.js` 머리 주석 한 줄과 아래 시험으로 지킨다.

## 6. 시험과 사진 검사
- `tests/test_demo.py` (사건 쪽):
  - ② `steps.db.total == papers + repos`, ⑤ `done.inside == weeks - len(over)`, 주별 `work.work_hours == sum(packages.hours)` 를 세 공부 시간 안(84·168·252)마다 `parametrize`.
  - ④ 모든 `item.row` 에 `total` 이 있고 늘어나기만 함.
  - 벤더 파일을 넣는 날에만: 파일 sha256 고정, `index.html` 에 외부 주소 없음.
- `shots.py` (화면 쪽, 새 검사 다섯):
  1. `.stat` 이 답마다 하나, 값 글자 20px·600·`tabular-nums`, 이름표 13px·먹. 13 아래 글 0개(지금 검사 확장).
  2. 1440×900 에서 다 끝난 답 하나가 대화 칸 한 화면 안(지금 검사가 `.stat` 으로도 돈다), 390 에서 동그라미·값·이름표가 한 줄 안(넘침 0).
  3. `.chart-card` 가 쪽마다 0 또는 1개, 그 안에 `.chart-card` 없음(두 겹), 그림자 `none`.
  4. 범례 견본의 계산된 바탕/테두리가 그림 칸의 같은 상태와 같음(④ 조각, ⑤ 공부·프로젝트·빗금, ③ 세 정도). 넘침 범례는 넘는 주가 그려지기 전 사진에 없음.
  5. 사건 하나 동안 `document.getAnimations()` 에 새로 생긴 움직임이 하나뿐이고, 그 키프레임 속성이 `transform`·`opacity` 뿐. 움직임 줄이기에서는 0개.
- 사진: 지금 상태 목록에 `stat-1`~`stat-6`(답 맨 위만 잘라서) 여섯 장을 더해 검토 에이전트가 템플릿 그림과 나란히 본다.

## 만드는 차례 (c1 고치기 끝난 뒤)
1. 서버 필드 셋(`db.total`, `inside`, 주별 시간) + `test_demo.py` → 화면은 받은 값만 쓰게 바꿈.
2. `cards.js` + `css` 한 덩이(`chat.css` 끝에 `.stat`, `panel.css` 끝에 `.chart-card`·`.legend`), `chat.headline` 속 바꾸기.
3. 그림 넷을 `chartCard` 로 감싸고 범례를 `legend` 로 합침, `play()` 로 움직임 모음.
4. `shots.py` 검사 다섯, 전체 한 번 통과, README 파일 표 갱신.
