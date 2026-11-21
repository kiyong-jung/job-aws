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
export function done({ slides }) {
  const root = $('report-doc');
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
