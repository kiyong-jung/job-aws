// 시작점: 시작 화면(공고 넣기) → 서버 사건 → 대시보드 쪽 그림. 사건마다 처리기 하나 (handlers). 대화 칸은 없다 (사용자 11/19).
// 쪽마다 바닥 줄 하나: 한 줄 불렛 둘 + 다음 단계 단추 (panel.foot). 단추를 누르면 같은 공고로 그 단계를 돈다 (STEPS, runStep):
// `이 역량으로 프로젝트 찾기` → `교육자료 찾기` → (하루 1·2·3시간으로 12주 계획 짜기) → `정리 리포트 만들기`.
// 공부 시간(budget)은 12주 계획 앞에서 단추로 한 번 고르고, 그 뒤에는 ⑤ ⑥ 쪽의 라디오 칸으로 바꾼다 (다시 틀지 않고 그린 쪽을 제자리에서 다시 쓴다, switchBudget).
import { run, getExamples } from './api.js';
import { scoreText, hoursText } from './tables.js';
import * as panel from './panel.js';
import * as search from './search.js';
import * as study from './study.js';
import * as weeks from './weeks.js';
import * as report from './report.js';
import * as budgetUI from './budget.js';
import { createComposer } from './composer.js';
import { icon, setInstant } from './icons.js';
import { store, resetResult, resetProject, resetStudy, resetWeeks, resetReport } from './store.js';

const $ = (id) => document.getElementById(id);
const app = $('app');
const fmt = (n) => n.toLocaleString('ko-KR');

const composer = createComposer({ onSend: (payload) => send(payload), onStop: () => store.controller?.abort(), onAdd: toLanding });
panel.init();
composer.setRunning(false);

function announce(text) { $('announce').textContent = text; }
// 쪽 머리 상태 줄의 말은 둘뿐이다: 저장해 둔 실행을 다시 트는 단계(① ② ④)와 사람이 손으로 만든 단계(⑤ ⑥). 도는 동안은 지금 하는 일
const REPLAY = '';      // 상태 줄에 '미리 돌려 둔 결과' 같은 말을 두지 않는다 (사용자 11/21). 도는 동안의 '…하는 중' 만 보인다
// ① 공고 읽기의 걸음 (서버 STAGES 와 같은 차례) · ② 사건 가운데 ③ 응용 쪽의 걸음
const READ_STEPS = [{ key: 'read', label: '공고 읽기' }, { key: 'split', label: '문장 나누기' }, { key: 'find', label: '핵심 문장 찾기' }, { key: 'sort', label: '역량 정리' }];
const HAND = '';

// 예시 공고 (서버가 보낸 차례: AWS 먼저). 시작 화면에 단추 하나씩, 누르면 그 공고 글을 파일 칩으로 붙인다.
// 대시보드의 안내(준비 중, 예시가 아닌 공고)에 다는 예시 단추는 누르면 바로 그 공고로 처음부터 돈다
let examples = [];
const useExample = (ex) => composer.add({ kind: 'file', name: ex.filename, size: new Blob([ex.text]).size, text: ex.text, title: ex.title });
const exampleActions = (skip = null) => examples.filter((ex) => ex.case !== skip).map((ex) => [ex.label, () => send({ text: ex.text, title: ex.title })]);
getExamples().then((list) => {
  examples = list;
  $('starters').replaceChildren(...list.map((ex) => {
    const b = document.createElement('button');
    Object.assign(b, { className: 'text-btn', type: 'button', textContent: ex.label });
    b.dataset.example = ex.case;
    b.addEventListener('click', () => useExample(ex));
    return b;
  }));
});

// 시작 화면으로: 도는 일을 멈추고 대시보드를 비운다 (왼쪽 위 로고, 대시보드에 공고 파일을 끌어다 놓기)
function toLanding() {
  if (app.dataset.empty === 'true') return;
  store.controller?.abort();
  store.controller = null;
  composer.setRunning(false);
  reset({ all: true });
  app.dataset.empty = 'true';
  $('top-title').textContent = '';
  $('new-chat').disabled = true;
}
$('brand-new').innerHTML = icon('plus', 16);
$('new-chat').addEventListener('click', () => { toLanding(); composer.focus(); });

