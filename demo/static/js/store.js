// 화면 상태는 여기 한 곳에 둔다. 다른 모듈은 이 값을 읽고, DOM 속성을 다시 읽어 상태를 짐작하지 않는다.
export const store = {
  controller: null,      // 지금 도는 요청의 AbortController. 끝난 요청이 새 요청 것을 지우지 않게 비교해서만 비운다
  last: null,            // 마지막으로 보낸 요청. "다시 해 보기"가 그대로 다시 보낸다
  rows: new Map(),       // 역량 id → {id, name, type, priority, sids, badges, level, tier}. 지금 공고의 것만 (level·tier 는 1위 판정, cover 사건)
  marks: new Map(),      // 문장 번호 n → 형광펜 mark
  stack: ['posting'],    // 쪽 더미, 아래부터 위로 ('posting' → 'search' → 'sample' → 'materials' → 'weeks' → 'report'). panel.reveal 만 바꾼다
  text: '',              // 지금 공고의 문장들. 다음 단계가 서버에 다시 보낸다 (주소를 다시 열지 않게)
  kind: '',              // 1위의 종류 (논문, 저장소)
  adapted: false,        // 이 공고의 저장본에 응용 프로젝트가 있다 (③ 쪽 이름이 "응용 프로젝트"). 공고가 바뀔 때만 지운다
  example: null,         // 예시 공고의 이름 (posting 사건의 case. 새 공고면 null). 안내의 예시 단추에서 지금 공고를 뺀다
  pending: {},           // 이 예시의 저장본이 아직 없는 단계 → 화면 글 (posting 사건). 그 단계는 단추 대신 이 글
  // 공부 시간 고르기. 값은 서버가 보낸 목록(budgets: [{key, hours, per_day}])의 열쇠만 쓴다
  budgets: [],           // 2단계 끝 사건이 싣는 안 목록. 새 공고가 오면 비운다
  budget: null,          // 고른 안의 열쇠 ("84"). 처음 고르기 단추를 누르면 정해진다 (setBudget 만 바꾼다)
  ownHours: false,       // ④ 가 한 주 공부 시간(주 14·15·28시간)을 스스로 고르는 예시다. ④ 쪽에서는 하루 공부 시간 칸을 숨긴다 (12주 계획을 다시 하면 지운다)
  drawn: new Set(),      // 끝까지 그린 단계 ('materials' | 'weeks' | 'report')
  runs: new Map(),       // `${단계}:${안}` → 사건들. 끝까지 받은 것만 (안을 바꿔 돌아올 때 서버에 다시 묻지 않는다)
  switching: null,       // 안 바꾸기 요청의 AbortController (controller 와 따로)
};

// 한 단계의 "그렸다" 기록을 지운다 (다시 하기 전에)
function forget(step) {
  store.drawn.delete(step);
  [...store.runs.keys()].filter((k) => k.startsWith(`${step}:`)).forEach((k) => store.runs.delete(k));
}

export function resetReport() { forget('report'); }
export function resetWeeks() {
  resetReport();
  forget('weeks');
  store.ownHours = false;
}
export function resetStudy() {
  resetWeeks();
  forget('materials');
}
export function resetProject() {
  resetStudy();
  store.kind = '';
  store.rows.forEach((r) => { r.level = null; r.tier = null; });
}
export function resetResult() {
  resetProject();
  store.rows.clear();
  store.marks.clear();
  store.adapted = false;
  store.example = null;
  store.pending = {};
  store.text = '';
  store.budgets = [];
  store.budget = null;
}
