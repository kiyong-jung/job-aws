// ④ 간트차트의 오른쪽 옆 패널 (노션의 side peek, 사용자 11/22: "세부 내용은 클릭하면 오른쪽에 사이드 탭이 뜨게").
// 작업 막대·이름 → 작업 / 주 머리 → 그 주 / 교육자료 동그라미 → 그 자료. 다른 것을 누르면 닫지 않고 내용만 바꾼다.
// 닫기: ✕ 단추 · Esc · 패널 밖 누르기. 열면 초점이 패널 제목으로 가고, 닫으면 누른 것으로 돌아온다. 주소 # 에 지금 보는 것을 적는다 (#w=W2 · #week=9 · #m=L0201).
import { el, icon } from './icons.js';
import { hoursText } from './tables.js';
import { label, picked } from './gantt.js';

const TIER = { 필수: 0, 우대: 1, 나머지: 2 };
const KEYS = { w: 'w', week: 'week', m: 'm' };
const hashOf = (kind, id) => `#${kind}=${encodeURIComponent(id)}`;
const unhash = () => {
  const [, k, v] = location.hash.match(/^#(w|week|m)=(.+)$/) || [];
  return k ? { kind: KEYS[k], id: decodeURIComponent(v) } : null;
};
const setHash = (h) => { try { history.replaceState(null, '', h || location.pathname + location.search); } catch { /* 주소를 못 바꾸는 환경 (file:) 은 그대로 둔다 */ } };

const sec = (title, ...kids) => {
  const s = el('section', { class: 'pk-sec' });
  s.append(el('h3', { class: 'pk-h', text: title }), ...kids);
  return s;
};
const lines = (items) => {
  const ul = el('ul', { class: 'pk-list' });
  items.forEach((x) => ul.append(el('li', { text: x })));
  return ul;
};
// 산출물은 쉼표로 나누되 괄호 안 쉼표는 지킨다
const splitOut = (t) => (t || '').split(/,\s*(?![^()]*\))/).map((x) => x.trim()).filter(Boolean);
// 할 일 글은 문장마다 한 줄 (마침표·물음표 뒤 공백에서. '다.' 로 끝나지 않는 문장도 가른다)
const splitDo = (t) => (t || '').split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);
const note = (t) => t.replace(/^(배정 근거|작업 근거) · /, '');