// 비우기 한 곳: 쪽 더미, 쪽 안 그림, 화면 상태. all 이면 공고까지 (새 공고), 아니면 from 단계와 그 뒤 단계의 결과만
// (다시 찾기: 프로젝트를 다시 찾으면 교육자료와 12주 계획도 비운다)
const CLEAR = { search: [search, study, weeks, report], materials: [study, weeks, report], weeks: [weeks, report], report: [report] };
const FORGET = { search: resetProject, materials: resetStudy, weeks: resetWeeks, report: resetReport };
function reset({ all = false, from = 'search' } = {}) {
  stopSwitch();      // 바꾸는 중에 다른 일이 시작되면 늦게 올 바꾸기 응답은 버린다
  panel.reset({ all, from });
  CLEAR[from].forEach((art) => art.clear());
  panel.placeBudget();
  if (all) { resetResult(); setBudget(null); store.live = null; } else FORGET[from]();
  syncSwitch();
}

// 다시 해도 같은 결과가 나올 까닭(막힌 사이트, 로그인, 짧은 글 등)에는 다시 해 보기를 주지 않는다
const TEMPORARY = new Set(['server', 'network', 'http']);
const retry = () => { if (!store.controller && store.last) send(store.last); };
// 새 공고 라이브 (demo/live.py): 서버는 상태를 두지 않는다. 단계마다 받은 결과(live_state)를 모아 다음 단계 요청에 싣는다
const liveState = (ev) => { store.live = { ...(store.live || {}), [ev.key]: ev.value }; };

// ── 1단계: 공고 읽기. ① 쪽에 원문과 형광펜, 오른쪽에 찾은 역량 칸 ──
const handlers = {
  stage(ev) {
    panel.progress('posting', ev.label, ev.key);
    announce(ev.label);
  },
  posting(ev, ctx) {
    ctx.posted = true;
    store.adapted = Boolean(ev.adapted);      // 이 공고의 저장본에 응용 프로젝트가 있으면 ③ 쪽 이름은 처음부터 "응용"
    store.example = ev.case ?? null;          // 예시 공고의 이름 (새 공고면 없음)
    store.pending = ev.pending ?? {};         // 저장본이 아직 없는 단계 → 그 단추 대신 적을 글
    store.text = ev.sections.flatMap((sec) => sec.items.map((x) => x.text)).join('\n');
    app.dataset.empty = 'false';
    $('new-chat').disabled = false;
    $('top-title').textContent = ev.title;
    ctx.status = ev.replay ? REPLAY : '';
    panel.retitle();
    panel.renderPosting(ev);
    panel.status(ctx.status, 'posting');
    panel.open();
  },
  highlight(ev) { panel.paint(ev.sid, ev.n); },
  live_state: liveState,
  row(ev) {
    store.rows.set(ev.row.id, { ...ev.row });
    panel.addCell(ev.row);
  },
  done(ev, ctx) {
    ctx.ended = true;
    panel.doneReading();
    panel.status(ctx.status, 'posting');
    const rest = ev.rows - ev.required - ev.preferred;
    panel.foot('posting', [`핵심 문장 ${ev.marks}개에서 역량 ${ev.rows}개를 찾았어요`, `필수 ${ev.required}개 · 우대 ${ev.preferred}개 · 나머지 ${rest}개`],
      ev.rows ? next('project') : []);
    announce(`역량 ${ev.rows}개를 찾았어요`);
  },
  notice(ev, ctx) {
    ctx.ended = true;
    panel.status('원문만 보여 드려요', 'posting');
    panel.foot('posting', [ev.text], exampleActions());
  },
  error(ev, ctx) {
    ctx.ended = true;
    if (!ctx.posted) { toLanding(); composer.showError(ev.message); return; }      // 공고를 못 읽었다: 시작 화면의 입력창 아래에
    panel.foot(panel.top(), [ev.message], TEMPORARY.has(ev.reason) ? [['다시 해 보기', retry]] : []);
  },
};

// 요청 하나를 흘려 받는다. 끝 사건 없이 닫히거나 끊기면 지금 쪽 바닥 줄에 안내와 `다시 해 보기`
async function stream(payload, table, ctx, again) {
  store.controller?.abort();
  const controller = new AbortController();
  store.controller = controller;
  composer.setRunning(true);
  syncSwitch();
  const broke = (text) => {
    ctx.onStop?.();
    if (!ctx.posted && table === handlers) { toLanding(); composer.showError(text); return; }
    panel.foot(panel.top(), [text], [['다시 해 보기', again]]);
  };
  try {
    await run(payload, (ev) => {
      if (ctx.budget && ev.budget_key && ev.budget_key !== ctx.budget) return;      // 늦게 온 다른 안의 사건은 버린다
      ctx.log?.push(ev);
      if (Object.hasOwn(table, ev.type)) table[ev.type](ev, ctx);
    }, controller.signal);
    if (!ctx.ended) broke('중간에 끊겼어요. 다시 해 볼까요?');
  } catch (e) {
    if (e.name === 'AbortError') { ctx.aborted = true; ctx.onStop?.(); }
    else broke('연결이 끊겼어요. 잠시 뒤 다시 해 볼까요?');
  } finally {
    if (store.controller === controller) {      // 그사이 새 요청이 시작됐으면 그쪽 상태를 건드리지 않는다
      store.controller = null;
      composer.setRunning(false);
      syncSwitch();
    }
  }
}

