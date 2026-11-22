// ④ 12주 계획 쪽 (사용자 11/22: "12주 계획 간트차트 형태로 보이도록 해줘. 세부 내용은 클릭하면 오른쪽에 사이드 탭이 뜨게(노션처럼)").
// 그림은 간트차트 하나 (gantt.js: 학기 16주 열, 작업 묶음 줄, 막대·교육자료 동그라미), 세부는 오른쪽 옆 패널 (peek.js).
// 시간·글은 모두 서버 값이다. 계획이 여럿이면(주 7·14·28시간) 머리에 한 주 공부 시간 고르기와 고른 안의 분량 한 줄(line). 7 은 보류 안내 글.
// 학기 모양은 6주 + 중간고사 2주 + 6주 + 기말고사 2주 (사용자 11/22): 계획의 12주가 학기 1~6주와 9~14주다 (서버 sem).
// 역량을 누르거나 마우스를 올리면 그 역량이 나온 공고 원문 문장을 작은 카드로 보인다 (popover, 옆 패널 안의 역량 칩).
import { el, icon } from './icons.js';
import { model, chart, legend, grow } from './gantt.js';
import { createPeek } from './peek.js';
import { chartCard, clearDoc } from './cards.js';
import { hoursText } from './tables.js';

const $ = (id) => document.getElementById(id);
const short = (h) => `${Math.round(h * 10) / 10}`;
let s = null;

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
    fill({ ...c, name: btn.dataset.name ?? btn.textContent.replace(/^(필수|우대|나머지)/, '') });
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

function fillFact(fact, p) {
  const md = p.source === 'md';
  fact.replaceChildren();
  if (p.source === 'blocked') { fact.append(p.blocked.title); return; }
  // 생성기 계획(하루 1·2·3시간): 배우기·만들기 합은 바닥 줄이 말하니 (S9) 머리 줄은 오른쪽 하루 공부 시간 고르기의 이름만
  if (p.source === 'generator') { fact.append('하루 공부 시간'); return; }
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
  const key = legend();
  const scroll = el('div', { class: 'g-scroll', tabindex: '-1' });
  const note = el('div', { class: 'wk-blocked-slot' });
  const peek = createPeek({ comps, popover });
  const page = $('page-weeks');
  const show = (k) => {
    chosen = k;
    const p = all.find((x) => x.key === k);
    current = plans.length ? p.summary : null;
    fillFact(fact, p);
    line.textContent = p.line || '';
    const blocked = p.source === 'blocked';
    key.hidden = blocked;
    scroll.hidden = blocked;
    note.replaceChildren(...(blocked ? [blockedNote(p.blocked)] : []));
    if (blocked) { scroll.replaceChildren(); peek.close({ focus: false, keepHash: true }); return; }
    const m = model(p);
    const g = chart(m, p.exams);
    scroll.replaceChildren(g);
    peek.use(m, page);
    return g;
  };
  const row = all.length > 1 ? planPick(all, chosen, (k) => { show(k); onPick(current, k); }) : el('div', { class: 'plan-row' });
  const card = chartCard(fact, [row, line, key, scroll, note], { cls: 'wk-card', aside: true });
  if (plans.length) card.dataset.plans = '';      // 계획 고르기가 있으면 합계 줄은 바닥 줄이 말한다
  root.replaceChildren(card);
  const g = show(chosen);
  s = { root, drop: () => peek.destroy() };
  if (g) grow(g);
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
