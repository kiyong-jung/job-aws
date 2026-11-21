// 결과와 근거 (사용자 11/21: 과정 그림보다 결과가 사람에게 쓸모 있는지가 중요하다).
// 쪽마다 "무엇이 나왔나"(큰 카드)와 "왜 이 공고에 맞나"(공고 문장 ↔ 결과 쪽 문장 짝)를 같은 부품으로 그린다.
import { el, play } from './icons.js';

export const LEVEL = { 있음: '다룸', 일부: '일부만', 없음: '없음' };

export const tag = (tier) => el('span', { class: 'tag', 'data-pri': tier, text: tier });

// 쪽 안의 한 덩어리: 머리 한 줄 + 내용
export function section(title, ...body) {
  const s = el('section', { class: 'rs' });
  s.append(el('h3', { class: 'rs-h', text: title }), ...body);
  return s;
}

// 인용 한 칸: 누가 말했나(공고, 1위 README, 자료 이름) + 근거 문장. 영어 원문은 한국어 옮김(ko)을 보이고 원문은 마우스를 올리면 (사용자 11/21)
function said(who, text, kind, ko = '') {
  const q = el('figure', { class: 'ev-q', 'data-kind': kind });
  q.append(el('figcaption', { class: 'ev-who', text: who }), el('blockquote', { text: ko || text || '근거 문장 없음', title: ko ? `원문: ${text}` : null }));
  return q;
}

// 근거 한 줄: [필수] 역량 이름 · 판정, 그 아래 왼쪽 공고 문장 | 오른쪽 결과 쪽 문장
export function evRow({ cid, tier, name, state, level, left, right }) {
  const li = el('li', { class: 'ev', 'data-cid': cid, 'data-level': level });
  const head = el('div', { class: 'ev-head' });
  head.append(tag(tier), el('b', { class: 'ev-name', text: name }), el('span', { class: 'ev-state', 'data-level': level, text: state }));
  const pair = el('div', { class: 'ev-pair' });
  pair.append(said(left.who, left.text, 'posting', left.ko), said(right.who, right.text, 'proof', right.ko));
  li.append(head, pair);
  return li;
}

export const evList = (rows) => {
  const ol = el('ol', { class: 'ev-list' });
  ol.append(...rows);
  return ol;
};

// 숫자 한 쌍: "필수 8개 중 5.5개"
export function score(label, n, total, cls = '') {
  const p = el('p', { class: `rs-score${cls ? ` ${cls}` : ''}` });
  p.append(el('span', { class: 'rs-score-label', text: label }), el('b', { class: 'num', text: String(n) }), el('span', { text: ` / ${total}` }));
  return p;
}

export const appear = (node) => play(node, [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], 240);
