# taste-skill rule sheet: Claude.ai-style job-posting demo
Source: Leonxlnx/taste-skill v2.5.1 (SKILL.md, references/system.md, motion.md, cards.md, copy.md).
Caveat: the skill targets marketing sites (heroes, photos, deal/gate scripts); only its taste rules apply here. [CONFLICT] = skill vs brief; brief wins.

## Colour and restraint
1. "The interface stays 90 to 95% neutral; colour comes from ... the work." Chrome = warm off-white/white + one warm near-black ink (~#2b2a27); colour only in highlights and mapping.
2. "One near-black ink, never #000"; hairlines "12 to 15% of it" (1px rgba(ink,.12)).
3. "One accent at most ... under 3% of a screen": Claude clay (~#c96442) only for send/primary button and focus ring.
4. [CONFLICT] "Highlight by contrast, never by colour: no marker highlights." Brief needs yellow: use soft yellow (~#fde68a at 70%), 3px radius, no border, text stays full ink (7:1). Never #ff0 saturated.
5. "Never violet or lavender"; no gradients, glass, blur, glow, neon.

## Typography (Korean-heavy)
6. "Text people read is 16px or more, line height 1.5 to 1.8, ink at 7:1. Never 14px paragraphs or 15px grey card text." Posting 16/1.75, chat 16/1.65.
7. "--muted only for labels, dates, meta"; "Nothing under 13px"; labels 13px/500, "never tracked capitals". No letter-spacing on Hangul (0 to -0.01em).
8. "Lines at most 62 characters": Korean ~36-40 chars (max-width ~38em). Use word-break: keep-all; overflow-wrap: anywhere.
9. "One size per kind of element", "one heading scale": only 13 / 16 / 20 / 28px and weights 400/500/600.
10. One font pairing, "faces loaded": Pretendard Variable for UI and body; optional Noto Serif KR for posting title/assistant prose only. tabular-nums for numbers.
11. "A number never breaks from its unit": nowrap on "3년 이상", "5,000만원". "Every word is live text."

## Spacing and one system
12. Scale only: "4, 8, 12, 16, 24, 32, 48, 64, 96". Panel padding "never under 24"; chat turn gap 24; table row padding 12-16.
13. "One button shape, one radius family, one card recipe, one hairline, one link look." Radii 8/12/20 only.
14. "Equal left and right content edges": chat, input, panel text and table share the same gutters.
15. "Everything lines up; one height per row kind": fixed table column grid, equal row heights.
16. Card = "barely there: one step off the page, a hairline, generous padding"; "No blurred shadow at rest"; hover shadow max blur 24px, 10% ink.
17. "Two levels, never three": panel > table > chip is the limit; no card-in-card for text; "never glass".
18. Header: "opaque ground, 1px hairline from first paint ... no blur, transparency, shrink, shadow". Panel header same.

## Motion (every motion needs a purpose; "a motion with no purpose is cut")
19. Timings: hover in 150ms, out 120ms, press 90ms, panel 200ms, indicator 240ms. Ease cubic-bezier(.2,.8,.2,1); entrance (.22,1,.36,1). "No bounce, no overshoot." Animate transform/opacity/colour only, "never width, height, top, left, margin, padding".
20. Buttons: "fill steps 14% toward ink, lifts 1px; press sinks 1px, scale .985"; linked card lifts 2px; link underline "draws left to right". Fine pointer only; keyboard focus shows same state.
21. Focus: "2px ring in the action colour, 2px off the control", no transition. Field: border + "3px soft ring, 140ms".
22. Entrance once: content "fades up 12px, 520ms each, 60ms apart"; panel slides in 200-240ms. No loader.
23. Signature moment: highlights wipe in sentence by sentence (~120ms stagger, background-size wipe), then each table row fades up. Shared number badge (1,2,3) on sentence and row. Hover/focus either side: that pair darkens a step, others dim to ~55%; posting scrolls to the sentence (240ms). Thin connector only on hover.
24. "No typing dots, no lone pulsing dot, no block cursor." One spinner (1s) or skeleton while parsing; streaming text is the only loop.
25. "Scrolling moves nothing": no scroll-reveal, parallax, scroll-jack, snap. Reduced motion: "everything rests and nothing stays hidden".

## Inputs and states
26. "A placeholder is never the label"; icon-only buttons get aria-label in Korean.
27. Errors "under their field", checked on submit, naming the fix ("주소는 https:// 로 시작해야 해요"). "A failure keeps everything typed." "Never a modal."
28. One status line, role="status": "분석 중... 문장 12개를 찾았어요".
29. Buttons 44px high, 16px label; "exactly one filled button marks the main action"; never gradient/ghost/shadowed.
30. Drop zone: the chat input itself at rest; dashed hairline only on drag-over.

## Copy (Korean)
31. "Say what it is ... in words a stranger understands in five seconds." Buttons "a verb plus what you get": "공고 분석하기", "역량 표 내보내기"; never "더 알아보기".
32. "Headings name things" (공고 원문 / 추출된 역량); card/row titles verb+object or short noun phrase, one line, plus one evidence line.
33. No slop words ("혁신적인", "원활한"), no invented figures, no "(sample)" or lorem visible.

## Anti-patterns
- Fade-in on every card, parallax, tilt, carousels, blinking, glow or shine sweeps.
- Gradients, glass, blur, coloured bars behind text, rest shadows, emoji as icons, mixed icon strokes.
- Redrawn look-alike logos (don't redraw Claude's mark; use a neutral text mark).
- Three radii, two button styles, many greys, 14-15px grey paragraphs, text shrunk to fit.
- Marketing hero, big centred headlines, stat strips, captions under visuals.
- Self-check: next to real Claude.ai nothing tilted, cut or overlapping; no overflow at 1440 and 390; Tab ring visible; highlight count equals table row count (1:1).
