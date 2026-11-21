// ⑥ 정리 리포트 쪽: 발표 자료 모양의 면접 대비 슬라이드 여러 장 (design/build_report_deck.py 가 만든 쪽 그림). 위에서 아래로 차례로 보이고,
// 받기는 바닥 줄의 `pptx 받기`. 질문 수·출처는 바닥 줄 불렛 둘이 말한다
import { el, play } from './icons.js';

const $ = (id) => document.getElementById(id);

// steps 사건: 빈 종이 자리 (짜는 동안)
export function start() {
  const root = $('report-doc');
  root.setAttribute('aria-busy', 'true');
  root.replaceChildren(el('div', { class: 'sheet', 'data-empty': '' }));      // 첫 장 자리
}

// done 사건: 쪽 그림을 차례로 (첫 장은 바로, 나머지는 보일 때 읽는다)
export function done({ slides, rows }) {
  const root = $('report-doc');
  if (rows && rows.length) {      // 새 공고 (demo/live.py): 역량마다 공고 문장 → 프로젝트 일 → 교육자료 → 면접 질문
    const list = el('ol', { class: 'ev-list' });
    rows.forEach((r) => {
      const li = el('li', { class: 'ev' });
      const head = el('div', { class: 'ev-head' });
      head.append(el('span', { class: 'tag', 'data-pri': r.tier, text: r.tier }), el('b', { class: 'ev-name', text: r.name }));
      const body = el('div', { class: 'rep-rows' });
      [['공고', r.posting_ko || r.posting], ['프로젝트에서', r.job], ['교육자료', r.material || '-'], [`면접 질문${r.asked ? ` (${r.asked})` : ''}`, r.question || '-']]
        .forEach(([k, v]) => { const p = el('p', { class: 'rep-row' }); p.append(el('b', { text: `${k} · ` }), v); body.append(p); });
      li.append(head, body);
      list.append(li);
    });
    root.replaceChildren(list);
    root.removeAttribute('aria-busy');
    return;
  }
  const deck = el('div', { class: 'slides' });
  slides.forEach((src, i) => {
    const sheet = el('figure', { class: 'sheet' });
    sheet.append(el('img', { src, alt: `면접 대비 리포트 ${i + 1}쪽 / ${slides.length}쪽`, width: '1920', height: '1080', loading: i ? 'lazy' : 'eager' }));
    deck.append(sheet);
  });
  root.replaceChildren(deck);
  root.removeAttribute('aria-busy');
  play(deck, [{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'none' }], 240);
}

export function stopped() {
  const root = $('report-doc');
  root.removeAttribute('aria-busy');
  root.dataset.stopped = '';
}
export function clear() {
  const root = $('report-doc');
  root.replaceChildren();
  root.removeAttribute('aria-busy');
  delete root.dataset.stopped;
}
