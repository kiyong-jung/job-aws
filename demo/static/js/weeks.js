// ⑤ 12주 계획 쪽 (사용자 11/21). 주마다 한 칸: 그 주의 배우기(교육자료)와 만들기(프로젝트 작업)를 한 칸에.
// 칸 아래 토글을 열면 목표·할 일·배우는 역량을 세 줄까지. 역량을 누르거나 마우스를 올리면 그 역량이 나온 공고 원문 문장을 작은 카드로 보인다.
// 시간·글은 모두 서버 값이다. 예시 공고의 주차 계획 md(source 'md')는 목표·할 일(학습·실습 방법)이 md 의 글이고, 작업이 끝나는 주에 산출물을 보인다.
// 생성기 결과(source 'generator')는 목표 = 만들기의 산출물, 할 일 = 만들기의 확인 기준과 배울 자료
import { el, play } from './icons.js';
import { chartCard, clearDoc } from './cards.js';
import { hoursText } from './tables.js';

const $ = (id) => document.getElementById(id);
const short = (h) => `${Math.round(h * 10) / 10}`;
const MAX = 3;
const TIER = { 필수: 0, 우대: 1, 나머지: 2 };
let s = null;
const holding = (tag, ...kids) => { const n = el(tag); n.append(...kids); return n; };

function list(items) {
  const ul = el('ul', { class: 'wk-lines' });
  items.slice(0, MAX).forEach((x) => ul.append(el('li', { text: x })));
  return ul;
}

function goals(acts) {
  const out = acts.filter((a) => a.kind === 'project' && a.out).map((a) => (a.done ? a.out : `${a.out} (다음 주까지)`));
  return out.length ? out : acts.filter((a) => a.kind === 'learning').map((a) => `「${a.title}」 공부 끝내기`);
}

function todos(acts) {
  return [...acts.filter((a) => a.kind === 'project' && a.check).map((a) => a.check),
    ...acts.filter((a) => a.kind === 'learning').map((a) => `「${a.title}」 공부 · ${hoursText(a.hours)}`)];
}

// 그 주 역량 (한 번씩, 필수 → 우대 → 나머지). '기초' 는 같은 역량의 기초만 다룬다는 표시
function weekComps(acts, comps) {
  const seen = new Map();
  for (const a of acts) for (const r of a.cids || []) if (comps[r.cid]) seen.set(r.cid, (seen.get(r.cid) ?? true) && r.basic);
  return [...seen].map(([cid, basic]) => ({ cid, basic, ...comps[cid] })).sort((x, y) => (TIER[x.tier] ?? 3) - (TIER[y.tier] ?? 3));
}

function chip(c) {
  const b = el('button', { type: 'button', class: 'wk-comp', 'data-cid': c.cid, 'data-tier': c.tier, 'aria-haspopup': 'dialog', 'aria-expanded': 'false' });
  b.append(el('span', { class: 'wk-tier', text: c.tier }), el('span', { text: c.basic ? `${c.name} 기초` : c.name }));
  return b;
}

function compLine(cs) {
  const p = el('p', { class: 'wk-comps' });
  cs.slice(0, MAX).forEach((c) => p.append(chip(c)));
  if (cs.length > MAX) {
    const rest = el('span', { class: 'wk-rest', hidden: '' });
    cs.slice(MAX).forEach((c) => rest.append(chip(c)));
    const more = el('button', { type: 'button', class: 'wk-more-comps', text: `+${cs.length - MAX}` });
    more.addEventListener('click', () => { rest.hidden = false; more.remove(); });
    p.append(more, rest);
  }
  return p;
}

// 한 줄: 배우기(자료 링크 · 시간) 또는 만들기(작업 이름 · 시간). md 계획은 끝나지 않은 작업에 끝나는 주, 끝나는 주에 산출물을 단다
function item(a, md, week) {
  const li = el('li', { class: 'wk-item', 'data-kind': a.kind });
  li.append(el('span', { class: 'g-kind', 'data-kind': a.kind, text: a.kind === 'learning' ? '배우기' : '만들기' }));
  const name = md && a.kind === 'project' ? `${a.id} ${a.title}` : a.title;      // md 의 목표·방법 글이 W2 처럼 작업 번호로 부른다
  li.append(a.url ? el('a', { href: a.url, target: '_blank', rel: 'noopener noreferrer', text: name }) : el('span', { class: 'wk-title', text: name }));
  li.append(el('span', { class: 'wk-h num', text: ` · ${hoursText(a.hours)}` }));
  if (md && a.kind === 'project' && !a.done && a.ends > week) li.append(el('span', { class: 'wk-ends', text: ` → ${a.ends}주에 끝` }));
  if (md && a.kind === 'project' && a.done && a.out) li.append(el('span', { class: 'wk-out', text: `산출물 · ${a.out}` }));
  return li;
}

