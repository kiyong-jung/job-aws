# b1 검토: 공부 시간 고르기 (frontend-ui-engineering 눈, 2026-11-18)

읽은 것: `DESIGN_RULES.md`, `v5-budget-spec.md` 6·8절, `proposals/budget-frontend-ui-engineering.md`, `README.md`, `pipeline.py`·`server.py`·`static/js/*`·`shots.py`·`../tests/test_demo.py`.
돌린 것: pytest 35개 통과. 내 서버(8791, `--speed 0`)에 `/api/run` 을 안마다·이상한 값 열세 가지로 찔러 봄 (`"100"`, `""`, `True`, `["84"]`, `1e9`, `"084"`, `" 84"`, `{}` 모두 error 하나, 정수 84 와 빈 값은 "84"). 머리 없는 Chrome 으로 바꾸기를 빠르게 몰아 봄 (`speed:0` 요청만 0.9초 늦춤).

## 반드시 (고치기 전에는 내지 않는다)

1. **바꾸기가 끝나기 전에 다음 단계를 누르면 단계마다 다른 안이 섞인다.** `main.js:638-681` `switchBudget` 은 기다린 뒤 `ac.signal.aborted` 만 본다(655). `runStep`(592-600)·`send`(299-306)·로고(162-168)·`reset`(175-184) 어느 곳도 `store.switching` 을 멈추지 않는다.
   - 재현 A: 84 로 ④ 를 그림 → 168 을 고르고 바로 `12주 계획 짜기` → 끝 상태가 라디오 168, ④ "168시간 중 120시간", ⑤ "한 주 14시간까지"(84 값). 이 ⑤ 는 `weeks:84` 로 `store.runs` 에 들어가고, 이어 리포트는 168 로 돈다.
   - 재현 B: 252 를 고르고 바로 로고(새 공고) → 빈 화면에서 "공부 시간을 바꾸지 못했어요. 지금 그림은 그대로예요" 알림이 나온다. 까닭: `redraw`(627)의 `store.answers[step]` 이 이미 지워져 `ai.has` 에서 TypeError가 나고, 그것이 실패 길로 잡힌다.
   - 고침: `reset` 맨 위에 `store.switching?.abort(); store.switching = null; budgetUI.busy(false);` 한 줄. 그러면 `runStep`·`send`·로고가 모두 이것을 지난다. 그리고 655 를 `if (ac.signal.aborted || store.controller) return;` 으로 바꾼다 (다른 단계가 도는 중이면 바꾸기를 버린다. 라디오 칸은 이미 `syncSwitch` 로 막혀 있다).
2. **늦게 온 바꾸기 응답이 새 공고의 받아 둔 사건(`store.runs`)에 들어간다.** `main.js:622` 의 `fetchLog` 는 받은 뒤 확인 없이 `store.runs.set` 한다. 그사이 `reset` 이 runs 를 비웠어도 옛 공고 사건이 다시 들어간다. 지금은 예시 공고 하나뿐이라 같은 글이 들어가 보이지 않지만, 공고가 둘이 되면 다른 공고의 그림이 뜬다.
   - 고침: 622 앞에 `if (signal.aborted) throw new DOMException('', 'AbortError');` (1번의 `reset` 이 abort 하므로 이것으로 막힌다). 더 단단히는 열쇠를 `${step}:${key}` 대신 요청 때의 `store.text` 와 묶는다.

## 고침 (이번 묶음 안에서)

