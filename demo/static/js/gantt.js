// ④ 12주 계획 간트차트 (사용자 11/22: "12주 계획 간트차트 형태로 보이도록 해줘"). 값은 모두 서버 계획 값이고 화면은 모으기만 한다.
// 열 = 학기 16주 (시험 7~8·15~16주는 띠 하나씩), 줄 = 프로젝트 작업 묶음(W1 …), 미룬 묶음은 맨 아래 "미룸" 한 줄.
// 막대 = 작업의 첫 주~끝 주, 칸 짙기 = 그 주에 그 작업에 쓴 시간(한 주 한도 몫). 끝나는 주에 마름모, 교육자료는 그 작업 줄의 동그라미.
// 막대·동그라미·주 머리·작업 이름은 모두 진짜 단추다 (누르면 오른쪽 옆 패널, peek.js).
import { el, reducedMotion } from './icons.js';
import { hoursText } from './tables.js';

export const SEM_WEEKS = 16;
const semOf = (w) => w.sem ?? w.week;
const LEVELS = 4;      // 칸 짙기 단계 (먹 55 · 70 · 85 · 100%, 모두 흰 바탕 3:1 이상, DESIGN_RULES S4)

// 계획 하나 → 간트 모델. rows: 작업 묶음 (배정 → 미룸 차례는 화면이 가른다), weeks: 학기 주 → 그 주 값
export function model(p) {
  const rows = new Map();
  const row = (id, init = {}) => {
    if (!rows.has(id)) rows.set(id, { id, name: id, short: '', do: '', out: '', held: false, hours: new Map(), done: 0, total: 0, comps: new Map(), mats: [], ...init });
    return rows.get(id);
  };
  for (const k of p.packages || []) row(k.id, { name: k.name, short: k.short, do: k.do, out: k.out, held: k.held });
  const weeks = new Map();
  for (const w of p.plan) {
    const n = semOf(w);
    weeks.set(n, w);
    for (const a of w.activities) {
      if (a.kind === 'project') {
        const r = row(a.id, { name: a.title });
        r.hours.set(n, (r.hours.get(n) ?? 0) + a.hours);
        r.total += a.hours;
        if (a.done) r.done = n;
        for (const c of a.cids || []) r.comps.set(c.cid, (r.comps.get(c.cid) ?? true) && c.basic);
      }
    }
  }
  const mats = new Map();      // 교육자료 id → {…활동, sem, week}
  for (const w of p.plan) {
    for (const a of w.activities) {
      if (a.kind !== 'learning') continue;
      const m = { ...a, sem: semOf(w), cap: p.cap };
      mats.set(a.id, m);
      rows.get(a.for)?.mats.push(m);
    }
  }
  const list = [...rows.values()];
  for (const r of list) {
    const ws = [...r.hours.keys()];
    r.first = ws.length ? Math.min(...ws) : 0;
    r.last = ws.length ? Math.max(...ws) : 0;
    r.done ||= r.last;
  }
  return { p, rows: list.filter((r) => !r.held), held: list.filter((r) => r.held), weeks, mats, byId: rows, md: p.source === 'md' };
}

export const label = (m, r) => (m.md ? `${r.id} ${r.short || r.name}` : r.short || r.name);
// 기존 배정 = 교육자료 단계(③)가 이미 고른 자료, 그 밖은 이 작업에 맞춰 더한 자료
export const picked = (a) => (a.why || []).some((t) => t.includes('기존 배정'));

const level = (h, cap) => Math.min(LEVELS, Math.max(1, Math.ceil((h / cap) * LEVELS)));

function button(cls, aria, data, kids = []) {
  const b = el('button', { type: 'button', class: cls, 'aria-label': aria, 'aria-pressed': 'false', ...data });
  b.append(...kids);
  return b;
}

// 막대 하나: 첫 주~끝 주를 한 단추로, 안은 주마다 칸 (시간이 없는 주는 이어 주는 선)
function bar(m, r, i) {
  const n = r.last - r.first + 1;
  const b = button('g-bar', `${label(m, r)} · ${r.first}주차부터 ${r.last}주차까지 · ${hoursText(r.total)} · 자세히 보기`, { 'data-peek': 'w', 'data-id': r.id });
  b.style.gridColumn = `${r.first + 1} / span ${n}`;
  b.style.gridRow = String(i + 2);
  const cells = el('span', { class: 'g-cells', 'aria-hidden': 'true' });
  cells.style.gridTemplateColumns = `repeat(${n}, minmax(0, 1fr))`;
  for (let w = r.first; w <= r.last; w++) {
    const h = r.hours.get(w);
    const c = el('span', { class: 'g-cell', 'data-w': w, ...(h ? { 'data-lv': level(h, m.p.cap), title: `${w}주차 · ${hoursText(h)}` } : { 'data-gap': '' }) });
    if (w === r.done) c.append(el('span', { class: 'g-done' }));
    cells.append(c);
  }
  b.append(cells);
  return b;
}

// 교육자료 동그라미: 그 작업 줄, 공부한 주 칸 아래. 한 칸에 여럿이면 가로로 (겹쳐 놓는다)
function marks(m, r, i, w, list) {
  const box = el('span', { class: 'g-marks', 'data-n': list.length, 'data-bar': r.hours.has(w) ? '' : null });
  box.style.gridColumn = String(w + 1);
  box.style.gridRow = String(i + 2);
  for (const a of list) {
    box.append(button('g-mark', `교육자료 · ${a.title} · ${hoursText(a.hours)} · ${picked(a) ? '교육자료 단계에서 고른 자료' : '작업에 맞춰 더한 자료'} · 자세히 보기`,
      { 'data-peek': 'm', 'data-id': a.id, 'data-picked': picked(a) ? '' : null }));
  }
  return box;
}

