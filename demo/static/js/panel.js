// 대시보드: 쪽 더미, 쪽마다 바닥 줄(한 줄 불렛 둘 + 단추), ① 공고 원문·형광펜·찾은 역량 칸, ③ 응용 프로젝트 덮기 띠.
// 쪽 더미: ① 공고 원문 → ② 프로젝트 찾기(DB 그림, search.js) → ③ 응용 프로젝트(덮기 띠) → ④ 교육자료(자료 × 역량, study.js)
// → ⑤ 12주 계획(학기 16주 칸, weeks.js) → ⑥ 정리 리포트(면접 대비 슬라이드, report.js).
// store.stack 이 하나뿐인 기록이고 reveal 만 바꾼다. 쪽은 모두 DOM 에 남아 맨 위 쪽만 보인다. 새 쪽은 오른쪽에서 밀려 들어오고, 뒤로는 거꾸로.
// 쪽 안의 글은 바닥 줄의 불렛 둘뿐이다 (사용자 11/19: 대시보드에는 그림만, 글은 한 줄 불렛 두 개). 그림 안 이름표·범례는 그림의 일부다.
import { el, icon, reducedMotion, play } from './icons.js';
import { place, element as budgetBox } from './budget.js';
import { store } from './store.js';
import { evRow, evList, section, halfNote, numUnit, LEVEL } from './result.js';

const $ = (id) => document.getElementById(id);
const sentences = new Map();      // sid → 문장 span (칠한 뒤에는 mark)

const ORDER = ['posting', 'search', 'materials', 'weeks', 'report'];      // ② 는 최종 응용 프로젝트 하나 (사용자 11/21: 1위와 응용을 따로 두지 않는다)
const NAMES = { posting: '공고 읽기', search: '프로젝트', materials: '교육자료', weeks: '12주 계획', report: '정리 리포트' };
// ③ 은 응용 프로젝트 (1위에 빌린 부분을 더한 한 건). 응용 결과가 저장본에 없으면 1위 프로젝트
const name = (key) => NAMES[key];
// 단계 길에는 짧은 이름을 쓴다 (여섯이 한 줄에 들어가게)
const SHORT = { posting: '공고', search: '프로젝트', materials: '교육자료', weeks: '12주 계획', report: '리포트' };
const short = (key) => SHORT[key];
const page = (key) => $(`page-${key}`);
const BOX = { posting: 'doc', search: 'search-doc', materials: 'materials-doc', weeks: 'weeks-doc', report: 'report-doc' };      // 쪽마다 스크롤하는 칸
export const box = (key) => $(BOX[key]);
const ready = new Set(['posting']);      // 그린 쪽 (단계 길에 나오고 갈 수 있다)
const fresh = new Set();                 // 보고 있지 않을 때 새로 그린 쪽 (단계 길의 그 번호에 점. 가 보면 지운다)
const statusOf = Object.fromEntries(ORDER.map((k) => [k, '']));      // 쪽 머리 상태 줄 (다시 틀기 알림)
const doing = {};                                                   // 도는 동안 그 쪽의 지금 하는 일 (상태 줄을 잠시 덮는다)
const feet = Object.fromEntries(ORDER.map((k) => [k, { bullets: [], actions: [] }]));
// 쪽 제목 (발표 자료의 그 장 제목 그대로, 사용자 11/21: 발표 디자인을 그대로). 형광펜 줄로 보인다
const TITLE = { posting: '공고 한 건에서 역량을 뽑는다', search: '1위 프로젝트에, 빈 역량은 다른 프로젝트에서 방식만 빌린다',
  materials: '낱말로 넓게 모아, 뜻으로 다시 고른다', weeks: '프로젝트 하나와 교육자료가 12주 계획이 된다', report: '공고 문장 하나에 빅테크 면접 질문 하나' };