function weekCard(w, cap, comps, md) {
  const used = w.learning + w.project;
  const card = el('article', { class: 'wk', 'data-over': String(used > cap + 1e-9), 'aria-label': `${w.week}주` });
  const head = el('header', { class: 'wk-head' });
  head.append(el('b', { class: 'wk-n', text: `${w.week}주` }), el('span', { class: 'wk-used num', text: `${hoursText(used)} / 상한 ${hoursText(cap)}` }));
  const items = el('ul', { class: 'wk-items' });
  w.activities.forEach((a) => items.append(item(a, md, w.week)));
  const more = el('details', { class: 'wk-more' });
  more.append(el('summary', { text: '목표 · 할 일 · 배우는 역량' }));
  const body = el('dl', { class: 'wk-body' });
  const cs = weekComps(w.activities, comps);
  body.append(el('dt', { text: '목표' }), holding('dd', list(md && w.goal ? [w.goal] : goals(w.activities))));
  body.append(el('dt', { text: '할 일' }), holding('dd', list(md && w.method ? [w.method] : todos(w.activities))));
  if (cs.length) body.append(el('dt', { text: '배우는 역량' }), holding('dd', compLine(cs)));
  more.append(body);
  card.append(head, items, more);
  return card;
}

// 역량 카드 (하나만). 마우스를 올리면 잠깐 보이고, 누르면 고정. Esc·바깥 누르기로 닫는다
function popover(root, comps) {
  const pop = el('div', { class: 'comp-pop', role: 'dialog', 'aria-label': '역량이 나온 공고 문장', hidden: '' });
  document.body.append(pop);
  let pinned = null;
  let timer = 0;
  const fill = (c) => {
    const head = el('p', { class: 'cp-head' });
    head.append(el('span', { class: 'wk-tier', 'data-tier': c.tier, text: c.tier }), el('b', { class: 'cp-name', text: c.name }));
    if (c.type) head.append(el('span', { class: 'cp-type', text: c.type }));
    const rows = c.said.map((q) => {
      const box = el('figure', { class: 'cp-said' });
      box.append(el('figcaption', { text: `공고 원문 · ${q.section}` }), el('blockquote', { text: q.text }));
      if (q.ko) box.append(el('p', { class: 'cp-ko', text: q.ko }));
      return box;
    });
    pop.replaceChildren(head, ...(rows.length ? rows : [el('p', { class: 'cp-ko', text: '공고 문장 번호가 없는 역량이에요.' })]));
  };
  const place = (btn) => {
    const r = btn.getBoundingClientRect();
    pop.hidden = false;
    const w = pop.offsetWidth, h = pop.offsetHeight, pad = 12;
    const left = Math.min(Math.max(pad, r.left), innerWidth - w - pad);
    const below = r.bottom + 8 + h < innerHeight - pad;
    pop.style.left = `${left}px`;
    pop.style.top = `${below ? r.bottom + 8 : Math.max(pad, r.top - h - 8)}px`;
  };
  const show = (btn) => {
    const c = comps[btn.dataset.cid];
    if (!c) return;
    fill({ ...c, name: btn.textContent.replace(/^(필수|우대|나머지)/, '') });
    place(btn);
  };
  const hide = () => {
    pop.hidden = true;
    pinned?.setAttribute('aria-expanded', 'false');
    pinned = null;
  };
  root.addEventListener('mouseover', (e) => {
    const b = e.target.closest('.wk-comp');
    if (!b || pinned) return;
    clearTimeout(timer);
    timer = setTimeout(() => show(b), 120);
  });
  root.addEventListener('mouseout', (e) => {
    if (!e.target.closest('.wk-comp') || pinned) return;
    clearTimeout(timer);
    timer = setTimeout(() => { if (!pinned) pop.hidden = true; }, 160);
  });
  root.addEventListener('click', (e) => {
    const b = e.target.closest('.wk-comp');
    if (!b) return;
    clearTimeout(timer);
    if (pinned === b) return hide();
    pinned?.setAttribute('aria-expanded', 'false');
    pinned = b;
    b.setAttribute('aria-expanded', 'true');
    show(b);
  });
  const outside = (e) => { if (pinned && !pop.contains(e.target) && !e.target.closest('.wk-comp')) hide(); };
  const esc = (e) => { if (e.key === 'Escape' && !pop.hidden) { pinned?.focus(); hide(); } };
  const away = () => { if (!pop.hidden) hide(); };
  document.addEventListener('click', outside);
  document.addEventListener('keydown', esc);
  addEventListener('scroll', away, { passive: true, capture: true });
  return () => {
    pop.remove();
    document.removeEventListener('click', outside);
    document.removeEventListener('keydown', esc);
    removeEventListener('scroll', away, { capture: true });
  };
}