const key = (txt, mark) => {
  const s = el('span', { class: 'g-key-item' });
  s.append(mark, el('span', { text: txt }));
  return s;
};
// 그림 위 범례: 동그라미 둘, 칸 짙기, 끝나는 주
export function legend() {
  const box = el('p', { class: 'g-key', 'aria-label': '범례' });
  const dot = (picked_) => el('span', { class: 'g-mark g-key-mark', 'aria-hidden': 'true', 'data-picked': picked_ ? '' : null });
  const shades = el('span', { class: 'g-key-shades', 'aria-hidden': 'true' });
  for (let k = 1; k <= LEVELS; k++) shades.append(el('i', { 'data-lv': k }));
  box.append(key('교육자료 단계에서 고른 자료', dot(true)), key('작업에 맞춰 더한 자료', dot(false)), key('진할수록 그 주에 많이 해요', shades),
    key('끝나는 주', el('span', { class: 'g-done g-key-done', 'aria-hidden': 'true' })));
  return box;
}

// 간트차트 노드 하나. 막대·동그라미·주 머리·작업 이름이 단추. exams 는 [{from, to, label}]
export function chart(m, exams = []) {
  const root = el('div', { class: 'gantt', role: 'group', 'aria-label': `${m.p.plan.length}주 계획 간트차트` });
  const grid = el('div', { class: 'g-grid' });
  const exam = new Set(exams.flatMap((e) => Array.from({ length: e.to - e.from + 1 }, (_, k) => e.from + k)));
  const body = m.rows.length;
  const last = body + 2 + (m.held.length ? 1 : 0);      // 격자 줄 수 (머리 1 + 작업 + 미룸 한 줄 + 바닥)
  // 시험 띠: 머리부터 바닥까지 한 덩어리, 이름은 한 번
  for (const e of exams) {
    const band = el('div', { class: 'g-exam', role: 'img', 'aria-label': `${e.from}~${e.to}주차 ${e.label}, 계획 없음` });
    band.style.gridColumn = `${e.from + 1} / span ${e.to - e.from + 1}`;
    band.style.gridRow = `1 / ${last}`;
    band.append(el('span', { text: e.label }));
    grid.append(band);
  }
  // 머리: 학기 주. 계획이 있는 주는 단추 (그 주의 목표·방법·이유)
  const top = el('div', { class: 'g-line' });
  top.style.gridRow = '1';
  grid.append(top, el('div', { class: 'g-corner', text: '작업 묶음' }));
  for (let w = 1; w <= SEM_WEEKS; w++) {
    const has = m.weeks.has(w);
    const h = has ? button('g-head', `${w}주차 계획 자세히 보기`, { 'data-peek': 'week', 'data-id': w }, [document.createTextNode(String(w))])
      : el('span', { class: 'g-head', 'data-exam': exam.has(w) ? '' : null, text: String(w) });
    h.style.gridColumn = String(w + 1);
    h.style.gridRow = '1';
    grid.append(h);
  }
  m.rows.forEach((r, i) => {
    const line = el('div', { class: 'g-line' });
    line.style.gridRow = String(i + 2);
    const name = button('g-label', `${label(m, r)} 자세히 보기`, { 'data-peek': 'w', 'data-id': r.id, title: r.name });
    name.style.gridRow = String(i + 2);
    if (m.md) name.append(el('span', { class: 'g-id', text: r.id }));
    name.append(el('span', { class: 'g-name', text: r.short || r.name }));
    grid.append(line, name);
    if (r.last) grid.append(bar(m, r, i));
    const byWeek = new Map();
    for (const a of r.mats) byWeek.set(a.sem, [...(byWeek.get(a.sem) ?? []), a]);
    for (const [w, list] of byWeek) grid.append(marks(m, r, i, w, list));
  });
  if (m.held.length) {      // 미룸 한 줄: 점선 틀, 막대 없음
    const at = body + 2;
    const line = el('div', { class: 'g-line g-held-line' });
    line.style.gridRow = String(at);
    const tag = el('div', { class: 'g-label g-held-tag', text: '미룸' });
    tag.style.gridRow = String(at);
    const box = el('div', { class: 'g-held' });
    box.style.gridRow = String(at);
    for (const r of m.held) {
      const b = button('g-label g-held-chip', `${label(m, r)} · 12주 안에는 못 넣어서 미뤘어요 · 자세히 보기`, { 'data-peek': 'w', 'data-id': r.id, title: r.name });
      if (m.md) b.append(el('span', { class: 'g-id', text: r.id }));
      b.append(el('span', { class: 'g-name', text: r.short || r.name }));
      box.append(b);
    }
    grid.append(line, tag, box);
  }
  root.append(grid);
  return root;
}

// 막대가 왼쪽에서 오른쪽으로 자란다 (≤1.5초: 줄마다 80ms 늦게 시작, 한 줄 600ms). 움직임 줄이기면 끝 그림만
export function grow(root) {
  if (reducedMotion() || !root.getClientRects().length) return;
  root.querySelectorAll('.g-bar').forEach((b, i) => {
    b.animate([{ transform: 'scaleX(0)', opacity: 0.4 }, { transform: 'none', opacity: 1 }], { duration: 600, delay: i * 80, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'backwards' });
  });
  root.querySelectorAll('.g-marks').forEach((m, i) => {
    m.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 300, delay: 500 + (i % 12) * 60, fill: 'backwards' });
  });
}
