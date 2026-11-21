# d2 검토: 숫자·차트 부품 + 고르기 칸 옮기기 + 제목 글꼴 (frontend-ui-engineering 눈, 2026-11-18)

읽은 것: `v7-dash-spec.md`, `c1-lead.md`, `c1-frontend-ui-engineering.md`, `static/js/{cards,icons,budget,panel,main,study,weeks,search}.js`, `static/css/{tokens,chat,panel,layout}.css`, `pipeline.py` 의 새 값, `shots.py` 의 `check_cards`·`check_title_font`, `../tests/test_demo.py`.
돌린 것: pytest 120개 통과. 내 서버(8794, `--speed 0.3`)에서 머리 없는 Chrome 으로 shots.py 의 `Page` 를 빌려 직접 눌러 봄 (shots.py 는 돌리지 않음, 8770 은 건드리지 않음). 스크립트 오류 0, 실패한 요청 0 (HALUNA 를 막은 경우 빼고).

## 1라운드 항목
- 1 `리포트로 돌아가기` 가 안 나옴: 고침. `main.js:596` 리포트 끝에서 `offerReturn()`.
- 2 진한 노랑 두 줄: 고침. `main.js:44-48` 돌아오면 `unpick()` (`link.clear`).
- 3 오가기 상태 네 곳: 고침. `store.back = {n, back}` 하나, `pickedN`·`returning` 없음, 글자 파싱 없음.
- 4 스크롤 셈 세 벌: 고침. `toPosting` 이 `panel.scrollInto` 를 씀 (`main.js:71`). 남은 `scrollTop =` 은 되돌리기·맨 위로뿐.
- 5 ⑤ 좁은 주 이름: 고침. `panel.css:387` 1·4·10·14, 주석도 맞음.
- 6 `weeks_text` 빈 글: 고침. `pipeline.py:752` `ValueError`.
- 7 Esc 알림: 고침. `link.js:150` 고른 것이 있을 때만.

## 확인된 것 (고칠 것 없음)
- 고르기 칸은 늘 하나(`#budget` 1개, 늘 붙어 있음). ④ ⑤ 를 처음 그리는 중에도 끝난 뒤에도 `.chart-aside` 안. ⑥ 에서는 `#stack` 바로 위, ①②③ 에서는 숨고 그 자리.
- ⑤ 에서 화살표로 84→168: 칸은 새 ⑤ 틀 머리에, 초점은 `input=168`, `:focus-visible` 고리 보임. 390: 칸이 사실 문장 아래 줄, 폭 332 = 머리 폭, 누르는 칸 52px, 가로 넘침 0.
- 빠르게 바꾸기 (늦춘 요청, ⑤ 에서 252→168→84 를 50ms 간격): 끝은 84 하나, 한도 글 "한 주 14시간까지", `?budget=84`, `aria-busy` 0, 초점 `input=84`.
- 바꾸는 중에 다른 쪽으로: ④ 에서 252 를 고르고 바로 ⑥ → 끝난 뒤 칸은 ⑥ 자리, 초점 그대로. 다시 ④ 로 가면 틀 머리. 168 을 고르고 바로 ② → 칸은 숨고, 끝난 뒤 ⑤ 로 가면 틀 머리.
- 단계 길·뒤로(진짜 마우스로 누름): ⑤→②→뒤로①→⑤→④→뒤로③. 칸의 자리와 숨김이 쪽마다 맞고, 초점은 그 쪽의 원문 칸이나 뒤로 단추로 감.
- 리포트 줄 → `공고에서 보기` → `리포트로 돌아가기`: 칸은 ①에서 숨고 ⑥에서 보임, 초점은 summary.
- ⑤ 에서 새 공고(로고): 칸은 붙은 채 자기 자리로 가고 숨음, `?budget=` 비워짐.
- 화면은 셈하지 않음: `db.total`(`search.js:51`, `main.js:396`), `inside_weeks`(`main.js:552`, `weeks.js:171`), `work_hours`(`weeks.js:139`), `row.total` 없으면 오류(`study.js:115`). pytest 가 셋 다 저장본과 견줌(`test_demo.py:254, 496, 509-510`).
- HALUNA 파일을 막으면 로고·인사·답 큰 숫자 모두 Pretendard 로 나오고 넘침 0, 스크립트 오류 0. 파일이 있으면 로고·큰 숫자는 HALUNA, 한글은 Pretendard.

