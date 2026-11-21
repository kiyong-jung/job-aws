# Demo v3 spec (lead synthesis of the five proposals)

Sources: v3-proposal-{frontend-design,taste-skill,ui-ux-pro-max,toss,frontend-ui-engineering}.md in this folder. Where they differ, this file decides. Read all five for detail and rationale.

## 1. Density and type (all five agree)
- Type scale in tokens.css only: 12 meta/captions, 13 table cells + labels + step list, 14 panel posting text, 15 chat body, 20 big numbers/section titles (600), 24 empty-screen hello. Composer textarea stays 16px (iOS zoom). Remove every other size. Line-heights: chat 1.6, panel doc 1.7, table 1.4.
- Table rows fixed ~32px (13px text, 6px vertical padding, weight 400; name may be 500). Badges shrink proportionally (20px tall).
- Toss TDS gives each size a role name (T5 17 일반 본문, T6 15 작은 본문, T7 13 "안 읽어도 됨"); the desktop step-down is our judgment — note it in README.

## 2. Each step answer = one glance (toss "한 화면 한 가지", all agree)
- Top of each answer: one big number + one line.
  - Step 1: **29** 역량 — "공고 29문장 중 핵심 19문장에서 찾았어요 · 필수 5 · 우대 7".
  - Step 2: **1** 개 — "89,659개 중 업무·자격 점수가 가장 높은 후보예요 (14점 중 5점)". Keep the honest line that no candidate passed half.
- Tables collapse: competency table shows 6 rows + button "29개 모두 보기" (aria-expanded). Coverage: a 29-cell coverage strip (있음/일부/없음 by fill + text alt) above a table that shows only 있음·일부 rows (10) + "없음 19개 보기". Ranking stays last, top 5, compact.
- link.js must expand a collapsed table when it needs to reveal a paired row.
- Chat progress list: compact (13px). When a step finishes, the list collapses to one line "4단계 끝 · 과정 보기" (expandable). No duplicate of what the panel shows in big.

## 3. Side panel = stack of views (fue shape)
- Views: ① 공고 (posting) → ② 프로젝트 찾기 (search visual) → ③ 샘플. `store.stack` is the single record; `panel.reveal(view)` the only mover. All views stay in the DOM (pairing keeps working); only the top is visible.
- Head: stage path "① 공고 읽기 › ② 프로젝트 찾기" (current bold) + back arrow "←" when depth > 1. Delete the old tab buttons.
- Push: new view slides in from the right (translateX 24px→0 + opacity, 280ms, ease-out); pop reverses. Transform/opacity only. prefers-reduced-motion: instant.
- 390px: panel is a separate view. Header toggle "대화 | 과정" (과정 = the panel stack, its own back arrow). Focus moves only on user action.

## 4. Step 1 panel
- Keep the live top-to-bottom highlighting. Add a counter line at the top: **19** "29문장 중 핵심 문장" updating live while reading.
- When done, non-highlighted sentences dim (ink at ~55%, still ≥4.5:1 on paper? if not, use --muted) so the 19 stand out. No minimap (complexity).

## 5. Step 2 panel: DB search visual (three scenes, driven by real stage events)
- Starting step 2 pushes view ②.
- Scene A (stage "DB 검색"): big **89,659** with "논문 68,145 · 저장소 21,514 중에서". Dot field: 1 dot = 1,000 → 68 paper dots + 22 repo dots (two inks, legend). Caption "점 하나 = 1,000개".
- Scene B (stage "후보 200"): the field zooms/fades into a 20×10 grid of 200 cells: **200** "가까운 후보". While judging (stage "판정"), cells fill in order; each filled cell's tone = that candidate's 업무·자격 score (0–14 → 4 tone steps). This needs all 200 tier-1 scores in demo data: copy them from outputs/project/naver_ml_intern.local.json ranking (real data) and emit per-batch progress events in the replay (40 batches of 5 = how the real run judged). Label "견줘 본 후보 n/200".
- Scene C (stage "고르기"): the top cell gets a ring (accent ink) and grows into the sample card (title, venue/year, 5.0/14). Clicking it pushes view ③ 샘플.
- One motion per event, no looping decoration, no DB cylinder icon, no fake count-up of numbers that were not computed. Reduced motion: final frame of each scene.
- Small caption under the visual: "저장된 실행을 다시 보여 줘요" (it is a replay; honesty).
- Drop the "검색어" count unless it is in saved data (it is in outputs/project/naver_ml_intern.search.json — copy if you show it).

## 6. Engineering
- Files: tokens.css, base/chat/panel/layout css, index.html, store.js (stack), panel.js (push/pop/reveal/visible; clearSample folds into reset), main.js (sync, onSelected, project handlers), link.js (scrollInto via panel.visible, expand collapsed tables), chat.js (one shared table shell with expand; dedupe the three tables), icons.js (if needed), pipeline.py (step-2 progress events + 200 scores), demo/data/naver_ml_intern.project.json (+scores), shots.py, tests/test_demo.py, README.md.
- Delete dead code (tabs, old view-toggle labels).
- shots.py: new shots for each scene at 1440/1024/390, collapsed/expanded tables, stack push/pop with back arrow, reduced-motion final frames; DOM checks: table heights (≤ one viewport at 1440 when collapsed), 200 grid cells, counts text matches data, back arrow pops, pairing still works when a collapsed row is targeted.
