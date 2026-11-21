# ui-ux-pro-max applied to: Claude.ai-style job-posting competency demo
Source: nextlevelbuilder/ui-ux-pro-max-skill, .claude/skills/ui-ux-pro-max/{SKILL.md, references/quick-reference.md, data/ux-guidelines.csv, data/typography.csv}.
Rule ids in `code` are quoted from the repo. "[mine]" = the repo has no rule; my extrapolation, not from the repo.
The repo is a search-tool/rule database; it gives no layout grid, no panel sizes, and no highlight-linking pattern.
## Priority order (SKILL.md table): 1 Accessibility, 2 Touch/Interaction, 3 Performance, 4 Style, 5 Layout, 6 Type/Color, 7 Animation, 8 Forms/Feedback.
Spend effort in that order. Style is Claude.ai-like: neutral, one accent, no emoji icons.
## 1. Layout and panels
- `container-width`/`spacing-scale`: use a 4/8 spacing scale and tokens; no ad hoc px values.
- `adaptive-navigation`: >=1024px shows chat column and side panel together; below that, stack or switch via tabs.
- `breakpoint-consistency`: 375 / 768 / 1024 / 1440.
- [mine] Desktop: chat 380-480px (flex, min 340) | panel flex-1 (min 480) | optional resizer. Panel about 55-60% at 1440.
- [mine] Panel header (title, source chip, copy/close) sticks; the body scrolls. The table lives in the same panel (tabs "공고 | 역량표") or in a lower half; with a split, drag the divider and keep keyboard +/- resize.
- `scroll-behavior`: avoid nested scroll regions that fight; give the panel and chat each ONE scroll container. `viewport-units`: min-h-dvh, not 100vh.
- `horizontal-scroll` + Table Handling (#71): no page-level horizontal scroll; wrap wide tables in `overflow-x-auto`, or switch to cards <768px.
- `fixed-element-offset` + `focus-not-obscured` (WCAG 2.2 AA): sticky headers/composer must not hide focused items; use `scroll-padding-top: var(--header-height)`.
## 2. Input flow (drop / paste / URL)
- `drag-threshold`, `gesture-feedback`: drop zone reacts in real time. States: idle (dashed border + "파일을 놓거나 붙여넣기") -> dragover (accent border, tinted bg, label "놓으면 업로드") -> uploading -> done/error.
- `dragging-alternative` (WCAG 2.2 AA): drag-drop must never be the only path. Add an "파일 선택" button, paste (Ctrl+V), and a URL field.
- `input-labels`/`input-helper-text`: visible label + persistent helper text ("PDF, DOCX, TXT, 10MB 이하 · URL 가능"), not placeholder-only.
- `ime-composition-enter`: Korean IME. Enter-to-send must check `isComposing`/keyCode 229 or the last syllable double-sends. Keep an explicit send button; Shift+Enter = newline.
## 3. Loading / progress / empty / error
- Loading Indicators (#78): match feedback to expected wait; no flashing spinner for near-instant work. Use "stable skeleton or progress with aria-busy".
- `progressive-loading`: skeleton instead of a blocking spinner for >1s. Posting panel shows text skeleton; table shows skeleton rows (`loading-chart` analog: no empty frame).
- `multi-step-progress` (#81): stages "읽는 중 -> 핵심 문장 찾는 중 -> 역량 추출 중" as "Step 2 of 3".
- Streaming (#93): stream chat text token by token; "Spinner until 100% complete" is the anti-pattern. Rows may appear one by one as highlights land.
- `content-jumping`/`layout-shift-avoid`: reserve space; rows inserted must not shove focused/active content.
- Empty States (#79): "helpful message and action", not blank. Panel empty: illustration-free text + 3 buttons (파일 선택 / 붙여넣기 / URL). Table empty: "하이라이트가 아직 없어요".
- `error-clarity`/`error-recovery`: state cause + fix + "다시 시도" (e.g. "이 URL은 로그인이 필요해 읽지 못했어요. 텍스트를 붙여넣어 보세요."). `timeout-feedback`: timeout shows retry.
- AI Disclaimer (#92): label AI-generated highlights/rows ("AI 추출 · 확인 필요").
## 4. Highlight <-> row mapping (repo silent; derived from its a11y rules)
- `color-not-only`/`color-not-decorative-only`: yellow alone is not enough. Add a numbered badge [1] superscript on each highlight and the same number in the table's first column.
- `contrast-readability`: dark text (slate-900-ish) on yellow bg; keep >=4.5:1 for text over highlight (`color-contrast`). Dark mode: use desaturated tonal yellow, not inverted (`color-dark-mode`).
- `hover-vs-tap`: hover must not be the only link. Click highlight -> select row (scrollIntoView, row tint + left accent bar); click row -> scroll posting to the mark and pulse it. Hover = preview only.
- Use `<mark>` with `tabindex=0`, `aria-describedby` -> row id; row `aria-selected`. `keyboard-nav`: Tab order = reading order; Arrow Up/Down moves between pairs [mine].
- `motion-meaning`/`excessive-motion`: one 300-500ms scroll+pulse as cause-effect, only 1-2 animated elements. `reduced-motion`: replace pulse with static outline.
- [mine] Overlapping/long sentences: clamp row preview, expand for full text (`truncation-strategy`: "prefer wrapping over truncation... tooltip/expand").
## 5. Data table
- `sortable-table`: sortable columns carry `aria-sort`. `data-table`: real `<table>` with `<th scope>`, caption; no div-grids.
- `visual-hierarchy`: columns [#, 역량, 분류, 근거 문장, 수준/중요도]. Use chip + icon for category (`color-not-only`).
- `chip-collection-reflow`/`compact-label-overflow`: tags wrap before shrinking; keep chips on one line each.
## 6. Korean typography
- Typography row #23 "Korean Modern": Noto Sans KR 300/400/500/700 (Pretendard is [mine], not in repo).
- `line-height` 1.5-1.75 (use ~1.7 Korean); `line-length` 65-75 chars: Latin-measured, Hangul ~35-45 chars/line [mine]; cap posting body ~ 40em.
- `readable-font-size` 16px body min; `font-scale` 12/14/16/18/24/32; `weight-hierarchy`: 400 body, 500 labels, 600-700 headings.
- `long-token-wrapping`: `overflow-wrap:anywhere` for URLs; Korean prose uses `word-break: keep-all` [mine], never `break-all` on prose.
- `text-reflow` (#112): no fixed-height clipped text; works at 200% zoom. Never disable zoom (`viewport-meta`).
## 7. Accessibility baseline
- `color-contrast` 4.5:1 normal, 3:1 large; `color-accessible-pairs` verify with a tool; `color-semantic`: tokens, no raw hex in components.
- `focus-states`: never `outline-none` without replacement. `focus-appearance`: >=2px, 3:1 indicator. `skip-links`; `heading-hierarchy`.
- `aria-labels` for icon-only buttons (copy, close, send); `icon-context`: decorative icons aria-hidden. `cursor-pointer` on clickables.
- `no-emoji-icons`, `icon-style-consistent`: one SVG set (Lucide). `state-clarity`: distinct hover/pressed/disabled (`disabled-states` opacity 0.38-0.5).
- `screen-reader-summary`-style: after analysis, announce "역량 N개 추출됨" in a polite live region (`contextual-live-badge-updates`), without moving focus.
## 8. Responsive
- `mobile-first`; `content-priority`: <768px show chat, with posting/table as full-screen sheets via tabs; `orientation-support`.
## Pre-delivery check
Contrast pass (light+dark) | full keyboard run of drop -> analyze -> link highlight/row | skeleton/empty/error screenshots | 375/768/1024/1440 no h-scroll | Korean IME Enter test | reduced-motion on.
