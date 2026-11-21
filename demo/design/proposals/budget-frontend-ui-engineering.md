# 공부 시간 고르기: 흐름·상태·시험 안 (frontend-ui-engineering 눈)

근거: `../budget_brief.md`, `../../DESIGN_RULES.md`, `../guides/frontend-ui-engineering.md`, `../reviews/v4-spec.md`, 코드(`pipeline.py`, `server.py`, `static/js/main.js`·`store.js`·`study.js`·`weeks.js`·`report.js`·`api.js`, `shots.py`, `../tests/test_demo.py`).
말과 그림 모양은 다른 안이 정한다. 이 안은 값이 어디서 오고, 어디에 살고, 바꿀 때 무엇이 다시 그려지는지만 정한다.

## 1. 한 줄로
- 숫자는 늘 서버가 저장본에서 보낸다. 화면은 고른 안의 열쇠(`"84"`·`"168"`·`"252"`)만 들고, 계산하지 않는다.
- 처음 고른 안은 지금처럼 흘려 받으며 자란다. **바꾸기는 다시 틀지 않는다**: 같은 사건을 `speed: 0` 으로 받아(또는 받아 둔 것을 꺼내) 끝 그림만 한 번에 바꾼다.
- 상태는 `store.js` 한 곳, 주소는 `?budget=168` 하나.

## 2. 요청과 서버
- `/api/run` 몸통에 `budget` 하나를 더한다: `{step: "materials"|"weeks"|"report", text, budget: "168", speed?}`. 새 길(endpoint)은 없다.
- `server.events`: 경계에서 한 번만 검사한다. `budget` 이 없으면 `"84"` (지금 시험이 그대로 통과), 저장본 열쇠에 없으면 `{"type":"error","reason":"budget","message":"공부 시간은 하루 1·2·3시간 중에서 고를 수 있어요."}` 하나로 끝낸다. 열쇠 목록은 `pipeline.budget_keys()` 가 `materials.json` 의 `budgets` 에서 읽는다 (박아 두지 않는다).
- `pipeline.materials/weeks/report(case, speed, budget="84")` 는 `data["budgets"][budget]` 만 읽는다. 공유되는 `lru_cache` 사전을 고치지 않는다 (같은 열쇠를 두 번 틀면 같은 사건, 시험으로 막는다).
- `project` 단계는 그대로다. 단 `done` 에 고르기 칸이 쓸 안 목록을 싣는다 (화면이 84·168·252 를 지어내지 않게).

### 사건 모양 (더하는 것만)
```
project.done    + budgets: [{key:"84", hours:84, per_day:1}, {key:"168", hours:168, per_day:2}, {key:"252", hours:252, per_day:3}]
materials.steps + budget_key:"168"            (budget 은 지금처럼 목표 시간 숫자 168, unit·total·big·small 은 그 안의 값)
materials.done  + budget_key, spare           (spare = budget − hours, 남는 시간을 화면이 빼지 않게)
weeks.steps     + budget_key                  (cap 은 그 안의 한 주 한도 14·21·28, study.hours 는 그 안의 공부 합)
weeks.done      + budget_key                  (지금 done.budget 은 팀 프로젝트 336 이라 이름을 겹치지 않게 budget_key 로 쓴다)
report.steps/done + budget_key                (line.row.study 만 안마다 다르다)
```
- 화면은 받은 `steps.budget_key` 가 보낸 값과 다르면 그 흐름을 버린다 (늦게 온 옛 응답 막기).

## 3. 상태 (`store.js`)
```js
budget: '84',          // 지금 고른 안. 주소 ?budget= 과 늘 같다 (setBudget 만 바꾼다)
drawn: new Set(),      // 이 공고에서 끝까지 그린 단계 ('materials' | 'weeks' | 'report')
runs: new Map(),       // `${step}:${budget}` → 사건 배열. done 까지 받은 것만 넣는다
answers: {},           // step → 그 단계의 대화 답 블록 (바꿀 때 그 자리를 다시 쓴다)
switching: null,       // 바꾸기 요청의 AbortController (store.controller 와 따로)
```
- `resetStudy()` 는 `drawn`·`runs`·`answers` 중 3단계 이후 것을 지운다. `resetResult()` 는 다 지우되 `budget` 은 남긴다 (사람이 고른 것이니 새 공고에도 따른다).
- 첫 흐름도 `stream()` 이 사건을 `ctx.log` 에 모아 `done` 때 `runs` 에 넣는다. 그래서 84 → 168 → 84 로 돌아올 때는 서버에 다시 묻지 않는다.