async function send(payload) {
  stopSwitch();
  store.controller?.abort();
  store.last = payload;
  reset({ all: true });
  composer.showError('');
  const ctx = { ended: false, posted: false };
  panel.walk('posting', READ_STEPS);
  await stream(payload, handlers, ctx, retry);
}

// ── 2~5단계. 앞 단계의 쪽은 그대로 두고 새 쪽을 밀어 넣는다 ──
function openStep(ctx, key, status) {
  ctx.status = status;
  if (ctx.quiet) return;      // 안을 바꿔 다시 쓰는 중: 쪽도 초점도 그대로
  panel.status(status, key);
  panel.reveal(key);
  panel.box(key).focus({ preventScroll: true });
}
// 단계가 끝났다: 상태 줄을 다시 틀기 알림으로 되돌린다
const settle = (ctx, key) => panel.status(ctx.status, key);
const progress = (key) => (ev, ctx) => {
  if (ctx.quiet) return;
  panel.progress(key, ev.label, ev.key);
  announce(ev.label);
};
// 새 공고(예시가 아님), 아직 준비 중인 단계: 지금 쪽 바닥 줄에 그 글과 다른 예시 단추
const stepNotice = (ev, ctx) => {
  ctx.ended = true;
  ctx.onStop();
  panel.foot(panel.top(), [ev.text], exampleActions(store.example));
};
const stepError = (ev, ctx) => {
  ctx.ended = true;
  ctx.onStop();
  panel.foot(panel.top(), [ev.message], TEMPORARY.has(ev.reason) ? [['다시 해 보기', ctx.again]] : []);
};
// 끝까지 그렸다: 공부 시간을 바꿀 때 다시 쓸 사건을 적어 둔다
function finishRun(ctx, key) {
  if (ctx.quiet) return;
  store.drawn.add(key);
  store.runs.set(`${key}:${ctx.budget}`, ctx.log);
  syncSwitch();
}