3. **주소의 `?budget=` 값 하나로 2단계가 "연결이 끊겼어요"로 끝난다.** `main.js:573` `querySelector(\`[data-key="${asked}"]\`)` 에 따옴표가 든 값(`?budget=%22`)이면 선택자 오류가 처리기 안에서 터지고, `stream` 이 그것을 끊김으로 받는다 (실제로 재현함: 단추 셋은 그려졌는데 끝에 "연결이 끊겼어요"). 고침: `[...store.follow.querySelectorAll('[data-key]')].find((b) => b.dataset.key === asked)?.focus(...)`. 서버가 보낸 열쇠가 아닌 값은 아예 쓰지 않는다 (`store.budgets.some((b) => b.key === asked)` 일 때만 초점을 옮긴다).
4. **바꾸기 시험이 빠른 바꾸기의 경쟁을 실제로 돌리지 않는다.** `shots.py:1271-1282` "빠르게 두 번"은 앞의 왕복(1245-1264)이 세 안을 모두 `store.runs` 에 받아 둔 뒤라 `Promise.all` 이 바로 풀린다 (기다림 0, 경쟁 없음). 고침: 그 앞에서 `location.reload` 없이 runs 를 비울 수 없으니, 시험용으로 `Fetch.enable`(이미 `Page.cut` 이 씀)로 `/api/run` 을 0.5초 잡아 두고 (a) 168→252 를 빠르게, (b) 168 을 고르고 바로 `12주 계획 짜기`, (c) 252 를 고르고 바로 로고 를 본다. (b)는 ④⑤ 의 머리 숫자가 한 안의 저장본과 같은지, (c)는 알림 칸이 비었는지를 본다. 1·2번 고침의 회귀 시험이 된다.
5. **막힌 라디오가 말없이 되돌아간다.** `budget.js:18-21`: 3단계가 도는 중 화살표를 누르면 초점은 옆 칸으로 가고 고른 표시만 원래 칸으로 돌아간다. 화면 읽기 사용자는 "어둡게 표시됨"만 듣고 왜인지 모른다. 고침: 되돌릴 때 알림 칸에 "교육자료를 찾는 동안에는 바꿀 수 없어요" 한 번 (`main.js` 에 `onLocked` 콜백을 넘겨 `announce`). 초점은 고른 칸으로 되돌린다 (`box().querySelector(':checked')?.focus()`).

## 손볼 것

6. **멈춘 ⑤ 는 바꾸기에서 빠져 옛 안으로 남는다.** `main.js:650` 은 끝까지 그린 단계(`drawn`)만 다시 쓴다. 12주 계획을 멈춘 뒤 안을 바꾸면 ⑤ 쪽의 반쯤 그린 막대와 대화 칸 주별 표가 옛 한도선으로 남는다. 고침: 바꿀 때 `drawn` 에 없는 ARTS 쪽이 그려져 있으면 `reset({ from: 그 단계 })` 로 비우고 다시 하기 단추만 남긴다.
7. **`asked` 를 처음 한 번만 읽어 새 공고에도 따라간다.** `main.js:567`. 로고를 누르면 `setBudget(null)` 이 주소의 `?budget=` 을 지우는데, 다음 공고의 고르기 단추도 옛 값에 초점이 간다. 고침: `suggest` 안에서 `new URLSearchParams(location.search).get('budget')` 를 그때 읽는다 (주소가 진실 하나).
8. **회색 정리 뒤 남은 군더더기.**
   - `panel.css:296` 주석 "빌림(번호 배지: 16px 원, 12px 글)" — 실제는 `--fs-label`(13px). 주석을 13px 로.
   - `color: var(--ink)` 가 `--muted` 를 갈아 끼운 자리에 그대로 남았다 (`panel.css:14, 67, 70, 83, 185, 292, 306, 312` 등, panel.css 36곳·chat.css 38곳). 몸통 글색이 이미 먹이라 하는 일이 없다. 바탕색이 바뀌는 곳(`.badge.by-n` 처럼) 말고는 지운다.
   - `store.js:40` 주석 "12주 계획만 비운다"가 `resetReport` 위에 붙어 있다. `resetWeeks`(46) 위로 옮긴다.
9. **시험이 잘 된 점과 한 군데 걸리는 점.** 안마다 `parametrize`, 3·4단계 공부 합, 리포트는 공부 칸만 다름, 같은 안 되풀이 = 같은 사건 — 모두 쓰는 사람이 보는 사건 흐름을 본다 (좋음). 다만 `test_materials_step_replays_saved_items_in_plain_words` 의 `set(r) == {…열 개…}`(`tests/test_demo.py:430`)는 줄의 열쇠 이름을 통째로 묶어, 화면이 안 쓰는 열쇠 하나를 더해도 깨진다. "보내면 안 되는 열쇠(`hours_how`, `note`)가 없다"로 바꾼다.

## 확인한 것 (문제 없음)
- 84→168→252 를 받아 두지 않은 채 0.1초 간격으로 → 끝 상태 252 하나 (섞인 숫자 없음, `aria-busy` 남지 않음, 주소 `?budget=252`, 내 말풍선 "하루 3시간으로…").
- 84→252→84 뒤 대화·④·⑤ 글이 글자까지 같고, 대화 칸 자식 수 8·표 5·`data-lid` 73 이 그대로 (쌓이지 않음).
- 서버 경계 검사는 `server.py:65-68` 한 곳, 저장본 사전을 고치지 않음 (`test_same_budget_twice…`).

판정: **조건부 통과** — 1·2번(바꾸기를 `reset` 에서 멈추고, 기다린 뒤 다른 요청이 돌면 버리기)을 고치고 4번 시험을 더하면 낼 수 있다.