## 4. 고르기 → 첫 흐름
- 2단계 답 끝의 `교육자료 찾기` 단추 위에 고르기 칸 하나 (`project.done.budgets` 로 그림). 미리 골라 둔 값은 주소의 `?budget=` 이고, 없으면 `"84"` (지금 안 D).
- 단추를 누르면 `runStep('materials')` 가 `{step, text, budget: store.budget}` 을 보낸다. 이어지는 `12주 계획 짜기`·`정리 리포트 만들기` 도 같은 `store.budget` 을 보낸다.
- 단추를 누른 뒤 이 고르기 칸은 지금의 다음 단계 단추처럼 사라진다. 그 뒤로는 패널의 고르기 칸 하나만 산다 (한 화면에 둘 두지 않는다, S9).
- 패널 고르기 칸: ④ ⑤ ⑥ 쪽 머리(단계 길 아래, 상태 줄 자리 옆)에 같은 노드 하나. `panel.reveal` 이 그 세 쪽에서만 보인다. 좁은 화면(1024 아래)에서도 과정 보기에 있다.

## 5. 바꾸기 (다시 틀지 않고, 몇 번 해도 같게)
```js
async function switchBudget(key) {
  if (key === store.budget && !store.controller) return;          // 같은 값 → 아무 일 없음
  store.switching?.abort(); const ac = (store.switching = new AbortController());
  const steps = ['materials', 'weeks', 'report'].filter((s) => store.drawn.has(s) || running(s));
  store.controller?.abort();                                      // 자라는 중이면 멈추고 그 단계도 바꿀 거리에 넣는다
  busy(steps, true);
  try {
    const logs = await Promise.all(steps.map((s) => store.runs.get(`${s}:${key}`) ?? fetchLog(s, key, ac.signal)));  // speed: 0
    if (ac.signal.aborted) return;                                // 그사이 또 바꿨으면 늦은 쪽은 버린다
    const week = weeks.picked();
    instant(() => steps.forEach((s, i) => redraw(s, logs[i])));    // 세 쪽과 대화 답을 한 번에 (중간 상태가 화면에 없다)
    weeks.pick(week);                                             // 눌러 고른 주는 남긴다
    setBudget(key); announce(summary(logs));                      // 알림 한 번
  } catch (e) { if (e.name !== 'AbortError') { radio(store.budget); note(...) } }   // 실패하면 고르기를 되돌리고 옛 그림 그대로
  finally { if (store.switching === ac) { busy(steps, false); store.switching = null; } }
}
```
- `redraw(step, log)`: 그 단계 그림만 지우고(`study.clear()` 등, `store.items` 의 그 단계 몫), `chat.rewrite(store.answers[step])` 로 **같은 답 블록 안을 비운 뒤** 같은 처리기(`materialHandlers` 등)에 사건을 차례로 넣는다. 처리기 코드는 하나다 (바꾸기용 그리기를 따로 만들지 않는다).
- `ctx.quiet = true` 이면 처리기가 `openStep` 의 쪽 넘기기·초점 옮기기, 사건마다의 `announce`, `landed` 를 건너뛴다. 다음 단계 단추는 그 단계 다음이 아직 안 그려졌을 때만 다시 단다.
- `instant(fn)`: 그동안 `icons.reducedMotion()` 이 참을 돌려 `study.item`·`weeks.grow` 의 움직임이 꺼진다. 바꾸기 뒤 `document.getAnimations()` 은 비어 있다.
- 대화 기록에 표를 세 벌 쌓지 않으려고 답을 제자리에서 다시 쓴다 (U6). 대신 각 답 맨 위 한 줄 아랫줄에 고른 안 이름("하루 2시간 기준")을 넣어 기록이 무엇을 말하는지 남긴다. "바꿨다는 새 답을 덧붙이기"는 표가 쌓여 버렸다.
- 바뀌지 않는 것: ① ② ③ 쪽과 그 답, 패널의 지금 쪽(④ 를 보고 있었으면 ④ 그대로), 패널 열림, 초점(고르기 칸에 남는다).
- 몇 번 해도 같게: (1) 같은 값은 아무 일 없음, (2) 늦은 응답은 AbortController 와 `budget_key` 비교 둘로 버림, (3) `redraw` 는 늘 "지우고 처음부터" 라서 앞 상태에 기대지 않음, (4) 짝 지도(`link.js`)는 `link.clear()` 뒤 새 노드로만 다시 찬다.

## 6. 주소와 새로고침
- `setBudget(key)` 가 `history.replaceState` 로 `?budget=key` 를 맞춘다 (뒤로 가기 기록을 쌓지 않는다. 데모는 한 쪽 앱이다).
- 새로고침하면 대화는 비어 있다 (지금도 결과를 저장하지 않는다). `?budget=` 은 고르기 칸의 처음 값으로만 쓴다. 저장본 열쇠에 없는 값이면 `"84"`.
- 발표용으로 `?budget=252` 링크 하나로 그 안부터 보여 줄 수 있다.