// ── 2단계: 프로젝트 찾기. ② 쪽에 DB 그림, 응용 프로젝트가 있으면 ③ 쪽에 덮기 띠 ──
const projectHandlers = {
  steps(ev, ctx) {
    ctx.db = ev.db.total;      // 서버가 센 DB 크기
    store.adapted = Boolean(ev.adapted);
    panel.retitle();
    search.start(ev);
    panel.walk('search', ev.items);      // 찾기와 응용이 한 쪽 (사용자 11/21)
    // 다시 틀기임을 숨기지 않는다. 실제로 걸린 시간은 저장본에 있을 때만 적는다 (없으면 지어내지 않는다)
    openStep(ctx, 'search', REPLAY);
  },
  stage(ev, ctx) {
    search.stage(ev);
    progress('search')(ev, ctx);
  },
  judged(ev) { search.judged(ev); },
  live_state: liveState,
  pending_adapt(ev, ctx) {      // 새 공고: 응용은 다음 요청. 이 요청이 닫히면 바로 이어서 부른다
    ctx.ended = true;
    store.lastProject = ctx.project;
    store.lastDb = ctx.db;
    const text = store.text;
    const go = () => { if (store.text !== text) return; if (store.controller) { setTimeout(go, 50); return; } runStep('adapt'); };
    setTimeout(go, 0);
  },
  // ② 바닥 줄: "111,753개 중 1위 · genkit-ai/genkit" / "필수 8점 중 5.5점" (제목은 ':' 앞까지)
  project(ev, ctx) {
    const [tier] = ev.tiers, top = ev.ranking[0].scores[0];
    ctx.project = ev;
    store.kind = ev.sample.kind;
    search.found(ev);
    settle(ctx, 'search');
    panel.foot('search', [`${fmt(ctx.db)}개 중 1위 · ${ev.sample.title.split(':')[0]}`, `${tier.name} ${scoreText(top, tier.total)}`]);
  },
  cover(ev) {
    const row = store.rows.get(ev.row.id);
    if (row) Object.assign(row, { level: ev.row.level, tier: ev.row.tier });
  },
  // 최종 응용 프로젝트: ② 쪽의 찾는 그림을 걷고 깔때기 띠 아래에 그린다 (1위와 응용을 따로 두지 않는다)
  adapt(ev, ctx) {
    ctx.adapt = ev;
    panel.renderAdapted(ev, { db: ctx.db, top: search.funnel() });
  },
  fill(ev) { panel.fill(ev); },
  done(ev, ctx) {
    ctx.ended = true;
    settle(ctx, 'search');
    store.budgets = ev.budgets ?? [];
    budgetUI.build(store.budgets, switchBudget, () => announce('지금 단계가 끝나면 바꿀 수 있어요'));
    if (!ctx.project) return;
    const { 있음: yes, 일부: part, 없음: no } = ev.levels;
    if (!ctx.adapt) {      // 응용 프로젝트가 없는 공고: ② 바닥 줄에 다음 단추
      panel.foot('search', null, next('materials'));
      announce(`${fmt(ctx.db)}개 중 1위를 골랐어요. 역량 ${yes + part + no}개 중 ${yes}개를 다루고, ${part}개는 일부만 다뤄요`);
      return;
    }
    // ② 바닥 줄: "111,753개에서 고른 1위 genkit-ai/genkit 바탕" / "필수 8개 중 8 · 우대 11개 중 9.5"
    const [must, nice] = ctx.adapt.tiers;
    panel.foot('search', [`${fmt(ctx.db)}개에서 고른 1위 ${ctx.adapt.base.title} 바탕에 빈 역량을 빌려 채웠어요`,
      `필수 ${must.total}개 중 ${must.after} · 우대 ${nice.total}개 중 ${nice.after}`], next('materials'));
    panel.playFills();
    announce(`응용 프로젝트는 역량 ${yes + part + no}개 중 ${ev.after}개를 다뤄요`);
  },
  notice: stepNotice,
  error: stepError,
};

// ── 3단계: 교육자료 (m3_materials/pick.py 결과를 다시 튼다). ④ 쪽에 자료 × 역량 행렬 (study.js) ──
const materialHandlers = {
  live_state: liveState,
  steps(ev, ctx) {
    study.start(ev.funnel);
    openStep(ctx, 'materials', REPLAY);
    panel.walk('materials', ev.items);
  },
  stage(ev, ctx) {
    study.stage(ev.key);
    progress('materials')(ev, ctx);
  },
  target(ev) { study.target(ev.row); },
  pick(ev) { study.pick(ev.row, ev.levels); },
  done(ev, ctx) {
    ctx.ended = true;
    study.done(ev);
    settle(ctx, 'materials');
    panel.foot('materials', [`교육자료 ${ev.n}개를 골랐어요 · 핵심 자료는 위, 보조 자료는 아래`, ev.line.split(' (')[0]], choose());      // 괄호 풀이는 그림의 반 칸이 말한다
    announce(`교육자료 ${ev.n}개를 골랐어요. ${ev.line}`);
    finishRun(ctx, 'materials');
  },
  notice: stepNotice,
  error: stepError,
};

function weeksFoot(ev) {
  const inside = ev.inside_weeks < ev.weeks ? `${ev.weeks}주 중 ${ev.inside_weeks}주는 그 안에` : `${ev.weeks}주 모두 그 안에`;
  const who = ev.source === 'md' ? '' : ' (한 사람)';      // md 계획은 한 사람 기준이라고 적혀 있지 않다
  panel.foot('weeks', [`교육자료로 배우기 ${hoursText(ev.learning)} · 프로젝트에 적용 ${hoursText(ev.project)}${who}`,
    `한 주 ${hoursText(ev.cap)}까지 · ${inside} · 산출물 ${ev.deliverables}개`],
  store.drawn.has('report') ? [] : next('report'));      // 공부 시간을 바꿔 다시 그려도(quiet) 아직 리포트가 없으면 단추는 남는다
  return inside;
}
weeks.picked((sum) => { if (store.drawn.has('weeks') && !store.controller) weeksFoot(sum); });      // 도는 중이면 done 이 고른 계획으로 쓴다

