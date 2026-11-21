// 공부 시간 고르기 (하루 1·2·3시간). 처음 고르기는 대화 답 끝의 단추 셋(chat.js choose), 바꾸기는 라디오 칸 하나
// (④ ⑤ 에서는 주 그림 틀의 머리 줄 오른쪽, ⑥ 에서는 쪽 더미 바로 위).
// 이 파일은 라디오 칸 하나만 맡는다: 값은 서버가 보낸 목록(store.budgets)에서만 오고, 바꾸는 일 자체는 main.js 가 한다.
// 진짜 라디오라 화살표 키로 옮기면 값이 바뀐다 (브라우저 기본). 막힌 동안(자료를 찾는 중)은 칸을 흐리게 보이고, 누르면 값을 되돌리고 까닭을 알린다 (onLocked).
import { el } from './icons.js';

// 칸 노드는 하나다. ④ ⑤ 쪽에서는 주 그림 틀의 머리 줄 오른쪽(.chart-aside)으로 옮겨 가고, 그 밖에는 제자리(쪽 더미 바로 위)에 있다 (place).
// 쪽을 다시 그리면 틀이 새로 생기므로 id 로 찾지 않고 노드를 쥐고 있는다
const node = document.getElementById('budget');
const home = node.nextElementSibling;      // #stack: 제자리는 그 바로 앞
export const element = node;
let pick = () => {};
let explain = () => {};
let current = null;
let locked = false;

export function build(budgets, onPick, onLocked) {
  pick = onPick;
  explain = onLocked;
  const fs = node;
  fs.replaceChildren(el('legend', { class: 'sr-only', text: '하루 공부 시간' }));
  for (const b of budgets) {
    const label = el('label', { class: 'budget-opt' });
    const input = el('input', { type: 'radio', name: 'budget', value: b.key });
    input.addEventListener('change', () => {
      if (locked) { show(current); node.querySelector(':checked')?.focus({ preventScroll: true }); explain(); return; }
      pick(b.key);
    });
    label.append(input, el('span', { text: `하루 ${b.per_day}시간` }));
    fs.append(label);
  }
  show(current);
}

function show(key) {
  node.querySelectorAll('input').forEach((i) => { i.checked = i.value === key; });
}
// 지금 고른 값 (바꾸기가 끝났거나 처음 골랐을 때)
export function value(key) {
  current = key;
  show(key);
}
// 막기: 자료를 찾는 중이거나 아직 그린 단계가 없을 때. aria-disabled 로 알리고 값은 바뀌지 않는다
export function lock(on) {
  locked = on;
  node.querySelectorAll('input').forEach((i) => i.setAttribute('aria-disabled', String(on)));
  if (on) node.dataset.locked = ''; else delete node.dataset.locked;
}
// 바꾸는 동안 aria-busy
export function busy(on) {
  if (on) node.setAttribute('aria-busy', 'true'); else node.removeAttribute('aria-busy');
}

// 쪽 틀을 비우기 전에 칸을 빼 둔다 (cards.clearDoc 가 부른다. 틀과 함께 노드를 잃지 않게). 노드는 DOM 밖에서 기다리고,
// 다음 place 가 한 번에 새 틀이나 제자리로 옮긴다: 공부 시간을 바꿔 쪽을 다시 그려도 노드는 한 번만 옮겨지고 초점도 한 번만 빠졌다 돌아온다
let refocus = false;      // 빼 둘 때 초점이 칸 안에 있었다
export function release(root) {
  if (!root.contains(node)) return;
  refocus ||= node.contains(document.activeElement);
  node.remove();
}
// 칸을 slot(주 그림 틀의 머리 줄 오른쪽) 안으로, slot 이 없으면 제자리로. 초점이 칸 안에 있었으면(빼 둔 때 포함) 고른 칸으로 되돌린다
export function place(slot) {
  const had = refocus || node.contains(document.activeElement);
  refocus = false;
  if (!(slot ? node.parentElement === slot : node.nextElementSibling === home)) {
    if (slot) slot.append(node); else home.before(node);
  }
  if (had && !node.contains(document.activeElement)) (node.querySelector(':checked') || node.querySelector('input'))?.focus({ preventScroll: true });
}
