# c1 검토: 시험 주 + 정리 리포트 새 모양 (frontend-ui-engineering 눈, 2026-11-18)

읽은 것: `exam_brief.md`, `v6-report-spec.md` 1·5·9절, `pipeline.py` (weeks·weeks_text·mark_numbers·report), `static/js/{panel,link,report,main,store,weeks,tables}.js`, `static/css/panel.css`, `shots.py` 의 리포트·가고 오기 검사, `../tests/test_demo.py`.
돌린 것: pytest 119개 통과. 내 서버(8791)에 머리 없는 Chrome 으로 shots.py 의 `Page` 를 빌려 1440·390 에서 직접 눌러 봄 (shots.py 는 돌리지 않음). 스크립트 오류·실패한 요청은 0.

## 확인된 것 (고칠 것 없음)
- 가고 오기: R7 `공고에서 보기` → ① 이 맨 위, 형광펜 7 `data-active`·초점, 알림 "공고의 7번 문장이에요", `리포트로 돌아가기` 보임 → 누르면 ⑥, R7 펼침·초점 summary. 단계 길 6 으로 돌아와도 같음. ① 에서 형광펜 3 을 고른 뒤 `리포트에서 보기` → R3 펼침(R7 은 `name` 으로 접힘).
- 빠르게 누르기: `공고에서 보기`↔`리포트로 돌아가기` 30ms 간격 6번, 두 번 누르기 → 보이는 쪽은 `page-report` 하나, 펼친 줄 1, 초점 summary, 오류 없음.
- 펼친 줄을 둔 채 공부 시간 84→168: 펼친 R10·`scrollTop` 326 그대로, 라디오에 있던 초점 그대로.
- 리포트에 있다가 새 공고(로고): `#report-doc` 비움, `store.back` 비움(`resetReport`), 돌아가기 단추 숨김, 새 공고 끝에 단계 길은 ① 만 단추.
- 짝짓기가 echo 를 잡지 않음: 형광펜 6 에 올리면 `#doc` 의 `mark.hl[data-n=6]` 하나만 원문 짝, echo 는 리포트 줄(`details[data-lid]`)의 조각으로만 켜짐. echo 는 role·tabindex 없음, 줄 안에서 초점 받는 것은 summary 하나. summary 를 눌러도 `select` 안 됨(`link.js:149`).
- 붙는 머리: R9 펼치고 300px 내림 → summary 가 칸 맨 위(0px), 1440·390 모두. 390 에서 summary 92px·`공고에서 보기` 44px, 가로 넘침 0.
- 서버 쪽: 예시 숫자 밑줄 62개가 모두 숫자 경계에서 끊김 (앞뒤에 숫자 붙은 것 0).

## 반드시
없음.

## 고침
1. **리포트가 도는 중에 `공고에서 보기` 를 누르면 `리포트로 돌아가기` 가 끝까지 안 나온다 (재현함, 1440·390).** 3줄이 왔을 때 R2 → ① 로 감: 단추 숨김 (`main.js:53` 이 `store.drawn.has('report')` 를 봄, 아직 안 그림). 리포트가 끝나도 `reportHandlers.done`(`main.js:594` `finishRun`) 이 `offerReturn()` 을 부르지 않아 계속 숨김. 단계 길 6 으로는 돌아가지만 spec 5절의 단추가 없다.
   - 고침: `reportHandlers.done` 의 `finishRun(ctx, 'report')` 뒤에 `offerReturn();` 한 줄. shots `check_jump` 에 "도는 중에 가서 끝난 뒤 단추가 보인다" 한 경우.
2. **돌아온 뒤 다른 줄을 펼치면 강한 노랑 줄이 둘이다 (재현함).** R2 에서 ① 갔다 돌아와 R9 를 펼치면 R9(펼침)과 R2(`link.pick` 이 단 `data-active` 가 남음) 둘 다 `--hl-strong`·먹 배지, 나머지는 `--hl-soft`. spec 3절 "다른 줄을 볼 때 나머지 soft"와 어긋나고, 어느 줄이 지금 줄인지 흐려진다.
   - 고침: `main.js:43-46` 에서 `store.back` 을 쓰고 나서 `link.clear(); pickedN = null;` (돌아오면 ① 의 고름은 할 일을 다 했다). 또는 `report.js` 에서 줄의 `toggle`(열림) 때 다른 줄의 고름을 푸는 쪽. 앞쪽이 한 곳이라 작다.

## 손볼 것
3. **가고 오기 상태가 네 곳에 흩어져 있다.** `store.back`(store), `pickedN`·`chosen`(main.js 모듈 변수), `returning`(panel.js), 짝 `active`(link.js). 1·2 번 둘 다 이 넷이 서로 안 맞아 생겼다. `store.back = {lid, n}` 으로 두고 `main.js:54` 의 `Number(store.back.lid.slice(1))` 같은 글자 파싱을 없애고, `pickedN` 도 store 로 옮긴다 (가이드 2절 "상태는 store 한 곳").
4. **스크롤 계산이 세 벌.** `toPosting`(`main.js:71-72`), `report.reveal`(`report.js:161-164`), `panel.flush`(`panel.js:417-418`) 가 각자 rect 를 빼서 `scrollTop` 을 고친다. `link.js:85` `scrollInto` 를 내보내 쓰면 숨은 칸 건너뛰기·움직임 줄이기가 같이 따라온다.
5. **⑤ 좁은 화면 주 이름이 16칸에 안 맞다.** `panel.css:372` 는 1·4·9·12 만 보이고 마지막 일하는 주 14 는 이름이 없다. 주석(371 "1·4·8·12")도 틀림. `9`·`14` 정도로 바꾸고 주석을 맞춘다. `weeks.js:1·7` 의 "12주 세로 막대 하나" 도 "학기 16주 칸" 으로.
6. **`weeks_text` 는 시험 주만 덮는 범위면 빈 글을 낸다** (`pipeline.py:732`, `{"from":7,"to":8}` → `""`). 지금 저장본에는 없지만 화면에 " : …" 로 나온다. 빈 결과면 `ValueError` 를 내 저장본을 만들 때 막는다. 기본값 `exams=(7, 8, 15, 16)` 은 저장본과 겹치는 두 번째 진실이라 빼고 늘 넘긴다.
7. **Esc 가 아무것도 안 골랐을 때도 "선택을 풀었어요" 라고 말한다** (`link.js:153`, 리포트 summary 에서 Esc). `active || lit` 일 때만 `onSelect(null)`.

판정: 반드시 0, 고침 2 (둘 다 한두 줄). 고치고 shots 에 1번 경우를 더하면 통과.