## 7. 키보드·화면 읽기
- 진짜 라디오: `<fieldset class="budget"><legend>공부 시간</legend>` 안에 `<input type="radio" name="budget" value="168">` + `<label>` 셋. 화살표로 옮기면 고른 것이 바뀌는 것은 브라우저 기본 동작을 쓴다 (손으로 roving tabindex 를 만들지 않는다).
- 화살표를 빨리 두 번 눌러도 마지막 값만 남는다 (5절의 abort). 받아 둔 안은 곧바로, 처음 안은 서버에서 `speed: 0` 이라 짧다.
- 라벨은 "하루 2시간" 이 이름, "168시간" 은 같은 label 안 둘째 줄. `aria-describedby` 로 "바꾸면 교육자료·12주 계획·리포트가 함께 바뀌어요" 한 번.
- 바꾸는 동안 ④ ⑤ ⑥ 글에 `aria-busy="true"`, 끝나면 뗀다. 알림은 끝에 한 번: "하루 2시간으로 바꿨어요. 공부 N시간, 12주 중 M주는 한 주 한도 안이에요" (숫자는 `done` 사건 값).
- 손가락 칸 44px, 고른 칸은 채움 + 굵기로 (색만으로 가르지 않는다, S4). 포커스 고리는 지금 토큰 그대로.

## 8. 움직임 줄이기
- 바꾸기는 누구에게나 움직임이 없다 (끝 그림만). 그래서 움직임 줄이기에서 따로 할 일이 없다.
- 첫 흐름은 지금 규칙 그대로 (움직임 줄이기면 끝 그림만). 쪽 넘기기도 없다 (쪽이 그대로이니).

## 9. 시험 (pytest, `../tests/test_demo.py`)
`@pytest.mark.parametrize("key", pipeline.budget_keys())` 로 안마다:
- `materials`: `steps.budget == int(key)`, 큰 것 조각 누적이 늘기만 하고 마지막 `total == done.hours <= budget`, `done.spare == budget − hours`, 줄 수 = 그 안의 `items` 수, 자료 없는 수 = `found + missing` 짝. 252 는 실습 자료가 붙은 줄 수가 저장본과 같다.
- `weeks`: `cap` 이 그 안의 한 주 한도, `placed` 공부 합 = 같은 열쇠 `materials.done.hours` (단계 사이 숫자가 맞는지), `over` 를 저장본에서 다시 세어 같음.
- `report`: 줄의 `study` 이름 ⊂ 같은 열쇠의 교육자료 이름. 안을 바꿔도 `jobs`·`question`·`answer` 는 같다 (공부 줄만 바뀐다).
- 서버: `budget` 없음 = `"84"` 와 같은 사건, 이상한 값(`"100"`, `1e9`, `["84"]`)은 error 하나뿐이고 `steps` 가 없다.
- 같은 열쇠를 두 번, 그리고 다른 열쇠를 사이에 끼워 틀어도 사건이 같다 (캐시 사전을 고치지 않는다).

## 10. 사진과 짝 검사 (`shots.py`)
- 상태 이름: `30-budget-{key}-materials-{w}`, `31-budget-{key}-weeks-{w}`, `32-budget-{key}-report-{w}` × 1440·1024·390. 84 는 흘려 받은 끝, 168·252 는 바꾸기로 만든 끝 (두 길을 다 찍는다).
- 셈 일치 (안마다, 세 너비): ④ 머리 "{budget}시간 중 {N}" 의 N = 조각 `--w` 합 × budget = `done.hours`, 조각 수 = 그 안의 큰 것 수, "목표 {budget}시간" 글, 범례 두 수 합 = 큰 것 수. ⑤ 주마다 공부 `--h` 합 = 저장본, 한도 선 글 = `cap`, `[data-over]` 칸 수 = 대화 맨 위 줄의 넘는 주 수. 대화 맨 위 큰 숫자 = 패널 숫자 (같은 값이 다르게 쓰이지 않는다).
- 바꾸기 검사 (1440 한 번, 390 한 번):
  - 84 → 252 → 84 뒤 `#materials-doc`·`#weeks-doc`·`#report-doc` 의 innerText 와 3·4·5단계 답 블록 innerText 가 처음 84 와 글자 하나까지 같다.
  - 답 블록 수, `.grid.study`·`.grid.plan` 표 수가 바꾸기 전과 같다 (쌓이지 않음). `[data-lid]` 가 쪽마다 겹치지 않는다.
  - 바꾼 직후 `document.getAnimations()` 이 비고, `aria-busy` 와 `[data-now]` 가 남지 않는다. 지금 쪽(`STACK` 맨 위)과 초점(고른 라디오)이 그대로.
  - 화살표 오른쪽 두 번을 빠르게 → 끝 상태가 252 하나와 같다 (섞인 숫자 없음). 자라는 중에 바꾸기 → 흐름이 멈추고 바꾼 안의 끝 그림.
  - 주소가 `?budget=` 과 같다. `?budget=168` 로 열면 2단계 답 끝의 고르기 칸이 168 에 맞춰져 있다. `?budget=100` 은 84.
  - 390: 고르기 칸이 한 줄, 칸 높이 ≥ 44px, 넘침 없음. 움직임 줄이기(1440)에서 바꾸기·첫 흐름 모두 움직임 0.

## 11. 하지 않는 것
- 화면이 저장본 사본을 들고 안 사이를 계산하는 것 (숫자는 서버에서만, "낙관적 갱신 없음").
- 바꿀 때마다 다시 자라는 막대 (되풀이 움직임), 바꾼 내용을 새 답으로 덧붙이기, 같은 고르기 칸을 대화와 패널에 둘 다 두기.
