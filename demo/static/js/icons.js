// 아이콘: 한 벌(선 굵기 1.75, 24 격자). 모두 장식이라 aria-hidden.
const paths = {
  plus: '<path d="M12 5v14M5 12h14"/>',
  up: '<path d="M12 19V5M5.5 11.5 12 5l6.5 6.5"/>',
  stop: '<rect x="7" y="7" width="10" height="10" rx="1.5" fill="currentColor" stroke="none"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  text: '<path d="M4 6h16M4 11h16M4 16h10"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/>',
  check: '<path d="M5 12.5 10 17.5 19 7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
  book: '<path d="M5 19V5a2 2 0 0 1 2-2h12v15H7a2 2 0 0 0-2 2 2 2 0 0 0 2 2h12"/><path d="M9 7h6"/>',
  code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
  back: '<path d="M15 5l-7 7 7 7"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  calendar: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4"/>',
  upload: '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/>',
};

export function icon(name, size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
}

export function el(tag, attrs = {}, html = '') {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === 'text') node.textContent = v;
    else node.setAttribute(k, v === true ? '' : v);
  }
  if (html) node.innerHTML = html;
  return node;
}

// 움직임 줄이기: 사용자 설정(prefersReduced) 이거나, 공부 시간을 바꿔 그림을 제자리에서 다시 쓰는 동안(setInstant)이면 끝 그림만
let instant = false;
export const setInstant = (on) => { instant = on; };
export const prefersReduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
export const reducedMotion = () => instant || prefersReduced();
export const narrow = () => matchMedia('(max-width: 1023.98px)').matches;

// 움직임 하나를 튼다 (사건마다 한 번). 움직임 줄이기거나 노드가 안 보이면(닫힌 패널, 숨은 쪽) 끝 그림 그대로 두고 null.
// switching 이면 공부 시간을 바꾸는 중의 제자리 다시 쓰기(setInstant)에도 튼다 (목표선·한도선만 옛 자리에서 새 자리로)
export function play(node, frames, ms, { switching = false } = {}) {
  if ((switching ? prefersReduced() : reducedMotion()) || !node.getClientRects().length) return null;
  return node.animate(frames, { duration: ms, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' });
}
