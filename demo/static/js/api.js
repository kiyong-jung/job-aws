// 서버와 말하기. /api/run 은 POST 로 보내고 text/event-stream 을 읽는다 (EventSource 는 GET 만 되어서 직접 읽는다).
// 사건 하나는 빈 줄로 끝나는 덩어리 하나다. data: 줄이 여럿이면 줄바꿈으로 잇는다. 읽지 못한 덩어리는 건너뛴다.
// 정적 판 (GitHub Pages, demo/export_static.py 가 <meta name="demo-static"> 를 단다): 서버 대신 미리 돌려 둔 사건 파일
// data/runs/<예시>.<단계>[.<공부 시간>].json 을 같은 간격(wait 초 × speed)으로 다시 튼다. 예시가 아닌 공고는 안내 사건 하나
const STATIC = document.querySelector('meta[name="demo-static"]') !== null;
let examples = null;

function parse(chunk) {
  const data = chunk.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).replace(/^ /, '')).join('\n');
  if (!data) return null;
  try { return JSON.parse(data); } catch { return null; }
}

const pause = (ms, signal) => new Promise((resolve, reject) => {
  const t = setTimeout(resolve, ms);
  signal?.addEventListener('abort', () => { clearTimeout(t); reject(new DOMException('', 'AbortError')); }, { once: true });
});

async function replay(payload, onEvent, signal) {
  const list = examples ?? await getExamples();
  const text = String(payload.text || '').trim();
  const ex = list.find((e) => e.text.trim() === text || e.steps_text?.trim() === text);
  if (!ex) {
    onEvent({ type: 'error', reason: 'static', message: '이 사이트는 예시 공고 두 건만 보여 드려요. 다른 공고는 저장소를 받아 컴퓨터에서 돌려 보세요.' });
    return;
  }
  const key = payload.step ? `${payload.step}${payload.budget ? `.${payload.budget}` : ''}` : 'read';
  const res = await fetch(`data/runs/${ex.case}.${key}.json`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const speed = payload.speed ?? 1;
  for (const { wait, ...ev } of await res.json()) {
    if (wait && speed) await pause(wait * speed * 1000, signal);
    if (signal?.aborted) throw new DOMException('', 'AbortError');
    onEvent(ev);
  }
}

export async function run(payload, onEvent, signal) {
  if (STATIC) return replay(payload, onEvent, signal);
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
    let cut;
    while ((cut = buffer.indexOf('\n\n')) >= 0) {
      const ev = parse(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
      if (ev && typeof ev.type === 'string') onEvent(ev);
    }
    if (done) break;
  }
}

// 예시 공고 목록 [{case, label, title, company, text, filename}] (빈 화면 단추 차례)
export const getExamples = () => fetch(STATIC ? 'data/examples.json' : '/api/examples').then((r) => r.json()).then((list) => (examples = list));
