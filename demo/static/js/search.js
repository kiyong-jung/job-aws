// ② 프로젝트 찾기 쪽: DB 에서 찾는 그림. 맨 위의 깔때기 띠(DB 111,753 › 낱말로 모은 후보 1,000 › 역량마다 다시 고른 후보 100 › 필수를 다 다룬 후보 1)는
// (끝 칸은 서버의 fit: 필수를 다 다룬 후보가 없는 공고는 '필수를 가장 많이 다룬 후보')
// 사라지지 않고, 그 아래 그림이 위에서 아래로 쌓인다 (DB 점 → 후보 칸 → 1위 카드). 서버의 단계 사건(stage, judged)마다 한 번씩만 움직인다.
//   A (search, scan): 점 하나 = 100개. 논문 덩어리와 저장소 덩어리 (둘 다 먹 60%, 덩어리마다 이름표). 낱말로 모으는 단계에서
//      낱말로 모은 후보 1,000개(점 10개)가 파랑(--pick)으로 켜지고 나머지 점은 옅어진다 (사용자 11/19: 1,000개 고르기를 색으로)
//   A' (rerank): 띠가 둘째 칸으로. 파란 점 10개 가운데 다시 고른 100개(점 1개)만 남는다
//   B (judge): 주 그림 틀(chartCard) 안에 칸 100개(20×5, 휴대폰 10×10)가 자라 나온다. 칸 r 은 순위 r 의 후보이고, 자리는 정해 둔 흩어진 자리다 (자리가 순위를 말하지 않게).
//      판정 한 묶음(5개)이 오면 그 후보들의 칸을 점수 짙기로 채운다. 묶음이 오는 차례도 순위와 상관없다 (pipeline.judge_order)
//   C (pick): 칸이 한 번에 점수 차례로 자리를 옮기고(FLIP), 1위 칸에 고리. 1위 이름과 점수는 바닥 줄 불렛이 말한다
// 숫자는 모두 서버가 보낸 저장본 값이다. 세어 올라가는 숫자처럼 계산하지 않은 값은 그리지 않는다.
import { el, play, reducedMotion } from './icons.js';
import { evRow, evList, section, score, halfNote, tag, LEVEL, appear } from './result.js';

const $ = (id) => document.getElementById(id);
const fmt = (n) => n.toLocaleString('ko-KR');
const PER_DOT = 100;
// 후보 칸은 필수 점수를 높이로 보인다: 칸 아래에서부터 점수 ÷ 만점만큼 먹 60% 로 채운다. 0점은 테두리만, 만점은 먹으로 꽉 (짙기로 가르지 않는다, S4)

let s = null;      // 지금 그림: 노드와 값

