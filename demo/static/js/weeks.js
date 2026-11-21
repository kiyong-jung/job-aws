// ⑤ 12주 계획 쪽 (사용자 11/21). 주마다 한 칸: 그 주의 배우기(교육자료)와 만들기(프로젝트 작업)를 한 칸에.
// 칸 아래 토글을 열면 목표·할 일·배우는 역량을 세 줄까지. 역량을 누르거나 마우스를 올리면 그 역량이 나온 공고 원문 문장을 작은 카드로 보인다.
// 시간·글은 모두 서버 값이다. 예시 공고의 주차 계획 md(source 'md')는 목표·할 일이 md 의 목표·학습·실습 방법을 연결 어미에서 나눈 개조식 줄(세 줄까지)이고,
// 작업이 끝나는 주에 산출물을 보인다. 계획이 여럿이면(주 7·14·28시간) 머리에 한 주 공부 시간 고르기와 고른 안의 분량 한 줄(line). 7 은 보류 안내 글.
// 칸 모양은 디자이너 셋 합의 (11/21, design/readability/merged.md): 줄마다 칠한 알약 대신 배우기 / 만들기 묶음 머리, 이름 | 오른쪽 시간 칸
// 생성기 결과(source 'generator')는 목표 = 만들기의 산출물, 할 일 = 만들기의 확인 기준과 배울 자료
import { el, icon, play } from './icons.js';
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
    const more = el('button', { type: 'button', class: 'wk-more-comps', text: `+${cs.length - MAX}개 더` });
    more.addEventListener('click', () => { rest.hidden = false; more.remove(); });
    p.append(more, rest);
  }
  return p;
}

// 한 줄: 이름 | 오른쪽 시간. 만들기 이름은 작업 번호와 함께 (md 의 목표·방법 글이 W2 처럼 번호로 부른다).
// md 계획은 작업이 처음 나온 주에만 이름 뒤에 끝나는 주 ("· 3주차까지", 따로 줄을 두지 않는다), 끝나는 주에 산출물 한 줄 (두 줄까지, 토글을 열면 다)
function item(a, md, week, first) {
  const li = el('li', { class: 'wk-item', 'data-kind': a.kind });
  const name = md && a.kind === 'project' ? `${a.id} · ${a.title}` : a.title;
  const n = a.url ? el('a', { class: 'wk-name', href: a.url, target: '_blank', rel: 'noopener noreferrer', text: name }) : el('span', { class: 'wk-name', text: name });
  if (md && a.kind === 'project' && !a.done && a.ends > week && first) n.append(el('span', { class: 'wk-ends', text: ` · ${a.ends}주차까지` }));
  li.append(n, el('span', { class: 'wk-h num', text: hoursText(a.hours) }));
  if (md && a.kind === 'project' && a.done && a.out) li.append(el('span', { class: 'wk-out', title: `산출물 · ${a.out}`, text: `산출물 · ${a.out}` }));
  return li;
}

// 칸 안 묶음 하나: 머리 "배우기 · 1시간 20분" 과 그 줄들. 빈 묶음은 그리지 않는다
function group(kind, acts, hours, md, week, seen) {
  if (!acts.length) return [];
  const sec = el('section', { class: 'wk-group', 'data-kind': kind });
  sec.append(el('h4', { class: 'wk-group-h', text: `${kind === 'learning' ? '배우기' : '만들기'} · ${hoursText(hours)}` }));
  const ul = el('ul', { class: 'wk-items' });
  acts.forEach((a) => { ul.append(item(a, md, week, !seen.has(a.id))); seen.add(a.id); });
  sec.append(ul);
  return [sec];
}

function weekCard(w, cap, comps, md, seen = new Set()) {
  const used = w.learning + w.project;
  const over = used > cap + 1e-9;
  const card = el('article', { class: 'wk', 'data-over': String(over), 'aria-label': `${w.week}주` });
  const head = el('header', { class: 'wk-head' });
  head.append(el('b', { class: 'wk-n', text: `${w.week}주` }), el('span', { class: 'wk-used num', text: over ? `${hoursText(used)} · ${hoursText(used - cap)} 넘음` : hoursText(used) }));
  const more = el('details', { class: 'wk-more' });
  more.append(el('summary', { text: '목표 · 할 일 · 배우는 역량' }));
  const body = el('dl', { class: 'wk-body' });
  const cs = weekComps(w.activities, comps);
  body.append(el('dt', { text: '목표' }), holding('dd', list(md && w.goal_steps?.length ? w.goal_steps : goals(w.activities))));
  body.append(el('dt', { text: '할 일' }), holding('dd', list(md && w.method_steps?.length ? w.method_steps : todos(w.activities))));
  if (cs.length) body.append(el('dt', { text: '배우는 역량' }), holding('dd', compLine(cs)));
  more.append(body);
  const of = (k) => w.activities.filter((a) => a.kind === k);
  card.append(head, ...group('learning', of('learning'), w.learning, md, w.week, seen), ...group('project', of('project'), w.project, md, w.week, seen), more);
  return card;
}

