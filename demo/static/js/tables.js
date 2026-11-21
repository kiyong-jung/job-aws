// 쪽 그림들이 같이 쓰는 작은 부품: 점수·시간 글, 번호 배지, 필수 | 우대 | 나머지 칸 판.
import { el } from './icons.js';

// 점수는 어디서나 한 꼴: "5점 중 4.5점" (5.0 → 5, 4.5 → 4.5)
const points = (x) => `${Number(x.toFixed(1))}점`;
export const scoreText = (x, total) => `${total}점 중 ${points(x)}`;
// 시간은 소리 내 읽히게: 3 → "3시간", 1.3 → "1시간 18분", 0.72 → "43분" (서버 pipeline.hm 과 같다)
export function hoursText(x) {
  const all = Math.round(x * 60), h = Math.floor(all / 60), m = all % 60;
  return [h ? `${h}시간` : '', m || !h ? `${m}분` : ''].filter(Boolean).join(' ');
}

// 번호 배지 (회색 둥근 칸). ③ 쪽의 빌린 부분 번호(by-n)는 같은 틀에 원 모양만 다르다
export const badge = (n, cls = '') => el('span', { class: `badge num${cls ? ` ${cls}` : ''}`, text: String(n) });

// 역량 칸 판: 필수 | 우대 | 나머지 세 묶음 (묶음 사이 간격과 작은 이름표). ① 찾은 역량 칸과 ③ 덮기 띠가 같이 쓴다.
// 구분 없는 역량("구분없음")은 나머지 묶음에 둔다
export const STRIP_TIERS = ['필수', '우대', '나머지'];
export function tierStrip() {
  const box = el('div', { class: 'strip-cells', role: 'img' });
  const groups = Object.fromEntries(STRIP_TIERS.map((name) => {
    const g = el('span', { class: 'strip-group', 'data-tier': name });
    const cells = el('span', { class: 'strip-row' });
    g.append(el('span', { class: 'strip-tier', 'aria-hidden': 'true', text: name }), cells);
    box.append(g);
    return [name, cells];
  }));
  box.add = (tier, cell) => { (groups[tier] || groups[STRIP_TIERS.at(-1)]).append(cell); return cell; };
  return box;
}