// ── 4단계: 12주 계획 (예시는 주차 계획 md, 새 공고는 라운드랩 커리큘럼 생성기 결과). ⑤ 쪽에 12주 막대와 주마다 "배우기 → 적용 → 산출물" (weeks.js) ──
const weekHandlers = {
  live_state: liveState,
  steps(ev, ctx) {
    store.ownHours = ev.plans?.length > 1;      // 한 주 공부 시간을 ④ 안에서 고르는 예시: ④ 쪽에서는 하루 1·2·3시간 칸을 숨긴다 (panel.head)
    weeks.start(ev);
    openStep(ctx, 'weeks', HAND);
    if (!ctx.quiet) panel.walk('weeks', ev.items);
  },
  stage: progress('weeks'),
  // ⑤ 바닥 줄: "교육자료로 배우기 7시간 30분 · 프로젝트에 적용 70시간" / "한 주 7시간까지 · 12주 모두 그 안에 · 산출물 9개" (수는 모두 서버 값).
  // 계획 크기(중·대)를 고르는 예시는 고른 계획의 수 (weeks.summary)
  done(ev, ctx) {
    ctx.ended = true;
    weeks.done(ev);
    settle(ctx, 'weeks');
    const inside = weeksFoot(weeks.summary() ?? ev);
    if (!ctx.quiet) announce(`${ev.weeks}주 계획을 짰어요. ${inside}`);
    finishRun(ctx, 'weeks');
  },
  notice: stepNotice,
  error: stepError,
};

// ── 5단계: 정리 리포트. ⑥ 쪽에 발표 자료 모양의 면접 대비 슬라이드 (report.js) ──
const reportHandlers = {
  live_state: liveState,
  steps(ev, ctx) {
    report.start();
    openStep(ctx, 'report', HAND);
    if (!ctx.quiet) panel.walk('report', ev.items);
  },
  stage: progress('report'),
  // ⑥ 바닥 줄: 서버가 리포트 쪽에서 센 값 (질문 수, 은행 질문 수)과 `pptx 받기`
  done(ev, ctx) {
    ctx.ended = true;
    report.done(ev);
    settle(ctx, 'report');
    panel.foot('report', ev.bullets, ev.pptx ? [{ label: 'pptx 받기', href: ev.pptx, download: ev.filename }] : []);
    if (!ctx.quiet) announce('정리 리포트를 만들었어요');
    finishRun(ctx, 'report');
  },
  notice: stepNotice,
  error: stepError,
};

// 다음 단계 넷. label 은 바닥 줄 단추(다음에 일어날 일을 동사로), from 은 그 단계의 쪽 (다시 하면 그 쪽부터 비운다).
// 12주 계획은 단추가 하나가 아니라 하루 1·2·3시간 단추 셋이다 (choose)
const STEPS = {
  project: { label: '이 역량으로 프로젝트 찾기', from: 'search', handlers: projectHandlers, art: search },
  materials: { label: '교육자료 찾기', from: 'materials', handlers: materialHandlers, art: study },
  weeks: { label: '12주 계획 짜기', from: 'weeks', handlers: weekHandlers, art: weeks },
  report: { label: '정리 리포트 만들기', from: 'report', handlers: reportHandlers, art: report },
  adapt: { from: 'materials', handlers: projectHandlers, art: search },      // 새 공고: ② 응용 (두 번째 요청, 같은 쪽에 그린다)
};
// 이 예시의 저장본이 아직 없는 단계는 단추 대신 그 글 (서버가 보낸 글, 예시 단추는 그 글의 쪽에서 다시 고른다)
// 다음 단계는 바닥 줄 단추로 연다 (사용자 11/21: 읽고 나서 단추로 넘긴다). 12주 계획은 첫 안(하루 1시간)으로 짜고, 바꾸기는 ⑤ ⑥ 의 라디오 칸
const next = (key, pick = null) => (store.pending[key] ? [] : [[`${STEPS[key].label} →`, () => { if (!store.controller) runStep(key, pick); }]]);
const choose = () => (store.pending.weeks || !store.budgets.length ? [] : next('weeks', store.budgets[0].key));
const perDayText = (key = store.budget) => `하루 ${store.budgets.find((b) => b.key === key)?.per_day}시간`;

// 고른 안을 한 곳에서 바꾼다: 상태, 라디오 칸
function setBudget(key) {
  store.budget = key;
  budgetUI.value(key);
  panel.retitle();
}
// 라디오 칸은 자료를 찾는 중이거나 아직 그린 12주 계획이 없으면 막는다
function syncSwitch() { budgetUI.lock(Boolean(store.controller) || !store.drawn.has('weeks')); }

