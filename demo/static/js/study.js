// ④ 교육자료 쪽 (3단계): 자료 × 역량 행렬 하나. m3_materials/pick.py 가 고른 결과를 다시 튼다.
// 열은 배울 역량(도구·지식, target 사건마다 하나), 줄은 고른 자료(핵심 1~2개, 보조 3~4개, pick 사건마다 하나), 칸은 그 자료가 그 역량을 다루는 정도
// (꽉 찬 칸 다룸, 반 칸 일부만, 빈 칸 안 다룸). 맨 아래 "합친 것" 줄은 그때까지 고른 자료를 합친 정도로, 서버가 보낸 levels 로만 바꾼다 (화면은 셈하지 않는다).
// 공부 시간은 이 쪽에서 쓰지 않는다 (⑤ 12주 계획에서 고른다). 글은 이름표뿐이고 셈은 바닥 줄 불렛이 말한다
import { el } from './icons.js';
import { evRow, evList, section, appear } from './result.js';
import { clearDoc } from './cards.js';

const $ = (id) => document.getElementById(id);
let s = null;


// 숫자 흐름 (발표 27쪽): 교육자료 은행 → BM25 → Cohere Rerank → AI 판정. 걸음마다 그 칸이 주황으로 켜진다 (② 깔때기와 같은 칸 모양)
const FLOW_AT = { targets: 0, search: 1, judge: 2, pick: 3 };
function flow(funnel) {
  const ol = el('ol', { class: 'funnel flow', 'aria-label': '교육자료를 고르는 차례' });
  funnel.forEach((f, i) => {
    if (i) ol.append(el('li', { class: 'stop-sep', 'aria-hidden': 'true', text: '→' }));
    const li = el('li', { class: 'stop', 'data-state': 'todo' });
    li.append(el('span', { class: 'stop-label', text: f.label }), el('span', { class: 'stop-n num', text: f.n.toLocaleString('ko-KR') }));      // ② 깔때기와 같은 차례 (css 가 숫자를 위로)
    ol.append(li);
  });
  return ol;
}
export function stage(key) {
  if (!s?.flow) return;
  const at = FLOW_AT[key] ?? -1;
  [...s.flow.querySelectorAll('.stop')].forEach((li, i) => { li.dataset.state = i < at ? 'done' : i === at ? 'current' : 'todo'; });
}

// steps 사건: 숫자 흐름과 빈 자료 목록. 결과와 근거 (사용자 11/21): 고른 자료마다 카드 하나 (핵심/보조 · 제목 링크 · 종류)와
// 그 자료가 가르치는 역량마다 "공고 문장 ↔ 자료의 구절" 짝
export function start(funnel = []) {
  const root = $('materials-doc');
  root.setAttribute('aria-busy', 'true');
  const list = el('ol', { class: 'mats', 'aria-label': '고른 교육자료' });
  const top = funnel.length ? flow(funnel) : null;
  const body = section('프로젝트만으로 다 못 배우는 도구·지식을 이 자료로 배워요', list);
  root.replaceChildren(...(top ? [top, body] : [body]));
  s = { root, list, flow: top };
}

// target 사건: 대상 역량 (자료 카드가 그 이름을 쓴다. 따로 그리지 않는다)
export function target() {}

// pick 사건: 자료 카드 하나
export function pick(row) {
  if (!s) return;
  const li = el('li', { class: 'mat', 'data-role': row.role });
  const head = el('p', { class: 'mat-head' });
  const a = el('a', { href: row.url, target: '_blank', rel: 'noopener noreferrer', class: 'mat-title', text: row.title });
  a.append(el('span', { class: 'sr-only', text: ' (새 창)' }));
  head.append(el('span', { class: 'tag m3-role', 'data-role': row.role, text: row.role }), a, el('span', { class: 'mat-kind', text: row.kind }));
  const rows = row.covers.map((c) => evRow({ cid: c.cid, tier: c.tier, name: c.name, level: c.level, state: c.text,
    left: { who: '공고', text: c.posting, ko: c.posting_ko }, right: { who: '자료', text: c.quote, ko: c.quote_ko, url: row.url, shot: c.shot } }));
  li.append(head, evList(rows));
  s.list.append(li);
  appear(li);
}

export function done() {
  if (!s) return;
  s.flow?.querySelectorAll('.stop').forEach((li, i, all) => { li.dataset.state = i === all.length - 1 ? 'end' : 'done'; });      // 끝 칸(고른 자료)은 먹
  s.root.removeAttribute('aria-busy');
}
export function stopped() {
  if (!s) return;
  s.root.removeAttribute('aria-busy');
  s.root.dataset.stopped = '';
}
export function clear() {
  s = null;
  clearDoc($('materials-doc'));
}
