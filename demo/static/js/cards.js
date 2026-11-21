// 숫자·차트 부품 셋 (design/reviews/v7-dash-spec.md 1절). 노드를 돌려주고 사건이 오면 부르는 쪽이 글만 바꾼다.
// 화면은 셈하지 않는다: 시간·점수를 더하거나 빼는 것은 서버가 하고, 여기서는 받은 사건 개수 세기까지만 한다.
import { el } from './icons.js';
import { release } from './budget.js';

// 쪽의 주 그림 틀 하나 (쪽마다 하나, 겹치지 않는다): 머리 줄 = 왼쪽 사실 문장(14px 먹) + 오른쪽 자리(aside, 공부 시간 고르기가 들어온다), 그 아래 그림.
// 1px 선, 둥글기 12, 그림자 없음. cls 는 그림 쪽의 이름 (shots 와 css 가 읽는다)
export function chartCard(fact, body, { cls = '', aside = false } = {}) {
  const card = el('section', { class: `chart-card${cls ? ` ${cls}` : ''}` });
  const head = el('div', { class: 'chart-head' });
  head.append(fact);
  if (aside) head.append(el('div', { class: 'chart-aside' }));
  card.append(head, ...body);
  return card;
}

// 쪽 칸(④ ⑤)을 비운다. 틀 머리 줄에 들어와 있던 공부 시간 고르기 칸은 먼저 빼 둔다 (budget.release. 다음 placeBudget 이 새 틀로 한 번에 옮긴다)
export function clearDoc(root) {
  release(root);
  root.replaceChildren();
  root.removeAttribute('aria-busy');
  delete root.dataset.stopped;
}

// 범례: 줄마다 10px 견본 + 이름(13px 먹) + 개수(오른쪽 맞춤 13px 600, 있을 때만). 견본은 그림의 칠과 같은 클래스·속성을 받는다.
// rows: [{swatch: [class, attrs], name, n, key}] → 목록과 줄을 key 로 찾는 표
export function legend(rows, cls = '') {
  const ul = el('ul', { class: `legend${cls ? ` ${cls}` : ''}` });
  const items = {};
  for (const r of rows) {
    const li = legendRow(r);
    ul.append(li);
    if (r.key) items[r.key] = li;
  }
  return { ul, items };
}
export function legendRow({ swatch: [cls, attrs = {}], name, n = '', key = null }) {
  const li = el('li', { class: 'legend-row', 'data-key': key });
  li.append(el('span', { class: `legend-swatch ${cls}`, 'aria-hidden': 'true', ...attrs }), el('span', { class: 'legend-name', text: name }),
    el('span', { class: 'legend-n num', text: n }));
  return li;
}