// 역량 카드 (하나만). 마우스를 올리면 잠깐 보이고, 누르면 고정. Esc·바깥 누르기로 닫는다
function popover(root, comps) {
  const pop = el('div', { class: 'comp-pop', role: 'dialog', 'aria-label': '역량이 나온 공고 문장', hidden: '' });
  document.body.append(pop);
  let pinned = null;
  let timer = 0;
  // 머리 = 필수·우대 태그 + 이름 (분류 낱말 '수행' 은 쓰지 않는다), 닫기 단추. 문장마다 한국어 먼저, 그 아래 영어 원문 (노랑 띠)
  const fill = (c) => {
    const head = el('p', { class: 'cp-head' });
    head.append(el('span', { class: 'wk-tier', 'data-tier': c.tier, text: c.tier }), el('b', { class: 'cp-name', text: c.name }));
    const close = el('button', { type: 'button', class: 'cp-close', 'aria-label': '닫기' }, icon('x'));
    close.addEventListener('click', () => { pinned?.focus(); hide(); });
    const rows = c.said.map((q) => {
      const box = el('figure', { class: 'cp-said' });
      box.append(el('figcaption', { text: `공고 원문 · ${q.section}` }));
      if (q.ko) box.append(el('p', { class: 'cp-ko', text: q.ko }));
      box.append(el('blockquote', { text: q.text }));
      return box;
    });
    pop.replaceChildren(head, close, ...(rows.length ? rows : [el('p', { class: 'cp-ko', text: '공고 문장 번호가 없는 역량이에요.' })]));
  };
  // 칩 아래에 두고, 자리가 모자라면 위로. 바닥 줄(.foot) 위에서 끝난다. 휴대폰은 css 가 아래 시트로 둔다
  const place = (btn) => {
    const r = btn.getBoundingClientRect();
    pop.hidden = false;
    pop.scrollTop = 0;
    const foot = btn.closest('.page')?.querySelector('.foot:not([hidden])');
    const floor = Math.min(innerHeight, foot && !btn.closest('.page').hasAttribute('data-foot-away') ? foot.getBoundingClientRect().top : innerHeight);
    const w = pop.offsetWidth, h = pop.offsetHeight, pad = 16;
    const left = Math.min(Math.max(pad, r.left), innerWidth - w - pad);
    const below = r.bottom + 8 + h <= floor - pad;
    pop.style.left = `${left}px`;
    pop.style.top = `${below ? r.bottom + 8 : Math.max(pad, Math.min(r.top - h - 8, floor - pad - h))}px`;
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
  pop.addEventListener('mouseover', () => clearTimeout(timer));      // 카드 위로 옮겨 가는 동안 닫지 않는다 (닫기 단추를 누를 수 있게)
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

// 한 주 공부 시간 고르기 (예시 공고의 주차 계획 md 가 둘 이상일 때: 주 7·14·28시간, 7 은 보류 안내). 진짜 라디오라 화살표 키로도 바뀐다
function planPick(plans, key, change) {
  const row = el('div', { class: 'plan-row' });
  const group = el('div', { class: 'plan-pick', role: 'radiogroup', 'aria-label': '한 주 공부 시간' });
  for (const p of plans) {
    const label = el('label', { class: 'budget-opt' });
    const input = el('input', { type: 'radio', name: 'week-plan', value: p.key });
    input.checked = p.key === key;
    input.addEventListener('change', () => change(p.key));
    label.append(input, el('span', { text: p.label }));
    group.append(label);
  }
  row.append(el('span', { class: 'plan-name', text: '한 주 공부 시간' }), group);
  return row;
}

// 주 칸 열두 개의 토글을 한 번에 열고 닫는다 (열린 칸만 길어져 격자가 들쭉날쭉하지 않게)
function allToggle(grid) {
  const b = el('button', { type: 'button', class: 'wk-all', 'aria-pressed': 'false', text: '모두 펼치기' });
  b.addEventListener('click', () => {
    const open = b.getAttribute('aria-pressed') !== 'true';
    grid.querySelectorAll('.wk-more').forEach((d) => { d.open = open; });
    b.setAttribute('aria-pressed', String(open));
    b.textContent = open ? '모두 접기' : '모두 펼치기';
  });
  return b;
}

function fillFact(fact, p) {
  const md = p.source === 'md';
  fact.replaceChildren();
  if (p.source === 'blocked') { fact.append(p.blocked.title); return; }
  if (md) fact.append(`총 ${hoursText(p.total)} · `);
  fact.append(el('span', { class: 'g-kind', 'data-kind': 'learning', text: '배우기' }), ` 교육자료 ${hoursText(p.learning)}  `,
    el('span', { class: 'g-kind', 'data-kind': 'project', text: '만들기' }), ` 프로젝트 ${hoursText(p.project)}`,
    md ? ` · 한 주 상한 ${hoursText(p.cap)}` : ` · 한 사람, 한 주 ${short(p.cap)}시간`);
}

// 계획을 보류한 시간(주 7시간): 주 칸 대신 본문 글 (오류가 아니라 그 시간으로는 짜지 않았다는 결과). 글은 서버 값.
// "보류했어요"·한 주 최소 시간은 바닥 줄이 말하므로 여기서는 까닭과 다시 짜는 길만
function blockedNote(b) {
  const box = el('section', { class: 'wk-blocked', 'aria-label': b.title });
  box.append(...b.lines.map((t) => el('p', { text: t })));
  return box;
}

let chosen = null;      // 고른 한 주 공부 시간(계획 열쇠). 하루 공부 시간을 바꿔 다시 그려도 남는다
let onPick = () => {};
// 한 주 공부 시간을 바꾸면 부를 것 (main.js 가 바닥 줄을 고친다). 인자는 고른 계획의 바닥 줄 수 (서버 값 summary)
export function picked(fn) { onPick = fn; }
let current = null;
// 지금 보이는 계획의 바닥 줄 수. 시간 고르기가 없는 계획이면 null (done 사건의 수를 쓴다)
export const summary = () => current;
// 고른 한 주 공부 시간의 열쇠 ("14"). ⑥ 리포트가 이 안으로 그린다 (main.js)
export const planKey = () => chosen;

export function start({ plans = [], comps = {}, default: first, ...one }) {
  s?.drop?.();
  const all = plans.length ? plans : [{ ...one }];
  if (!all.some((p) => p.key === chosen)) chosen = first ?? all[0].key;
  const root = $('weeks-doc');
  root.setAttribute('aria-busy', 'true');
  const fact = el('p', { class: 'wk-fact' });
  const line = el('p', { class: 'wk-line' });
  const grid = el('div', { class: 'wk-list', role: 'list' });
  const note = el('div', { class: 'wk-blocked-slot' });
  const all12 = allToggle(grid);
  const show = (key) => {
    chosen = key;
    const p = all.find((x) => x.key === key);
    current = plans.length ? p.summary : null;
    fillFact(fact, p);
    line.textContent = p.line || '';
    grid.hidden = p.source === 'blocked';
    all12.hidden = p.source === 'blocked';
    all12.setAttribute('aria-pressed', 'false');
    all12.textContent = '모두 펼치기';
    note.replaceChildren(...(p.source === 'blocked' ? [blockedNote(p.blocked)] : []));
    grid.setAttribute('aria-label', `${p.plan.length}주 계획`);
    const seen = new Set();      // 앞 주에 이미 나온 작업 (끝나는 주는 처음 나온 주에만 말한다)
    grid.replaceChildren(...p.plan.map((w) => weekCard(w, p.cap, comps, p.source === 'md', seen)));
  };
  const row = all.length > 1 ? planPick(all, chosen, (k) => { show(k); onPick(current, k); }) : el('div', { class: 'plan-row' });
  row.append(all12);
  const card = chartCard(fact, [row, line, note, grid], { cls: 'wk-card', aside: true });
  if (plans.length) card.dataset.plans = '';      // 계획 고르기가 있으면 합계 줄은 바닥 줄이 말한다
  root.replaceChildren(card);
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