// 글 속 주소는 링크로 (배정 근거의 "함께 보는 자료 · 이름 https://…")
function linked(text) {
  const p = el('p', { class: 'pk-text' });
  text.split(/(https?:\/\/\S+)/).forEach((s) => {
    if (/^https?:\/\//.test(s)) p.append(el('a', { href: s, target: '_blank', rel: 'noopener noreferrer', text: '링크' }));
    else if (s) p.append(s);
  });
  return p;
}

export function createPeek({ comps = {}, popover, host = document.body } = {}) {
  const root = el('aside', { class: 'peek', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'peek-title', hidden: '' });
  const head = el('header', { class: 'pk-head' });
  const title = el('h2', { class: 'pk-title', id: 'peek-title', tabindex: '-1' });
  const closeBtn = el('button', { type: 'button', class: 'icon-btn pk-close', 'aria-label': '옆 패널 닫기' }, icon('x'));
  head.append(title, closeBtn);
  const body = el('div', { class: 'pk-body' });
  root.append(head, body);
  host.append(root);

  let m = null;          // 간트 모델 (gantt.model)
  let cur = null;        // {kind, id}
  let opener = null;     // 닫으면 초점이 돌아갈 곳 (차트에서 마지막으로 누른 것)
  let timer = 0;
  let page = null;       // 이 패널이 속한 쪽 (쪽이 가려지면 닫는다)
  let watch = null;

  const compChip = (cid, extra = '', shown = '') => {
    const c = comps[cid];
    if (!c) return null;
    const b = el('button', { type: 'button', class: 'wk-comp', 'data-cid': cid, 'data-name': c.name + shown, 'data-tier': c.tier, 'aria-haspopup': 'dialog', 'aria-expanded': 'false' });
    b.append(el('span', { class: 'wk-tier', text: c.tier }), el('span', { text: c.name + shown + extra }));
    return b;
  };
  const chips = (ids) => {
    const box = el('p', { class: 'wk-comps' });
    [...ids].filter(([cid]) => comps[cid]).sort(([a], [b]) => (TIER[comps[a].tier] ?? 3) - (TIER[comps[b].tier] ?? 3))
      .forEach(([cid, basic]) => box.append(compChip(cid, '', basic ? ' 기초' : '')));
    return box;
  };

  // 공부 자료 한 줄 (이름 | 시간, 아래에 배정 근거). 누르면 그 자료로 패널이 바뀐다
  const matItem = (a, withWeek) => {
    const li = el('li', { class: 'pk-mat' });
    const b = el('button', { type: 'button', class: 'pk-mat-btn', 'data-go': 'm', 'data-id': a.id });
    b.append(el('span', { class: 'g-mark g-key-mark', 'aria-hidden': 'true', 'data-picked': picked(a) ? '' : null }),
      el('span', { class: 'pk-mat-name', text: a.title }), el('span', { class: 'pk-mat-h num', text: `${withWeek ? `${a.sem}주차 · ` : ''}${hoursText(a.hours)}` }));
    li.append(b);
    const why = note(a.why?.[0] ?? '').split(' 함께 보는 자료 · ')[0];
    if (why) li.append(el('p', { class: 'pk-why', text: why }));
    return li;
  };
  const link = (a) => (a.url ? el('a', { class: 'pk-link', href: a.url, target: '_blank', rel: 'noopener noreferrer' }, `${icon('external', 16)}<span>자료 열기</span>`) : null);

  // ── 작업 묶음 ──
  function work(r) {
    title.textContent = label(m, r);
    const kids = [];
    if (r.name && r.name !== (r.short || r.name)) kids.push(el('p', { class: 'pk-sub', text: r.name }));
    if (r.held) kids.push(el('p', { class: 'pk-sub', text: '12주 안에는 못 넣어서 뒤로 미뤘어요' }));
    if (r.do) kids.push(sec('할 일', lines(splitDo(r.do))));
    const outs = splitOut(r.out || m.p.plan.flatMap((w) => (w.deliverables || []).filter((d) => d.task === r.id).map((d) => d.out)).join(', '));
    if (outs.length) kids.push(sec('산출물', lines(outs)));
    if (r.total) {
      const list = el('ul', { class: 'pk-weeks' });
      for (const [w, h] of [...r.hours].sort((x, y) => x[0] - y[0])) {
        const li = el('li', { class: 'pk-wk' });
        const track = el('span', { class: 'pk-track', 'aria-hidden': 'true' });
        const fill = el('i');
        fill.style.width = `${Math.min(100, (h / m.p.cap) * 100)}%`;
        track.append(fill);
        li.append(el('span', { class: 'pk-wk-n', text: `${w}주차` }), track, el('span', { class: 'pk-wk-h num', text: hoursText(h) }));
        list.append(li);
      }
      kids.push(sec(`총 ${hoursText(r.total)}`, list));
      kids.push(sec('완료', el('p', { class: 'pk-text', text: `${r.done}주차에 끝나요` })));
    }
    if (r.comps.size) kids.push(sec('다루는 역량', chips(r.comps)));
    if (r.mats.length) kids.push(sec('붙은 공부 자료', (() => { const ul = el('ul', { class: 'pk-mats' }); r.mats.forEach((a) => ul.append(matItem(a, true))); return ul; })()));
    body.replaceChildren(...kids);
  }

  // ── 주 ──
  const goalsOf = (acts) => {
    const out = acts.filter((a) => a.kind === 'project' && a.out).map((a) => (a.done ? a.out : `${a.out} (다음 주까지)`));
    return out.length ? out : acts.filter((a) => a.kind === 'learning').map((a) => `「${a.title}」 공부 끝내기`);
  };
  const todosOf = (acts) => [...acts.filter((a) => a.kind === 'project' && a.check).map((a) => a.check),
    ...acts.filter((a) => a.kind === 'learning').map((a) => `「${a.title}」 공부 · ${hoursText(a.hours)}`)];

  function week(n) {
    const w = m.weeks.get(n);
    const used = w.learning + w.project;
    title.textContent = `${n}주차`;
    const kids = [el('p', { class: 'pk-sub', text: `이번 주 ${hoursText(used)} · 한 주 ${hoursText(m.p.cap)}까지` })];
    const md = m.p.source === 'md';
    kids.push(sec('주간 목표', lines(md && w.goal_steps?.length ? w.goal_steps : goalsOf(w.activities))));
    kids.push(sec('방법', lines(md && w.method_steps?.length ? w.method_steps : todosOf(w.activities))));
    if (w.reason) kids.push(sec('이유', el('p', { class: 'pk-text', text: w.reason.replace(/학습 (\d+)건/g, '배우기 $1건') })));      // 발표 자료는 "배우기"
    const ul = el('ul', { class: 'pk-mats' });
    for (const a of w.activities) {
      if (a.kind === 'learning') { ul.append(matItem({ ...a, sem: n }, false)); continue; }
      const li = el('li', { class: 'pk-mat' });
      const r = m.byId.get(a.id);
      const b = el('button', { type: 'button', class: 'pk-mat-btn', 'data-go': 'w', 'data-id': a.id });
      b.append(el('span', { class: 'pk-build', 'aria-hidden': 'true' }), el('span', { class: 'pk-mat-name', text: r ? label(m, r) : a.title }), el('span', { class: 'pk-mat-h num', text: hoursText(a.hours) }));
      li.append(b);
      ul.append(li);
    }
    kids.push(sec('이번 주 할 일 차례', ul));
    const outs = (w.deliverables || []).map((d) => (typeof d === 'string' ? d : `${d.task} · ${d.out}`));
    if (outs.length) kids.push(sec('이번 주 끝나는 산출물', lines(outs)));
    body.replaceChildren(...kids);
  }

  // ── 교육자료 ──
  function material(a) {
    title.textContent = a.title;
    const kids = [el('p', { class: 'pk-sub', text: `${a.sem}주차 · ${hoursText(a.hours)} · ${picked(a) ? '③에서 고른 자료' : '작업 묶음마다 붙인 자료'}` })];
    const l = link(a);
    if (l) kids.push(l);
    const r = m.byId.get(a.for);
    if (r) {
      const b = el('button', { type: 'button', class: 'pk-mat-btn pk-for', 'data-go': 'w', 'data-id': r.id });
      b.append(el('span', { class: 'pk-mat-name', text: `붙은 작업 묶음 · ${label(m, r)}` }));
      kids.push(b);
    }
    const lv = Object.entries(a.levels || {}).filter(([cid]) => comps[cid]);
    if (lv.length) {
      const box = el('p', { class: 'wk-comps' });
      lv.sort(([x], [y]) => (TIER[comps[x].tier] ?? 3) - (TIER[comps[y].tier] ?? 3)).forEach(([cid, level]) => box.append(compChip(cid, ` · ${level}`)));
      kids.push(sec('다루는 역량', el('p', { class: 'pk-text', text: '있음은 이 자료가 그 역량을 가르친다는 뜻, 일부는 한 부분만 가르친다는 뜻이에요' }), box));
    }
    const why = note((a.why || [])[0] ?? '');
    if (why) kids.push(sec('배정 근거', linked(why.replace(' 함께 보는 자료 · ', '\n함께 보는 자료 · '))));
    body.replaceChildren(...kids);
  }

  function paint() {
    if (!m || !cur) return false;
    if (cur.kind === 'w') { const r = m.byId.get(cur.id); if (!r) return false; work(r); }
    else if (cur.kind === 'week') { if (!m.weeks.has(Number(cur.id))) return false; week(Number(cur.id)); }
    else { const a = m.mats.get(cur.id); if (!a) return false; material(a); }
    body.scrollTop = 0;
    return true;
  }

  function select() {      // 차트에서 열려 있는 것에 표시 (aria-pressed)
    document.querySelectorAll('.gantt [aria-pressed="true"]').forEach((x) => x.setAttribute('aria-pressed', 'false'));
    if (!cur) return;
    document.querySelectorAll(`.gantt [data-peek="${cur.kind}"][data-id="${CSS.escape(String(cur.id))}"]`).forEach((x) => x.setAttribute('aria-pressed', 'true'));
  }

  function show(kind, id, from = null) {
    cur = { kind, id: String(id) };
    if (!paint()) { cur = null; return false; }
    if (from) opener = from;
    const first = root.hidden;
    clearTimeout(timer);
    root.hidden = false;
    page?.setAttribute('data-peek', '');
    if (first) requestAnimationFrame(() => requestAnimationFrame(() => { root.dataset.open = ''; }));
    else root.dataset.open = '';
    select();
    setHash(hashOf(kind, cur.id));
    if (first || from) title.focus({ preventScroll: true });
    return true;
  }

  function close({ focus = true, keepHash = false } = {}) {
    if (root.hidden) return;
    delete root.dataset.open;
    page?.removeAttribute('data-peek');
    cur = null;
    select();
    if (!keepHash) setHash('');
    const done = () => { if (!root.dataset.open) root.hidden = true; };
    timer = setTimeout(done, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 260);
    if (focus && opener?.isConnected) opener.focus({ preventScroll: true });
    opener = null;
  }

  // 차트와 패널 안 누르기
  const onClick = (e) => {
    const t = e.target.closest('[data-peek], [data-go]');
    if (!t || !(t.closest('.gantt') || root.contains(t))) return;
    const kind = t.dataset.peek || t.dataset.go;
    const same = cur && cur.kind === kind && cur.id === t.dataset.id && !root.hidden;
    if (same && !root.contains(t)) { close(); return; }      // 열린 같은 것을 다시 누르면 닫는다
    show(kind, t.dataset.id, root.contains(t) ? null : t);
  };
  const outside = (e) => {
    if (root.hidden || root.contains(e.target) || e.target.closest('.gantt, .comp-pop')) return;
    close({ focus: false });
  };
  const esc = (e) => {
    if (e.key !== 'Escape' || root.hidden || document.querySelector('.comp-pop:not([hidden])')) return;
    close();
  };
  document.addEventListener('click', onClick);
  document.addEventListener('pointerdown', outside);
  document.addEventListener('keydown', esc);
  closeBtn.addEventListener('click', () => close());
  const dropPop = popover?.(root, comps);
  const onHash = () => { const h = unhash(); if (h && m) show(h.kind, h.id); else if (!h && !root.hidden) close({ focus: false, keepHash: true }); };
  addEventListener('hashchange', onHash);

  return {
    // 새 계획을 그렸다: 같은 것이 새 계획에도 있으면 내용을 바꿔 두고, 없으면 닫는다. 처음이면 주소 # 로 연다
    use(model, pageNode) {
      m = model;
      page = pageNode;
      watch?.disconnect();
      watch = new MutationObserver(() => { if (page.hidden) close({ focus: false, keepHash: true }); });
      watch.observe(page, { attributes: true, attributeFilter: ['hidden', 'inert'] });
      const want = cur || unhash();
      if (want && !(root.hidden && !unhash())) { if (!show(want.kind, want.id)) close({ focus: false }); }
      else select();
    },
    close,
    get open() { return !root.hidden; },
    destroy() {
      clearTimeout(timer);
      watch?.disconnect();
      document.removeEventListener('click', onClick);
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', esc);
      removeEventListener('hashchange', onHash);
      dropPop?.();
      if (!root.hidden) setHash('');
      page?.removeAttribute('data-peek');
      root.remove();
    },
  };
}