// 계획 크기 고르기 (예시 공고의 주차 계획 md 가 둘 이상일 때: 중 · 주 14시간, 대 · 주 28시간). 진짜 라디오라 화살표 키로도 바뀐다
function planPick(plans, key, change) {
  const row = el('div', { class: 'plan-row' });
  const group = el('div', { class: 'plan-pick', role: 'radiogroup', 'aria-label': '계획 크기' });
  for (const p of plans) {
    const label = el('label', { class: 'budget-opt' });
    const input = el('input', { type: 'radio', name: 'week-plan', value: p.key });
    input.checked = p.key === key;
    input.addEventListener('change', () => change(p.key));
    label.append(input, el('span', { text: p.label }));
    group.append(label);
  }
  row.append(el('span', { class: 'plan-name', text: '계획 크기' }), group);
  return row;
}

function fillFact(fact, p) {
  const md = p.source === 'md';
  fact.replaceChildren();
  if (md) fact.append(`총 ${hoursText(p.total)} · `);
  fact.append(el('span', { class: 'g-kind', 'data-kind': 'learning', text: '배우기' }), ` 교육자료 ${hoursText(p.learning)}  `,
    el('span', { class: 'g-kind', 'data-kind': 'project', text: '만들기' }), ` 프로젝트 ${hoursText(p.project)}`,
    md ? ` · 한 주 상한 ${hoursText(p.cap)}` : ` · 한 사람, 한 주 ${short(p.cap)}시간`);
}

let chosen = null;      // 고른 계획 크기. 공부 시간을 바꿔 다시 그려도 남고, clear 가 지운다
let onPick = () => {};
// 계획 크기를 바꾸면 부를 것 (main.js 가 바닥 줄을 고친다). 인자는 고른 계획의 바닥 줄 수 (서버 값 summary)
export function picked(fn) { onPick = fn; }
let current = null;
// 지금 보이는 계획의 바닥 줄 수. 크기 고르기가 없는 계획이면 null (done 사건의 수를 쓴다)
export const summary = () => current;

export function start({ plans = [], comps = {}, default: first, ...one }) {
  s?.drop?.();
  const all = plans.length ? plans : [{ ...one }];
  if (!all.some((p) => p.key === chosen)) chosen = first ?? all[0].key;
  const root = $('weeks-doc');
  root.setAttribute('aria-busy', 'true');
  const fact = el('p', { class: 'wk-fact' });
  const held = el('p', { class: 'wk-held' });
  const grid = el('div', { class: 'wk-list', role: 'list' });
  const show = (key) => {
    chosen = key;
    const p = all.find((x) => x.key === key);
    current = plans.length ? p.summary : null;
    fillFact(fact, p);
    held.hidden = p.source !== 'md';
    held.textContent = `보류 작업 · ${p.held?.length ? p.held.map((h) => `${h.id} ${h.name}`).join(', ') : '없음'}`;
    grid.setAttribute('aria-label', `${p.plan.length}주 계획`);
    grid.replaceChildren(...p.plan.map((w) => weekCard(w, p.cap, comps, p.source === 'md')));
  };
  const body = all.length > 1 ? [planPick(all, chosen, (k) => { show(k); onPick(current); }), held, grid] : [held, grid];
  root.replaceChildren(chartCard(fact, body, { cls: 'wk-card', aside: true }));
  show(chosen);
  s = { root, drop: popover(grid, comps) };
  play(grid, [{ opacity: 0 }, { opacity: 1 }], 240);
}

export function done() {
  s?.root.removeAttribute('aria-busy');
}
export function stopped() {
  if (!s) return;
  s.root.removeAttribute('aria-busy');
  s.root.dataset.stopped = '';
}
export function clear() {
  s?.drop?.();
  s = null;
  current = null;
  clearDoc($('weeks-doc'));
}