// 걸음 (발표의 "걸음 ① ② ③ ④ ⑤"): 쪽마다 그 단계의 하위 일 목록과 지금 하는 일. 서버의 steps·stage 사건이 채운다
const walks = {};      // 쪽 → {items:[{key, label}], at: 지금 걸음 번호(0부터), done}

export function init() {
  for (const k of ORDER) page(k).prepend(el('h2', { class: 'page-title', id: `title-${k}` }, `<span class="hl-line">${TITLE[k]}</span>`));
  // 바닥 줄: 사람이 굴린 방향만 본다 (휠·터치). 화면이 스스로 굴리는 것(형광펜 따라가기)에는 숨지 않는다
  for (const k of ORDER) {
    const p = page(k);
    let touchY = null;
    const move = (dy) => { if (Math.abs(dy) < 2) return; if (dy > 0) p.dataset.footAway = ''; else delete p.dataset.footAway; };
    p.addEventListener('wheel', (e) => move(e.deltaY), { passive: true });
    p.addEventListener('touchstart', (e) => { touchY = e.touches[0].clientY; }, { passive: true });
    p.addEventListener('touchmove', (e) => { if (touchY !== null) { move(touchY - e.touches[0].clientY); touchY = e.touches[0].clientY; } }, { passive: true });
  }
  $('panel-back').innerHTML = icon('back');
  $('panel-back').addEventListener('click', () => { reveal(store.stack.at(-2)); refocus(); });
  $('panel-path').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-to]');
    if (b) { reveal(b.dataset.to); refocus(); }
  });
  head();
}

export const top = () => store.stack.at(-1);
const visible = (node) => !$('panel').hidden && node?.closest('.page')?.dataset.view === top();

// key 쪽을 맨 위로. 더미는 늘 ORDER 의 앞부분(그린 쪽만)이라, 위의 쪽이면 밀어 넣고 아래 쪽이면 되돌아간다
export function reveal(key) {
  if (!key) return;
  ready.add(key);
  fresh.delete(key);
  const from = top();
  store.stack = ORDER.slice(0, ORDER.indexOf(key) + 1).filter((k) => ready.has(k));
  if (from !== key) go(from, key, ORDER.indexOf(key) > ORDER.indexOf(from) ? 1 : -1);
  head();
}
// 저절로 넘기지 않은 쪽이 새로 그려졌다 (사용자가 다른 쪽으로 돌아가 있었다): 끌고 가지 않고 단계 길의 그 번호에 점을 단다
export function markFresh(key) {
  if (top() === key) return;
  ready.add(key);
  fresh.add(key);
  head();
}
// 머리의 단추(뒤로, 단계 길)를 눌러 그 단추가 사라졌으면 초점을 새 쪽 글로
function refocus() {
  const a = document.activeElement;
  if (!a || a === document.body || !a.isConnected || a.hidden) box(top()).focus({ preventScroll: true });
}