## 반드시
없음.

## 고침
없음.

## 손볼 것
1. **바꿀 때마다 초점이 두 번 빠졌다 돌아옴.** 화살표 한 번에 `focusout(→null)/focusin` 이 두 쌍 생김. `main.js:726` `place(null)` 과 `main.js:740` `placeBudget()` 이 노드를 두 번 옮기기 때문. 화면 읽기 프로그램이 라디오 무리를 다시 읽어 "하루 2시간으로 바꿨어요" 알림과 겹칠 수 있음. 고칠 길: 다시 그릴 때 `.chart-head` 를 두고 그 아래 그림만 바꾸거나, 새 틀을 만들 때 노드를 바로 새 `.chart-aside` 로 옮겨 한 번만 움직이게.
2. **HALUNA 는 400 하나뿐인데 600 으로 씀** (`tokens.css:20`, 쓰는 곳 `chat.css:59`, `panel.css:93,153`, `layout.css:67`). 계산값 `font-weight 600`, `font-synthesis-weight: auto`. 그래서 라틴 글자·숫자가 가짜 굵기로 그려짐. 제목 글꼴 자리에 `font-synthesis: none` 을 주거나, HALUNA 로 그리는 덩어리는 400 으로.
3. **HALUNA 에서는 `tabular-nums` 가 안 먹음.** 20px 에서 "1111" 은 27.3px, "0000" 은 44.8px (`chat.css:61` `.stat-num`, `panel.css:153` `.stop-n.is-db`). 설계서 1절(큰 숫자 tabular)과 5절(tabular 가 필요한 곳엔 HALUNA 금지)이 서로 어긋남. 숫자 하나뿐이라 보기에는 탈이 없음. 다만 `shots.py:286` 은 계산된 속성만 봐서 `.stop-n.is-db` 를 통과시키는데, 이는 대신 재는 값임. 큰 숫자에서 tabular 를 빼고 검사에서도 제외하든지, 실제 폭으로 재든지 하나로.
4. **파일이 없는 저장소 사본에서는 페이지를 열 때마다 글꼴 404 가 콘솔에 찍힘.** `shots.py:2190` 은 `setBlockedURLs`(ERR_BLOCKED)로 막아서 실제 404 와는 다름. 가이드 8절 "콘솔 오류 없음"에 걸림. `Fetch` 로 404 를 돌려주게 바꾸거나, 404 하나는 알고 받아들인다고 적기.
5. **군더더기**: `budget.js:10` `box = () => node` 는 감싸기만 함(노드를 바로 씀). `budget.js:56,61` `place` 가 돌려주는 `at` 은 아무도 안 씀. 맨 위 주석 `budget.js:1` "④ ⑤ ⑥ 쪽 머리의 라디오 칸"과 `index.html:75` "쪽 머리 아래, 쪽 본문의 첫 줄"은 옛 자리 설명이라 지금 자리에 맞게 고침.
6. **"틀을 비우기 전에 칸을 먼저 빼낸다"는 규칙이 순서에만 기대고 있음** (`main.js:220-221` 은 `panel.reset` 의 `head()` 가 먼저 돎, `main.js:711,726`). 지금은 다 지켜지고, 어겨도 다음 `head()` 가 칸을 되돌려 놓음(`budget.js:57-59`). 다만 그때 초점은 잃음. `study.clear`/`weeks.clear` 가 스스로 `place(null)` 을 부르게 하면 규칙이 한 곳에 모임.

판정: 반드시 0, 고침 0, 손볼 것 6. 이대로 내보내도 됨 (2·3번은 글꼴 자리를 손볼 때 같이 고치길 권함).