// 정해 둔 흩어진 자리: 후보 i 의 칸 자리. 고정 씨앗으로 섞어 돌 때마다 같다
function scatter(n) {
  const a = [...Array(n).keys()];
  let x = 2463534242;
  for (let i = n - 1; i > 0; i--) {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5; x >>>= 0;
    const j = x % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// 깔때기 띠의 한 칸: 이름표, 숫자와 "개". 칸은 오른쪽으로 맞춘다: 이름표 끝과 숫자 끝이 같은 세로선에 서고,
// 숫자 끝에서 › 까지의 거리가 칸마다 같다 (이름표 길이가 그 거리를 바꾸지 않는다).
// 눈에 보이는 이름표는 어느 너비에서나 짧은 이름 (DB · 낱말로 모음 · 다시 고름 · 필수를 다 다룬 후보). 긴 이름은 화면 읽기 프로그램에만 (대화의 진행 목록이 풀어 말한다).
// 띠의 칸 너비는 장면이 바뀌어도 그대로다: 숫자 굵기는 늘 같고, 견준 수는 칸 아래 그림에 쓴다. 칸 사이 › 는 제 칸을 가진 진짜 칸이다 (sep)
// 아직 시작하지 않은 칸은 숫자 줄을 비워 둔다 (자리는 그대로라 칸 너비가 바뀌지 않는다. 그 단계가 시작될 때 숫자가 한 번 나타난다)
function stop(label, short, n, big = false, unit = '개', picked = false) {
  const li = el('li', { class: 'stop', 'data-state': 'todo' });
  const name = el('span', { class: 'stop-label' });
  if (picked) name.append(el('span', { class: 'dot stop-swatch', 'data-picked': '', 'aria-hidden': 'true' }));      // 파란 점 = 낱말로 모은 후보 (DB 그림과 같은 색)
  name.append(el('span', { class: 'stop-long sr-only', text: label }), el('span', { class: 'stop-short', 'aria-hidden': 'true', text: short }));
  const num = el('span', { class: `stop-n num${big ? ' is-db' : ''}`, text: fmt(n) });
  num.append(el('span', { class: 'stop-unit', text: unit }));
  li.append(name, num);
  return { li };
}
const sep = () => el('li', { class: 'stop-sep', 'aria-hidden': 'true', text: '›' });

// steps 사건: 띠와 점·칸을 한 번에 다 만들고, 뒤 사건은 속성만 바꾼다
export function start({ db, pool, shortlist, tier, fit, names }) {
  const root = $('search-doc');
  const total = db.total;      // 서버가 센 DB 크기 (화면은 더하지 않는다)
  root.dataset.stage = 'search';
  root.setAttribute('aria-busy', 'true');
  const funnel = el('ol', { class: 'funnel', 'aria-label': '찾는 차례' });
  const stops = [stop('모아 둔 공개 프로젝트', '공개 프로젝트', total, true), stop('낱말로 모은 후보', '낱말로 모은 후보', pool, false, '개', true),
    stop('역량마다 다시 고른 후보', '다시 고른 후보', shortlist), stop(fit.label, fit.label, fit.n)];
  funnel.append(...stops.flatMap((x, i) => (i ? [sep(), x.li] : [x.li])));

  // DB 점: 논문 덩어리와 저장소 덩어리 (둘 다 먹 60%. 짙기가 아니라 자리와 이름표로 가른다: 덩어리마다 왼쪽 위 이름표, 덩어리 사이 8px)
  const poolBox = el('div', { class: 'pool', role: 'img', 'aria-label': `논문 ${fmt(db.papers)}개와 저장소 ${fmt(db.repos)}개. 점 하나가 ${PER_DOT}개예요` });
  const dots = [];
  for (const [kind, name, n] of [['paper', '논문', db.papers], ['repo', '저장소', db.repos]]) {
    const part = el('div', { class: 'pool-part', 'data-kind': kind });
    const field = el('div', { class: 'field', 'aria-hidden': 'true' });
    for (let i = 0; i < Math.round(n / PER_DOT); i++) dots.push(field.appendChild(el('span', { class: 'dot', 'data-kind': kind })));
    part.append(el('p', { class: 'pool-name num', 'aria-hidden': 'true', text: `${name} ${fmt(n)}개` }), field);
    poolBox.append(part);
  }
  // 낱말로 모은 후보(pool)와 다시 고른 후보(shortlist)의 점: 정해 둔 흩어진 자리 (돌 때마다 같다). 앞 shortlist 몫은 다시 고른 뒤에도 남는다
  const spread = scatter(dots.length);
  spread.slice(0, Math.round(pool / PER_DOT)).forEach((i, k) => {
    dots[i].dataset.picked = '';
    if (k < Math.max(1, Math.round(shortlist / PER_DOT))) dots[i].dataset.kept = '';
  });

  // 칸 r 은 순위 r 의 후보. 자리(order)는 정해 둔 흩어진 자리
  const grid = el('div', { class: 'cells', role: 'img' });
  const cells = scatter(shortlist).map((at) => { const c = el('span', { class: 'cell', style: `order:${at}` }); c.append(el('i')); return c; });
  grid.append(...cells);
  // 범례: 빈 칸(0점) · 반 찬 칸 · 꽉 찬 칸(만점). 설명 글은 두지 않는다
  const keyC = el('p', { class: 'art-key ramp-key' });
  const ends = el('span');
  const sample = (f) => { const c = el('span', { class: 'cell cell-key', 'data-fill': f === 1 ? 'full' : f ? 'part' : 'none', style: `--f:${f}` }); c.append(el('i')); return c; };
  ends.append(el('span', { text: '0점' }), sample(0), sample(0.5), sample(1), el('span', { text: `${tier.total}점` }));
  keyC.append(ends);
  // 단계별 실제 후보 이름 (사용자 11/21): 낱말로 모은 1,000개 가운데 일부 → 다시 고른 100개에 남는 것만 진하게 → 위 다섯과 1위.
  // 논문은 파란 칸, 저장소(깃헙)는 먹 테두리 칸 (색과 글 "논문"·"깃헙" 둘 다로 가른다)
  const namesBox = el('section', { class: 'names', hidden: true });
  const chip = (x) => {
    const c = el('span', { class: 'name-chip', 'data-kind': x.kind, 'data-short': String(x.short ?? true), title: x.title });
    c.append(el('span', { class: 'name-kind', text: x.kind === 'paper' ? '논문' : '깃헙' }), el('span', { class: 'name-title', text: x.title }));
    if (x.rank) c.dataset.rank = x.rank;
    return c;
  };
  const poolChips = (names?.pool || []).map(chip);
  const topChips = (names?.top || []).map((x) => { const c = chip(x); c.prepend(el('b', { class: 'name-rank', text: `${x.rank}위` })); return c; });
  const namesHead = el('p', { class: 'names-head' });
  const namesList = el('div', { class: 'names-list' });
  namesBox.append(namesHead, namesList);
  // 주 그림 틀: 후보 칸과 범례만 (설명 글은 바닥 줄 불렛이 맡는다)
  const short = el('section', { class: 'chart-card short' });
  short.append(grid, keyC);
  short.hidden = true;
  root.replaceChildren(funnel, poolBox, namesBox, short);
  s = { root, stops, short, grid, cells, shortlist, total: tier.total, scores: [], n: 0, top: 0, at: 0,
        names: { box: namesBox, head: namesHead, list: namesList, pool: poolChips, top: topChips, from: names?.pool_from_rerank } };
  move(0);
}

// 띠에서 지금 칸: 앞 칸은 끝남(체크, 흐린 이름표), 뒤 칸은 아직(옅은 글)
function move(at) {
  s.at = at;
  s.stops.forEach(({ li }, i) => {
    li.dataset.state = i < at ? 'done' : i === at ? 'current' : 'todo';
    if (i === at) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
  });
}

// 칸의 화면 읽기 이름: 견준 수 (눈에 보이는 견준 수 줄은 없다. 진행 글과 깔때기 띠가 말한다)
function counter() {
  s.grid.setAttribute('aria-label', `다시 고른 후보 ${fmt(s.shortlist)}개 중 ${fmt(s.n)}개를 견줘 봤어요`);
}

// stage 사건: search 는 장면 A, scan 은 점이 진해진다, rerank 는 범례에 점 열 개, judge 는 범례의 점 하나에서 칸이 자라고,
// pick 은 칸을 점수 차례로 옮긴다
const OWN = new Set(['search', 'scan', 'rerank', 'judge', 'pick']);      // 이 그림의 단계 (응용 단계 borrow·merge 는 ③ 쪽 일이라 그림을 두고 간다)
// 이름 칩: 모으는 단계는 1,000개 가운데 일부, 다시 고르면 100개에 남는 것만 진하게, 고르면 위 다섯 (1위 주황)
function showNames(key) {
  const n = s.names;
  if (!n.pool.length) return;
  n.box.hidden = false;
  if (key === 'scan') { n.head.textContent = n.from ? `낱말로 모은 1,000개 가운데 점수가 높은 ${n.pool.length}개` : `다시 고른 100개 가운데 ${n.pool.length}개`; n.list.replaceChildren(...n.pool); }
  if (key === 'rerank') { n.head.textContent = '뜻으로 다시 고르면 진한 것만 100개에 남아요'; n.list.dataset.cut = ''; }
  if (key === 'pick') { n.head.textContent = '필수를 가장 많이 다룬 차례로 위 다섯'; delete n.list.dataset.cut; n.list.replaceChildren(...n.top); }
}
export function stage(ev) {
  if (!s || !OWN.has(ev.key)) return;
  s.root.dataset.stage = ev.key;
  showNames(ev.key);
  if (ev.key === 'scan') move(1);      // 낱말로 모은 1,000개: 파란 점이 켜지는 때 띠의 숫자도 나타난다
  if (ev.key === 'rerank') move(2);
  if (ev.key === 'judge') {
    s.short.hidden = false;
    counter();
    play(s.grid, [{ transform: 'translateY(12px)', opacity: 0 }, { transform: 'none', opacity: 1 }], 520);
  }
  if (ev.key === 'pick') {
    move(3);
    s.top = ev.top ?? 0;
    sort(ev.order);
  }
}

// 칸을 최종 순위 차례로 (서버가 pick 에 실어 보낸 차례 그대로: 필수 → 우대 → 나머지. 화면은 순위를 셈하지 않는다). 움직임은 한 번, 칸마다 제자리에서 새 자리로
function sort(order) {
  const { cells } = s;
  const rank = order || [...cells.keys()];
  const before = s.grid.getClientRects().length && !reducedMotion() ? cells.map((c) => c.getBoundingClientRect()) : null;
  rank.forEach((i, at) => { cells[i].style.order = String(at); });
  const ring = () => { if (s?.cells === cells) cells[s.top].dataset.top = ''; };
  if (!before) { ring(); return; }
  const mine = cells.map((c, i) => {
    const a = before[i], b = c.getBoundingClientRect();
    return play(c, [{ transform: `translate(${a.left - b.left}px, ${a.top - b.top}px)` }, { transform: 'none' }], 560);
  }).filter(Boolean);
  Promise.all(mine.map((x) => x.finished)).then(ring, ring);
}

// judged 사건: 판정이 끝난 묶음의 칸(순위 번호 ranks)을 점수 짙기로 채운다. 칸 자리는 정해 둔 흩어진 자리 그대로
export function judged({ n, ranks, scores }) {
  if (!s) return;
  ranks.forEach((r, i) => {
    s.scores[r] = scores[i];
    const f = s.total ? scores[i] / s.total : 0;
    s.cells[r].dataset.fill = f >= 1 ? 'full' : f > 0 ? 'part' : 'none';
    s.cells[r].style.setProperty('--f', String(f));
  });
  s.n = n;
  counter();
}

// 멈추거나 끊기면 그림은 그 자리에 둔다 (단계 속성은 그대로라 점·칸이 되돌아가지 않는다). 띠의 지금 칸 아래 "멈췄어요".
// 1위를 이미 골랐으면 띠에는 아무것도 달지 않는다. data-stopped 는 css 가 읽지 않는다 (시험과 디버깅용 표시)
export function stopped() {
  if (!s) return;
  s.root.dataset.stopped = '';
  s.root.removeAttribute('aria-busy');      // 멈췄다는 말은 바닥 줄의 안내가 한다
}

// project 사건: 다 찾았다. 찾는 그림(점·이름·칸)은 걷고 깔때기 띠 아래에 결과를 둔다 (사용자 11/21: 과정보다 결과와 근거).
// 1위 카드(이름, 별, 소개 한 줄, 점수, 2~5위) → 왜 이 공고에 맞나 (필수·우대 역량마다 공고 문장 ↔ 1위 글의 구절) → 1위가 다루지 않는 역량
export function found(ev) {
  if (!s) return;
  s.root.removeAttribute('aria-busy');
  s.stops.forEach(({ li }, i) => { li.dataset.state = i === s.stops.length - 1 ? 'end' : 'done'; });      // 다 찾았다: 끝 칸(1위)은 먹
  if (!ev || ev.adapted) return;      // 응용 프로젝트가 있으면 1위 카드는 그리지 않는다 (adapt 사건에서 최종 응용 하나만, panel.renderAdapted)
  const top = ev.ranking[0], { sample, fit, tiers } = ev;
  const hero = el('section', { class: 'rs-hero' });
  const name = el('h3', { class: 'rs-title' });
  name.append(el('span', { class: 'rs-rank', text: '1위' }), el('span', { class: 'name-kind', 'data-kind': sample.kind === '논문' ? 'paper' : 'repo', text: sample.kind === '논문' ? '논문' : '깃헙' }));
  const link = el('a', { href: sample.url, target: '_blank', rel: 'noopener noreferrer', text: sample.title.split(':')[0] });
  name.append(link, el('span', { class: 'rs-where num', text: sample.where }));
  hero.append(name);
  if (fit.intro) hero.append(el('p', { class: 'rs-intro', text: fit.intro.ko }), el('blockquote', { class: 'rs-en', text: fit.intro.en }));
  const scores = el('div', { class: 'rs-scores' });
  tiers.slice(0, 2).forEach((t, i) => scores.append(score(`${t.name} 역량`, top.scores[i], t.total)));
  hero.append(scores, ...[halfNote(...top.scores.slice(0, 2))].filter(Boolean));
  const rivals = el('ol', { class: 'rs-rivals', 'aria-label': '2~5위' });
  ev.ranking.slice(1, 5).forEach((r) => {
    const li = el('li');
    li.append(el('b', { text: `${r.rank}위` }), ` ${r.title.split(':')[0]} · 필수 ${r.scores[0]} · 우대 ${r.scores[1]}`);
    rivals.append(li);
  });
  hero.append(rivals);
  const who = `1위 ${sample.kind === '논문' ? '논문' : 'README'}`;
  const row = (r) => evRow({ cid: r.cid, tier: r.tier, name: r.name, level: r.level, state: LEVEL[r.level],
    left: { who: '공고', text: r.posting, ko: r.posting_ko }, right: { who, text: r.quote, ko: r.quote_ko, url: sample.url } });
  const has = fit.rows.filter((r) => r.level !== '없음'), none = fit.rows.filter((r) => r.level === '없음');
  const parts = [s.stops[0].li.parentElement, hero, section('왜 이 공고에 맞나: 공고 문장과 1위 글의 같은 뜻 구절', evList(has.map(row)))];
  if (none.length) {
    const ul = el('ul', { class: 'rs-gaps' });
    none.forEach((r) => { const li = el('li'); li.append(tag(r.tier), ` ${r.name}`); ul.append(li); });
    parts.push(section(`1위가 다루지 않는 역량 ${none.length}개는 ③ 응용에서 채워요`, ul));
  }
  s.root.replaceChildren(...parts);
  s.root.scrollTop = 0;
  appear(hero);
}

// 비우기: 그림과 쪽 칸의 속성까지 (다음 그림이 지난 단계·멈춤 속성을 물려받지 않게)
export function clear() {
  s = null;
  const root = $('search-doc');
  root.replaceChildren();
  root.removeAttribute('aria-busy');
  for (const k of Object.keys(root.dataset)) delete root.dataset[k];
}

// 깔때기 띠 (최종 응용 쪽이 맨 위에 그대로 둔다)
export const funnel = () => s?.stops[0].li.parentElement ?? null;