async function runStep(key, pick = null) {
  stopSwitch();
  const step = STEPS[key], text = store.text;
  if (pick) setBudget(pick);
  panel.dropActions();      // 누른 단추와 앞 쪽들의 다음 단계 단추를 거둔다 (불렛은 남는다)
  reset({ from: step.from });
  // 같은 공고가 그대로일 때만 다시 하게 한다 (그사이 새 공고를 보냈으면 그 공고 것이 아니다)
  const again = () => { if (store.text === text && !store.controller) runStep(key, key === 'weeks' ? store.budget : null); };
  const budget = ['project', 'materials'].includes(key) ? null : store.budget;
  const ctx = { ended: false, again, onStop: () => step.art.stopped(), budget, log: [], posted: true,
    ...(key === 'adapt' ? { project: store.lastProject, db: store.lastDb } : {}) };
  await stream({ step: key, text, ...(budget ? { budget } : {}), ...(store.live?.case ? { state: store.live } : {}) }, step.handlers, ctx, again);
}

// ── 공부 시간 바꾸기 (⑤ ⑥ 쪽의 라디오 칸). 다시 틀지 않는다: 그린 단계의 사건을 서버에서 기다림 없이(speed 0) 받아(받아 둔 것은 그대로)
// 같은 처리기에 넣어 쪽 그림과 바닥 줄을 제자리에서 다시 쓴다. 같은 값은 아무 일 없음, 늦게 온 응답은 버린다, 실패하면 칸을 되돌린다 ──
const DOCS = { weeks: 'weeks-doc', report: 'report-doc' };      // 공부 시간을 쓰는 쪽 (④ 교육자료는 쓰지 않는다)
async function fetchLog(step, key, signal) {
  const log = [];
  await run({ step, text: store.text, budget: key, speed: 0, ...(store.live?.case ? { state: store.live } : {}) }, (ev) => log.push(ev), signal);
  if (signal.aborted) throw new DOMException('', 'AbortError');
  if (log[0]?.type !== 'steps' || log.at(-1)?.type !== 'done' || log.some((e) => e.budget_key !== key)) throw new Error('budget');
  store.runs.set(`${step}:${key}`, log);
  return log;
}
function redraw(step, log) {
  const { handlers: table, art } = STEPS[step];
  art.clear();
  const ctx = { quiet: true, ended: false, budget: log[0].budget_key, again() {}, onStop() {} };
  for (const ev of log) if (Object.hasOwn(table, ev.type)) table[ev.type](ev, ctx);
}
function stopSwitch() {
  if (!store.switching) return;
  store.switching.abort();
  store.switching = null;
  budgetUI.busy(false);
  Object.values(DOCS).forEach((id) => $(id).removeAttribute('aria-busy'));
  budgetUI.value(store.budget);
}
async function switchBudget(key) {
  if (key === store.budget) { stopSwitch(); budgetUI.value(key); return; }
  if (store.controller || !store.drawn.has('weeks')) { budgetUI.value(store.budget); return; }
  if (!store.drawn.has('report')) { report.clear(); resetReport(); }      // 끝까지 못 그린 ⑥ 쪽은 옛 안의 그림이다
  store.switching?.abort();
  const ac = (store.switching = new AbortController());
  const steps = Object.keys(DOCS).filter((k) => store.drawn.has(k));
  budgetUI.busy(true);
  steps.forEach((k) => $(DOCS[k]).setAttribute('aria-busy', 'true'));
  try {
    const logs = await Promise.all(steps.map((k) => store.runs.get(`${k}:${key}`) ?? fetchLog(k, key, ac.signal)));
    if (ac.signal.aborted || store.controller) return;
    setInstant(true);
    try { steps.forEach((k, i) => redraw(k, logs[i])); } finally { setInstant(false); }
    setBudget(key);
    announce(`${perDayText(key)}으로 바꿨어요`);
  } catch (e) {
    if (e.name !== 'AbortError' && store.switching === ac) {
      budgetUI.value(store.budget);
      announce('공부 시간을 바꾸지 못했어요. 지금 그림은 그대로예요');
    }
  } finally {
    panel.placeBudget();
    if (store.switching === ac) {
      store.switching = null;
      budgetUI.busy(false);
      steps.forEach((k) => $(DOCS[k]).removeAttribute('aria-busy'));
    }
  }
}
