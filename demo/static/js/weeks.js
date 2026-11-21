// ⑤ 12주 계획 쪽: 라운드랩 커리큘럼 생성기 결과 (사용자 11/21). 일마다 한 줄, 주마다 한 칸 (간트 표):
// 줄 = 배울 자료 또는 만들 일 (처음 나온 차례), 칸 = 그 주에 그 일에 쓰는 시간. 한 일이 여러 주에 걸치면 칸이 이어진다.
// 줄 이름 아래에 산출물(만들 일)과 키우는 역량. 맨 아래 줄은 주마다 합계와 한 주 한도. 시간·글은 모두 서버가 보낸 생성기 값이다
import { el, play } from './icons.js';
import { chartCard, clearDoc } from './cards.js';
import { hoursText } from './tables.js';

const $ = (id) => document.getElementById(id);
const short = (h) => `${Math.round(h * 10) / 10}`;      // 칸 안 숫자 (시간): 5, 1.5
let s = null;

// 주별 활동 → 일 목록 (처음 나온 차례). 같은 일이 여러 주에 나뉘어 있으면 한 줄로 모은다
function tasks(plan) {
  const byId = new Map();
  for (const w of plan) {
    for (const a of w.activities) {
      const t = byId.get(a.id) ?? byId.set(a.id, { ...a, weeks: new Map(), total: 0 }).get(a.id);
      t.weeks.set(w.week, (t.weeks.get(w.week) ?? 0) + a.hours);
      t.total += a.hours;
      if (a.out) t.out = a.out;
    }
  }
  return [...byId.values()];
}
// "X 기초" 와 "X" 가 함께 있으면 X 하나만
const skillsOf = (list) => list.filter((n) => !(n.endsWith(' 기초') && list.includes(n.slice(0, -3))));

export function start({ plan, cap, learning, project }) {
  const root = $('weeks-doc');
  root.setAttribute('aria-busy', 'true');
  const n = plan.length;
  const grid = el('div', { class: 'gantt', role: 'table', 'aria-label': '12주 계획: 일마다 주별 시간', style: `--weeks:${n}` });
  const head = el('div', { class: 'g-row g-head', role: 'row' });
  head.append(el('span', { class: 'g-label', role: 'columnheader', text: '할 일 (시간)' }));
  plan.forEach((w) => head.append(el('span', { class: 'g-week num', role: 'columnheader', text: `${w.week}주` })));
  grid.append(head);
  for (const t of tasks(plan)) {
    const row = el('div', { class: 'g-row', role: 'row', 'data-kind': t.kind });
    const label = el('div', { class: 'g-label', role: 'rowheader' });
    const name = el('p', { class: 'g-name' });
    name.append(el('span', { class: 'g-kind', 'data-kind': t.kind, text: t.kind === 'learning' ? '배우기' : '만들기' }));
    name.append(t.url ? el('a', { href: t.url, target: '_blank', rel: 'noopener noreferrer', text: t.title }) : el('span', { text: t.title }));
    name.append(el('span', { class: 'g-total num', text: ` · ${hoursText(t.total)}` }));
    label.append(name);
    if (t.out) label.append(el('p', { class: 'g-out', text: `산출물 · ${t.out}` }));
    const skills = skillsOf(t.skills || []);
    if (skills.length) {
      const chips = el('p', { class: 'g-skills' });
      skills.forEach((x) => chips.append(el('span', { class: 'skill', text: x })));
      label.append(chips);
    }
    row.append(label);
    const weeks = [...t.weeks.keys()];
    plan.forEach((w) => {
      const h = t.weeks.get(w.week);
      const cell = el('span', { class: 'g-cell', role: 'cell' });
      if (h) {
        cell.dataset.on = '';
        if (w.week === weeks[0]) cell.dataset.first = '';
        if (w.week === weeks.at(-1)) cell.dataset.last = '';
        cell.append(el('span', { class: 'g-h num', text: short(h) }));
        cell.title = `${w.week}주 · ${hoursText(h)}`;
      }
      row.append(cell);
    });
    grid.append(row);
  }
  const sum = el('div', { class: 'g-row g-sum', role: 'row' });
  sum.append(el('span', { class: 'g-label', role: 'rowheader', text: `한 주 합계 (한도 ${short(cap)}시간)` }));
  plan.forEach((w) => sum.append(el('span', { class: 'g-cell num', role: 'cell', 'data-over': String(w.learning + w.project > cap + 1e-9), text: short(w.learning + w.project) })));
  grid.append(sum);
  const key = el('p', { class: 'wk-fact' });
  key.append(el('span', { class: 'g-kind', 'data-kind': 'learning', text: '배우기' }), ` 교육자료 ${hoursText(learning)}  `,
    el('span', { class: 'g-kind', 'data-kind': 'project', text: '만들기' }), ` 프로젝트 ${hoursText(project)} · 한 사람 기준`);
  root.replaceChildren(chartCard(key, [grid], { cls: 'wk-card', aside: true }));
  s = { root };
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
  s = null;
  clearDoc($('weeks-doc'));
}
