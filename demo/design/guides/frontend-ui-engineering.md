# Rule sheet: frontend-ui-engineering (addyosmani/agent-skills) applied to the job-posting highlight demo
Sources read: skills/frontend-ui-engineering/SKILL.md and references/accessibility-checklist.md (raw.githubusercontent.com).
The skill is React/Tailwind-flavoured and has NO perf, SSE, testing-harness, or file-layout-for-vanilla guidance; those sections below are my adaptation (marked [adapt]).
## 1. Component structure
- Skill: "Prefer composition over configuration"; "Keep components focused" (one job); "Separate data fetching from presentation" (container vs presentational); Red flag: "Components with more than 200 lines (split them)".
- Map: ChatColumn, MessageList, Composer(drop/paste/URL), ArtifactPanel, PostingView (renders sentences), CompetencyTable, ProgressBar. Each = one ES module exporting `render(el, props)`-style pure function; a separate `api.js` (fetch/SSE/replay) is the only "container" layer.
- [adapt] Components are plain functions returning/patching DOM; no class hierarchy. Cap each module at ~200 lines.
- Use real elements: `<button>`, `<a>`, `<table>` with `<th scope>`, `<ul role="list">`. Skill: "NEVER use div/span as buttons".
## 2. State management (no framework)
- Skill ladder: "Choose the simplest approach that works": local -> lifted -> context -> URL -> server -> global store. "Avoid prop drilling deeper than 3 levels."
- [adapt] One `store.js`: a single plain object + `subscribe(fn)` + `dispatch(action)`; components subscribe to slices. Shared state needed by chat, panel, and table (so lifted/global rung): `messages`, `posting{sentences[]}`, `highlights[{id,sentenceId,competencyId}]`, `activeHighlightId`, `run{status,progress}`, `mode:'live'|'replay'`.
- Hover/click linking = one field `activeHighlightId`; both `<mark>` and table row read it and toggle `data-active`. Never query the other side's DOM directly.
- URL state for shareable bits: `?replay=case01` (skill: "URL state ... shareable UI state").
## 3. Accessibility (WCAG 2.1 AA, from skill + checklist)
- "Every interactive element must be keyboard accessible". Highlights: `<mark tabindex="0">` (or `<button class="hl">`), Enter/Space activates, Escape clears. Hover-only linking is a violation; mirror every hover with focus.
- Focus visible; no keyboard traps; skip-to-content link; `<html lang="ko">`; descriptive `<title>`; one `<h1>`, no skipped heading levels.
- Checklist: "Color is not the only way to convey information" -> yellow highlight also gets underline/border and a numbered badge `[3]` matching the table row; active state adds outline.
- Contrast: "4.5:1 for normal text, 3:1 for large text"; yellow background must keep dark text >=4.5:1 (check, "Do not round a failing contrast ratio up").
- Live regions: streaming progress in `role="status"` / `aria-live="polite"`; errors in `role="alert"`. "Dynamic content changes announced".
- Drop zone: must also have a visible `<label>`ed file `<input type=file>` and URL `<input>` ("Every input has a visible label"); icon buttons need `aria-label`; paste works on focused composer.
- Touch targets >=44x44px; text resizable to 200%.
- "Meaningful empty and error states": empty panel ("공고를 붙여넣거나 파일을 놓으세요"), error with retry; no blank screens. Loading = skeleton with `aria-busy="true"` ("Skeleton loading (not spinners for content)").
- Tables: `<th scope="col|row">`, caption.
## 4. Performance [adapt; skill only says "Shadow-heavy design ... slows rendering"]
- Render posting once; toggle highlight state via `data-active` / class on existing nodes, don't re-render the whole panel on hover.
- Use one delegated listener on the panel/table (`mouseover`/`click` + `closest('[data-hl]')`).
- SSE: append events to store, batch DOM updates with `requestAnimationFrame`; mark highlights incrementally as they stream in.
- Avoid shadows/gradients heavy effects; no web-font CDN (vendor Pretendard/Noto Sans KR subset locally, `font-display: swap`, system-ui fallback).
## 5. CSS architecture
- Skill: "Use semantic color tokens ... not raw hex values"; "Consistent spacing scale. Don't invent values" (0.25rem increments; bad: `13px`); "Consistent border-radius"; Red flag: "Inline styles or arbitrary pixel values".
- Files: `css/tokens.css` (:root custom properties: --color-surface, --color-text, --color-hl-yellow, --color-hl-active, --space-1..8, --radius-1..3, --font-body, --z-*), `base.css` (reset, type scale h1->small), `layout.css` (grid: `grid-template-columns: minmax(320px,1fr) 1.4fr`), `components/*.css`. Dark mode by overriding tokens only.
- Anti-AI aesthetic table: no purple/indigo default, "Flat or subtle gradients", no rounded-2xl everywhere, "Subtle or no shadows", "Realistic placeholder content" (use a real Korean posting, never lorem ipsum), "Content-first layouts". Claude.ai-like = neutral warm greys, one accent, but do not copy branding (skill: "Never copy another product's branding... or exact layout").
- Write a short design contract first: screen job, primary action (analyze posting), states (empty/loading/streaming/done/error), responsive rules, rejected patterns.
- Mobile-first: below ~768px stack chat above panel (tab switch); test 320 / 768 / 1024 / 1440.
- Typography: Korean needs `word-break: keep-all; line-height: 1.7`; `overflow-wrap: anywhere` for URLs.
## 6. File organisation [adapt; skill: "Colocate everything related to a component"]
```
web/
  index.html            (lang=ko, <script type=module src=js/main.js>)
  css/ tokens.css base.css layout.css components/
  js/  main.js store.js api.js(sse+replay) ; components/chat.js panel.js table.js composer.js
  vendor/ fonts/ (any lib vendored, no CDN)
  replay/ case01.json   (recorded events: same shape as SSE events)
  tests/ shots.py  checks.mjs-free (python only)
server.py               (http.server: static + /api/events SSE + /api/analyze)
```
- Replay mode = same event stream read from `replay/*.json` with timers; UI cannot tell live from replay. Works with zero network.
## 7. Streaming progress [adapt]
- SSE (`EventSource`) via ThreadingHTTPServer, headers `Content-Type: text/event-stream`, `Cache-Control: no-cache`, flush per event; fall back to polling `/api/status` if EventSource fails. Events: `progress`, `sentence`, `highlight`, `competency`, `done`, `error`.
- Optimistic/skeleton states keep UI responsive ("Optimistic updates for perceived speed").
## 8. Verification (skill: "Verify With What the Project Has", "Don't install a framework... just to check")
Skill checklist to tick: renders without console errors; Tab through page; screen reader conveys structure; responsive at 320/768/1024/1440; loading/empty/error/success states; follows tokens; no a11y warnings.
- [adapt] Headless Chrome screenshots (no npm needed):
  `chrome --headless=new --screenshot=out.png --window-size=1440,900 --virtual-time-budget=5000 "http://localhost:8000/?replay=case01"` at 4 widths; then LOOK at images (Read tool).
- Console errors: `--enable-logging=stderr --v=0` and grep for `CONSOLE`; or `--dump-dom` and assert expected `<mark>` count == table rows.
- Linking test: use `--remote-debugging-port` + a tiny Python CDP script, or an `?autotest=1` hook that dispatches click and dumps DOM with `data-active`.
- State each screenshot covers: empty, streaming (mid-replay), done, error, narrow mobile. Say which checks (axe, screen reader) could not be run; don't claim them.
- Final "UI-specific finish-gate review": inspect the screenshots for overflow, Korean wrapping, contrast, yellow-highlight legibility.