// 쪽 넘기기: 들어오는 쪽은 24px 옆에서, 나가는 쪽은 반대로 24px 물러나며 사라진다. transform·opacity 만. 움직임 줄이기면 바로 바꾼다
let moving = [];
function go(from, to, dir) {
  moving.forEach((a) => a.cancel());
  moving = [];
  for (const k of ORDER) {
    page(k).hidden = k !== to && k !== from;
    page(k).inert = k !== to;
  }
  const ms = reducedMotion() || $('panel').hidden ? 0 : px('--t-view');
  const out = page(from), inn = page(to);
  if (!ms) { out.hidden = true; return; }
  const opts = { duration: ms, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' };
  moving = [inn.animate([{ transform: `translateX(${24 * dir}px)`, opacity: 0 }, { transform: 'none', opacity: 1 }], opts),
    out.animate([{ transform: 'none', opacity: 1 }, { transform: `translateX(${-24 * dir}px)`, opacity: 0 }], opts)];
  moving[1].finished.then(() => { if (top() !== from) out.hidden = true; }, () => {});
}

// 머리: 뒤로 단추(두 쪽 이상일 때), 단계 길(지금 쪽은 굵게, 그린 다른 쪽은 단추, 아직 안 그린 쪽은 옅게), 그 쪽의 상태 줄
function head() {
  const now = top(), back = store.stack.at(-2);
  $('panel-back').hidden = !back;
  if (back) $('panel-back').setAttribute('aria-label', `뒤로: ${name(back)}`);
  $('panel-path').replaceChildren(...ORDER.map((k) => {
    const li = el('li', { 'data-new': fresh.has(k) });
    const item = k === now ? el('span', { 'aria-current': 'step' })
      : ready.has(k) ? el('button', { type: 'button', 'data-to': k, title: fresh.has(k) ? '새로 그렸어요' : null }) : el('span', { 'aria-disabled': 'true' });
    item.append(el('span', { class: 'path-n num', 'aria-hidden': 'true', text: String(ORDER.indexOf(k) + 1) }), el('span', { class: 'path-name', text: short(k) }));
    if (fresh.has(k)) item.append(el('span', { class: 'sr-only', text: ', 새로 그렸어요' }));
    li.append(item);
    return li;
  }));
  $('panel').dataset.stack = store.stack.join(' ');
  drawStatus(now);
  // 하루 공부 시간 고르기: 12주 계획·리포트 쪽에서만. 12주 계획이 한 주 공부 시간을 스스로 고르는 예시면 어디서도 숨긴다 (⑥ 도 ④ 에서 고른 시간을 따른다)
  budgetBox.hidden = !(store.budget && !store.ownHours && (now === 'report' || now === 'weeks'));
  placeBudget();
}
// 공부 시간 고르기 칸의 자리: ⑤ 쪽이면 주 그림 틀의 머리 줄 오른쪽, 그 밖(⑥)은 쪽 더미 바로 위.
// ⑤ 가 한 주 공부 시간을 스스로 고르는 예시(store.ownHours)면 ⑤ 틀에 넣지 않는다 (숨긴 칸이 ⑤ 안에 남지 않게)
export function placeBudget() {
  const now = top();
  place(now === 'weeks' && !store.ownHours ? page(now).querySelector('.chart-aside') : null);
}
// ③ 쪽의 이름이 정해졌다 (이 공고의 저장본에 응용 프로젝트가 있는지 알았다): 단계 길을 다시 그린다
export const retitle = () => head();

export function open() { $('panel').hidden = false; }
// 상태 줄: 다시 틀기 알림 (그 쪽에 머문다). 바꾸면 도는 동안의 말도 거둔다
export function status(text, of = 'posting') {
  statusOf[of] = text;
  if (walks[of] && doing[of]) walks[of].done = true;      // 돌던 단계가 끝났다 (시작할 때 부르면 걸음은 그대로)
  delete doing[of];
  if (top() === of) drawStatus(of);
}
// 도는 동안 지금 하는 일 ("DB 에서 찾는 중"). 단계가 끝나면 status 가 거둔다
export function progress(of, text, stage = null) {
  doing[of] = text;
  const w = walks[of];
  if (w && stage) { const i = w.items.findIndex((x) => x.key === stage); if (i >= 0) { w.at = i; w.done = false; } }
  if (top() === of) drawStatus(of);
}
// 쪽의 걸음 목록을 정한다 (그 단계가 시작될 때)
export function walk(of, items) {
  walks[of] = { items, at: -1, done: false };
  if (top() === of) drawStatus(of);
}
// 상태 줄: 걸음 동그라미(끝난 것 먹 테두리, 지금 것 주황, 아직 옅게) + 지금 하는 일, 끝나면 다시 틀기 알림.
// 동그라미는 단계가 도는 동안만 (끝난 뒤 이름 없는 번호 줄이 단계 길과 겹쳐 보이지 않게, 디자이너 셋 합의 11/21)
function drawStatus(now) {
  const box = $('panel-status'), w = walks[now];
  box.replaceChildren();
  if (w && doing[now]) {
    const dots = el('span', { class: 'walk', 'aria-hidden': 'true' });
    dots.append(el('span', { class: 'walk-name', text: '걸음' }));
    w.items.forEach((x, i) => dots.append(el('span', { class: 'walk-n', 'data-state': w.done || i < w.at ? 'done' : i === w.at ? 'now' : 'todo', title: x.label, text: String(i + 1) })));
    box.append(dots);
  }
  const text = doing[now] || statusOf[now];
  if (text) box.append(el('span', { class: 'walk-text', text }));      // 빈 상태 줄은 그리지 않는다 (머리가 한 줄 52px, 디자이너 2차 11/21)
}

// 바닥 줄: 한 줄 불렛 둘(받은 글 그대로, 둘까지)과 단추. bullets 가 null 이면 불렛은 그대로 두고 단추만 바꾼다.
// 단추는 [이름, 할 일] 이나 {label, href, download} (내려받기 링크)
export function foot(key, bullets, actions = []) {
  const f = feet[key];
  if (bullets) f.bullets = bullets.slice(0, 2);
  f.actions = actions;
  drawFoot(key);
}
function drawFoot(key) {
  const node = $(`foot-${key}`), { bullets, actions } = feet[key];
  delete page(key).dataset.footAway;      // 바닥 줄이 새로 그려지면 (다음 단계 단추가 생기면) 다시 보인다
  const list = el('ul', { class: 'bullets' });
  bullets.forEach((t) => list.append(el('li', { text: t })));
  const row = el('div', { class: 'actions' });
  actions.forEach((a) => {
    const b = Array.isArray(a) ? el('button', { type: 'button', class: 'go', text: a[0] })
      : el('a', { class: 'go', href: a.href, download: a.download || '', text: a.label });
    if (Array.isArray(a)) b.addEventListener('click', a[1]);
    row.append(b);
  });
  node.replaceChildren(list, row);
  node.hidden = !bullets.length && !actions.length;
}
// 다음 단계를 시작했다: 모든 쪽의 단추를 거둔다 (불렛은 남는다)
export function dropActions() {
  ORDER.forEach((k) => { if (feet[k].actions.length) { feet[k].actions = []; drawFoot(k); } });
}

// 다 읽었다: 칠하지 않은 문장을 물린다
export function doneReading() { $('doc').dataset.done = ''; }

// from 쪽부터 뒤 쪽을 비우고 그 앞 쪽만 남긴다. 보던 쪽이 비워지면 남은 맨 뒤 쪽으로 돌아간다.
// 쪽 안 그림은 search·study·weeks·report 의 clear 가 비운다 (main.js reset 이 함께 부른다). all 이면 공고 원문까지 비우고 대시보드를 숨긴다
export function reset({ all = false, from = 'search' } = {}) {
  moving.forEach((a) => a.cancel());
  moving = [];
  const gone = all ? ORDER : ORDER.slice(ORDER.indexOf(from));
  if (gone.includes('search')) adapt = null;
  gone.forEach((k) => {
    if (k !== 'posting') ready.delete(k);
    fresh.delete(k);
    statusOf[k] = '';
    delete doing[k];
    delete walks[k];
    feet[k] = { bullets: [], actions: [] };
    drawFoot(k);
  });
  const left = ORDER.filter((k) => ready.has(k));
  const now = left.includes(top()) ? top() : left.at(-1);
  store.stack = left.slice(0, left.indexOf(now) + 1);
  for (const k of ORDER) { page(k).hidden = k !== now; page(k).inert = k !== now; }
  if (all) {
    sentences.clear();
    queue.length = 0;
    $('doc').replaceChildren();
    delete $('doc').dataset.done;
    cells = null;
    $('posting-cells').replaceChildren();
    $('panel').hidden = true;
  }
  head();
}

// ── ① 공고 원문과 찾은 역량 칸 ──
// 실제 공고 화면 (사용자 11/21): 캡처 그림 위에 핵심 문장 자리(서버가 보낸 좌표, 페이지 픽셀)마다 형광펜 칸을 얹는다.
// 좌표는 그림 너비에 대한 % 로 둔다 (칸 너비가 바뀌어도 자리가 맞게)
let shot = null;
function renderShot(p) {
  const { png, width, height, marks } = p.shot;
  const box = el('div', { class: 'shot' });
  box.append(el('img', { src: png, alt: `${p.company || ''} 공고 원문 화면`, width: String(width), height: String(height) }));
  const layer = el('div', { class: 'shot-layer' });
  box.append(layer);
  shot = { layer, width, height, marks };
  return box;
}
function paintShot(n) {
  const rs = shot?.marks[n];
  if (!rs) return null;
  const pct = (v, of) => `${(v / of) * 100}%`;
  // 번호 배지는 글 칸 왼쪽 여백에 (형광펜 첫 칸 바로 왼쪽에 두면 줄 가운데서 시작하는 문장이 앞 낱말을 덮는다, 디자이너 2차 11/21).
  // 배지는 첫 칸 안에 두어 칠·켜짐 상태를 그대로 따르고, 자리만 글 칸 왼쪽 끝(모든 형광펜 가운데 가장 왼쪽)에서 28px 왼쪽으로
  shot.colX ??= Math.min(...Object.values(shot.marks).flat().map(([x]) => x));
  const parts = rs.map(([x, y, w, h], i) => {
    const d = el('mark', { class: 'hl shot-hl', 'data-n': n, style: `left:${pct(x, shot.width)};top:${pct(y, shot.height)};width:${pct(w, shot.width)};height:${pct(h, shot.height)}` });
    if (!i) d.append(el('span', { class: 'badge', 'aria-hidden': 'true', text: String(n), style: `left:calc(${((shot.colX - x) / w) * 100}% - 28px)` }));
    shot.layer.append(d);
    return d;
  });
  return parts;
}

let koOf = {};      // 문장 id → 한국어 옮김 (영어 공고)
export function renderPosting(p) {
  sentences.clear();
  koOf = p.ko || {};
  const doc = $('doc');
  doc.replaceChildren();
  shot = null;
  if (p.shot) {      // 실제 화면: 원문 글은 칠할 곳만 숨겨 둔다 (형광펜 짝은 그림 위 칸이 맡는다)
    doc.dataset.shot = '';
    doc.append(renderShot(p));
  } else delete doc.dataset.shot;
  const text = p.shot ? el('div', { class: 'shot-text', hidden: true }) : doc;
  if (p.shot) doc.append(text);
  if (p.company) text.append(el('p', { class: 'doc-company', text: p.company }));
  text.append(el('h3', { class: 'doc-title', text: p.title }));
  for (const sec of p.sections) {
    const part = el('section', { class: 'doc-sec' });
    part.append(el('h4', { text: sec.name }));
    let para = null, list = null;
    for (const item of sec.items) {
      const span = el('span', { class: 'sent', 'data-sid': item.id, text: item.text });
      sentences.set(item.id, span);
      if (item.kind === 'li') {
        para = null;
        if (!list) { list = el('ul'); part.append(list); }
        const li = el('li');
        li.append(span);
        list.append(li);
      } else {
        list = null;
        if (!para) { para = el('p'); part.append(para); } else para.append(' ');
        para.append(span);
      }
    }
    text.append(part);
  }
  doc.scrollTop = 0;
  // 오른쪽: 이 공고가 원하는 역량 (사용자 11/21: 결과를 읽히게). 필수는 이름과 그 공고 문장, 우대는 이름, 나머지는 수와 접은 목록.
  // row 사건마다 한 줄이 생긴다. 줄에 올리면 그 문장의 형광펜이 진해지고, 누르면 원문의 그 문장으로
  const box = el('div', { class: 'wants' });
  box.append(el('h3', { class: 'rs-h', text: '이 공고가 원하는 역량' }));
  const group = (tier, title) => {
    const s = el('section', { class: 'want-group', 'data-tier': tier, hidden: true });
    const h = el('h4', { class: 'want-h' });
    h.append(tag(tier), el('span', { class: 'want-title', text: title }), el('span', { class: 'want-n num', text: '0개' }));
    const ol = el('ol', { class: 'want-list' });
    s.append(h, ol);
    box.append(s);
    return { s, ol, n: h.lastChild, count: 0 };
  };
  const rest = el('details', { class: 'want-rest', hidden: true });
  const restSum = el('summary');
  const restList = el('p', { class: 'want-rest-list' });
  rest.append(restSum, restList);
  cells = { 필수: group('필수', '자격요건'), 우대: group('우대', '우대사항'), rest, restSum, restList, restN: 0 };
  box.append(rest);
  $('posting-cells').replaceChildren(box);
}
const tag = (tier) => el('span', { class: 'tag', 'data-pri': tier, text: tier });
let cells = null;
export function addCell(row) {
  if (!cells) return;
  const marks = () => row.badges.map((n) => store.marks.get(n)).filter(Boolean);
  const lit = (on) => marks().forEach((m) => { if (on) m.dataset.lit = ''; else delete m.dataset.lit; });
  const hover = (node) => {
    node.addEventListener('pointerenter', () => lit(true));
    node.addEventListener('pointerleave', () => lit(false));
    node.addEventListener('focus', () => lit(true));
    node.addEventListener('blur', () => lit(false));
    node.addEventListener('click', () => scrollInto($('doc'), marks()[0]));
  };
  const g = cells[row.priority];
  if (!g) {      // 나머지: 접은 목록에 이름만
    cells.restN += 1;
    cells.rest.hidden = false;
    cells.restSum.textContent = `나머지 역량 ${cells.restN}개 보기`;
    cells.restList.textContent = cells.restList.textContent ? `${cells.restList.textContent}, ${row.name}` : row.name;
    return;
  }
  g.s.hidden = false;
  g.count += 1;
  g.n.textContent = `${g.count}개`;
  // 같은 공고 문장에서 나온 역량은 한 줄에 모은다 (문장은 한 번만)
  const key = row.badges[0];
  g.by ??= new Map();
  let item = g.by.get(key);
  if (!item) {
    const li = el('li', { class: 'want' });
    const names = el('span', { class: 'want-names' });
    li.append(el('span', { class: 'badge num', 'aria-hidden': 'true', text: String(key) }), names);
    if (row.priority === '필수') {
      const sid = row.sids.find((x) => sentences.get(x));
      const text = sid && sentences.get(sid).textContent.replace(/^\d+번 문장: \d*/, '');
      if (text) li.append(el('blockquote', { class: 'want-q', text: koOf[sid] || text, title: koOf[sid] ? `원문: ${text}` : null }));
    }
    g.ol.append(li);
    item = { li, names };
    g.by.set(key, item);
    play(li, [{ opacity: 0, transform: 'translateY(4px)' }, { opacity: 1, transform: 'none' }], 200);
  }
  const b = el('button', { type: 'button', class: 'want-btn', 'aria-label': `${row.name}, ${row.badges.join(', ')}번 문장` });
  b.append(el('b', { class: 'want-name', text: row.name }));
  hover(b);
  item.names.append(b);
}

// 형광펜 한 줄: 번호 배지(형광펜 안 맨 앞) + 공고 원문 그대로
function sentenceMark(n, text) {
  const mark = el('mark', { class: 'hl', 'data-n': n });
  mark.append(el('span', { class: 'sr-only', text: `${n}번 문장: ` }), el('span', { class: 'badge', 'aria-hidden': 'true', text: String(n) }), text);
  return mark;
}
// 형광펜: 사건이 오면 줄을 세워 두고 한 프레임에 한 번만 DOM 을 바꾼다 (서버가 몇 줄씩 함께 보낸다, pipeline.WAVES).
// 프레임 1 에서 span 을 mark 로 바꾸고, 프레임 2 에서 칠하기를 켠 뒤(css 전환) 그 묶음의 마지막 것이 보이게 스크롤한다
const queue = [];
export function paint(sid, n) {
  queue.push({ sid, n });
  if (queue.length === 1) requestAnimationFrame(flush);
}
function flush() {
  const now = [];
  for (const { sid, n } of queue.splice(0)) {
    const onShot = paintShot(n);
    if (onShot) { store.marks.set(n, onShot[0]); now.push(...onShot); continue; }      // 실제 화면 위 칸
    const span = sentences.get(sid);
    if (!span) continue;
    const mark = sentenceMark(n, span.textContent);
    mark.dataset.sid = sid;
    span.replaceWith(mark);
    sentences.set(sid, mark);
    store.marks.set(n, mark);
    now.push(mark);
  }
  if (!now.length) return;
  requestAnimationFrame(() => {
    now.forEach((m) => { m.dataset.painted = ''; });
    scrollInto($('doc'), now[now.length - 1], { smooth: false });
  });
}

// 스크롤 칸 안에서 target 이 보이게. 이미 보이면 그대로, 아니면 target 이 칸 위 1/4 자리에 오게. 숨은 칸은 건드리지 않는다
export function scrollInto(scroller, target, { smooth = true } = {}) {
  if (!target || !target.getClientRects().length || !visible(scroller)) return;
  const b = scroller.getBoundingClientRect(), t = target.getBoundingClientRect();
  if (t.top >= b.top + 8 && t.bottom <= b.bottom - 8) return;
  const offset = t.height < b.height * 0.6 ? b.height * 0.25 : 8;
  scroller.scrollTo({ top: scroller.scrollTop + t.top - b.top - offset, behavior: smooth && !reducedMotion() ? 'smooth' : 'auto' });
}

// ── ③ 응용 프로젝트 (adapt 사건: m2_project/adapt.py 가 만든 한 건) ──
// 결과와 근거 (사용자 11/21): 응용 프로젝트 카드(이름, 목표, 필수·우대 셈 전→뒤) → 1위에 없던 역량을 어떤 일로 채우나
// (공고 문장 ↔ 채우는 일과 그 근거: 빌린 프로젝트의 구절 또는 AI가 더한 까닭) → 만들 것 (일마다 시간과 산출물).
// fill 사건은 ③ 이 보일 때 차례로 다시 튼다 (playFills): 그 줄의 판정이 "없음 → 다룸"으로 바뀌고 큰 숫자가 오른다 (게임처럼 능력치가 하나씩)
let adapt = null;
export function renderAdapted(a, { top = null } = {}) {
  const doc = $('search-doc');
  doc.scrollTop = 0;
  const hero = el('section', { class: 'rs-hero' });
  hero.append(el('h3', { class: 'rs-title', text: a.title }), el('p', { class: 'rs-intro', text: a.goal }));
  const scores = el('div', { class: 'rs-scores' });
  const now = {};
  for (const t of a.tiers) {      // "필수 역량 8개 중 바탕 5.5개 → 빌려서 8개": 앞은 1위 바탕만으로 덮은 정도, 큰 숫자는 빌린 뒤 (fill 사건마다 오른다)
    const p = el('p', { class: 'rs-score' });
    const b = el('b', { class: 'num', text: String(t.before), 'data-after': String(t.after) });
    p.append(el('span', { class: 'rs-score-label', text: `${t.name} 역량 ${t.total}개 중` }), el('span', { class: 'rs-score-was', text: `바탕 ${t.before}개 → 빌려서` }),
      numUnit(b));
    const gain = el('span', { class: 'rs-gain', 'aria-hidden': 'true' });      // 오른 만큼 (+1, +0.5) 이 그 숫자 바로 옆에 잠깐 뜬다
    p.append(gain);
    now[t.name] = { b, gain };
    scores.append(p);
  }
  hero.append(scores, ...[halfNote(...a.tiers.flatMap((t) => [t.before, t.after]))].filter(Boolean));
  const rows = new Map();
  const filled = new Set(a.filled.map((r) => r.cid));      // 1위에 없던 것을 채운 줄: "없음 → 다룸" 으로 바뀌는 모습을 튼다
  const who = (r) => (r.from === 'AI가 더함' ? `AI가 더한 일 · ${r.job}` : r.from === '바탕' ? `1위 ${a.base.title} · ${r.job}`
    : r.from ? `${r.from}에서 빌림 · ${r.job}` : r.job);
  const list = evList(a.rows.map((r) => {
    const grow = filled.has(r.cid);
    const li = evRow({ cid: r.cid, tier: r.tier, name: r.name, level: grow ? r.was : r.level, state: grow ? `${LEVEL[r.was]} → ${LEVEL[r.level]}` : LEVEL[r.level],
      left: { who: '공고', text: r.posting, ko: r.posting_ko }, right: { who: who(r), text: r.proof, ko: r.proof_ko, url: r.url, shot: r.shot } });
    if (grow) { li.dataset.to = r.level; rows.set(r.cid, li); }
    return li;
  }));
  const jobs = el('ol', { class: 'jobs' });
  a.jobs.forEach((j, i) => {
    const li = el('li', { class: 'job', 'data-core': String(j.core) });
    const head = el('p', { class: 'job-head' });
    head.append(el('b', { class: 'num', text: `${i + 1}` }), ` ${j.name}`, el('span', { class: 'job-h num', text: ` · ${j.hours}시간` }));
    const from = el('span', { class: 'job-from', text: j.from.join(' + ') });
    li.append(head, el('p', { class: 'job-out', text: `산출물 · ${j.out}` }), from);
    jobs.append(li);
  });
  doc.replaceChildren(...(top ? [top] : []), hero, section(`공고의 필수·우대 역량 ${a.rows.length}개를 이 프로젝트에서 이렇게 다뤄요`, list),
    section(`만들 것 · 일 ${a.jobs.length}개 · ${a.hours.total}시간 (팀 전체)`, jobs));
  adapt = { rows, now, queue: [] };
}
// fill 사건은 모아 두었다가 ③ 이 보이면 하나씩 튼다 (보이지 않는 동안 틀면 움직임이 없다)
export function fill(ev) { adapt?.queue.push(ev); }
// 몇 개든 다 합쳐 1.5초 안 (사용자 11/21: "+1 되는거 좀 느린듯"). 적으면 160ms 간격 그대로
export function playFills() {
  if (!adapt) return;
  const q = adapt.queue.splice(0);
  const gap = Math.min(160, Math.round(1500 / Math.max(q.length, 1)));
  q.forEach((ev, i) => setTimeout(() => step(ev), reducedMotion() ? 0 : i * gap));
}
function step({ id, tier, tier_count: n }) {
  const li = adapt?.rows.get(id);
  const k = adapt?.now[tier];
  if (k && n != null) {
    const gain = Math.round((n - Number(k.b.textContent)) * 10) / 10;
    k.b.textContent = String(n);
    if (gain > 0 && !reducedMotion()) {
      const pop = el('span', { class: 'rs-gain', 'aria-hidden': 'true', 'data-on': '', text: `+${gain}` });      // 하나만: 새것이 앞것을 바꾼다
      k.gain.replaceWith(pop);
      k.gain = pop;
      play(k.b, [{ transform: 'scale(1)' }, { transform: 'scale(1.18)' }, { transform: 'scale(1)' }], 260);
    }
  }
  if (!li) return;
  li.dataset.level = li.dataset.to;
  li.querySelector('.ev-state').dataset.level = li.dataset.to;
  li.dataset.flash = '';
  setTimeout(() => delete li.dataset.flash, 600);
}

const px = (v) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(v)) || 0;
