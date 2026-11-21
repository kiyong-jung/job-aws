// 입력창: 글이 늘면 함께 커지고, 파일·긴 붙여넣기·예시는 칩으로 붙는다. 창 어디에 끌어다 놓아도 받는다.
import { el, icon } from './icons.js';

const LONG_PASTE = 400;      // 이보다 긴 붙여넣기는 칩으로 바꾼다
const URL_ONLY = /^https?:\/\/\S+$/i;
const $ = (id) => document.getElementById(id);

export function chipNode(a, onRemove) {
  const chip = el('div', { class: 'chip' }, `<span class="chip-icon">${icon(a.kind === 'paste' ? 'text' : 'file')}</span>`);
  const text = el('span', { class: 'chip-text' });
  text.append(el('span', { class: 'chip-name', text: a.name, title: a.name }));
  chip.append(text);
  if (onRemove) {
    const x = el('button', { class: 'icon-btn', type: 'button', 'aria-label': `${a.name} 첨부 빼기` }, icon('x', 16));
    x.addEventListener('click', onRemove);
    chip.append(x);
  }
  return chip;
}


async function readFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext === 'pdf') throw new Error('PDF는 아직 읽지 못해요. 공고 내용을 복사해 붙여넣어 볼까요?');
  if (!['txt', 'md', 'html', 'htm'].includes(ext) && !file.type.startsWith('text/')) {
    throw new Error('이 파일은 읽지 못했어요. 텍스트·HTML 파일이나 붙여넣기로 해 볼까요?');
  }
  const body = await file.text();
  const isHtml = ext === 'html' || ext === 'htm' || file.type === 'text/html';
  return { kind: 'file', name: file.name, size: file.size, text: isHtml ? '' : body, html: isHtml ? body : '' };
}

export function createComposer({ onSend, onStop, onAdd = () => {} }) {
  const form = $('composer'), input = $('composer-input'), send = $('send');
  const list = $('attachments'), error = $('composer-error'), fileInput = $('file-input');
  const drop = $('drop');
  let items = [], running = false;

  $('attach').innerHTML = icon('plus');
  $('drop-icon').innerHTML = icon('upload', 28);

  function render() {
    list.replaceChildren(...items.map((a, i) => chipNode(a, () => { items.splice(i, 1); render(); input.focus(); })));
    send.disabled = !running && !items.length && !input.value.trim();
  }
  function fit() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 240)}px`;
    render();
  }
  function showError(msg) {
    error.textContent = msg || '';
    error.hidden = !msg;
  }
  function add(a) {
    items = [a];      // 공고는 한 번에 하나만 본다
    onAdd();          // 대시보드를 보는 중에 공고 파일을 끌어다 놓으면 시작 화면으로 (main.js)
    showError('');
    render();
    input.focus();
  }
  async function addFiles(files) {
    const file = files && files[0];
    if (!file) return;
    try { add(await readFile(file)); } catch (e) { showError(e.message); }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (running) return onStop();
    const typed = input.value.trim();
    if (!items.length && !typed) return showError('공고 주소나 내용을 넣으면 시작할 수 있어요');
    const a = items[0];
    const payload = a ? { text: a.text, html: a.html, title: a.title || '' }
      : URL_ONLY.test(typed) ? { url: typed } : { text: typed };
    onSend(payload, { text: typed, attachments: items.slice(), isUrl: !a && URL_ONLY.test(typed) });
    items = []; input.value = ''; showError(''); fit();
  });
  input.addEventListener('input', fit);
  input.addEventListener('keydown', (e) => {
    // 한글 조합 중 Enter 는 글자를 마저 짓는 것이라 보내지 않는다
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
  input.addEventListener('paste', (e) => {
    if (e.clipboardData.files.length) { e.preventDefault(); return addFiles(e.clipboardData.files); }
    const text = e.clipboardData.getData('text/plain');
    if (text.length > LONG_PASTE) {
      e.preventDefault();
      const first = text.trim().split('\n')[0].slice(0, 40);
      add({ kind: 'paste', name: first || '붙여넣은 공고', text, size: text.length });
    }
  });
  $('attach').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { addFiles(fileInput.files); fileInput.value = ''; });

  // 창 전체 끌어다 놓기. 자식 요소를 지날 때도 enter/leave 가 나서 깊이를 센다
  let depth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
  const setDrag = (on) => { drop.hidden = !on; };
  window.addEventListener('dragenter', (e) => { if (hasFiles(e)) { depth += 1; setDrag(true); } });
  window.addEventListener('dragleave', (e) => { if (hasFiles(e)) { depth -= 1; if (depth <= 0) { depth = 0; setDrag(false); } } });
  window.addEventListener('dragover', (e) => { if (hasFiles(e)) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; } });
  window.addEventListener('drop', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); depth = 0; setDrag(false);
    addFiles(e.dataTransfer.files);
  });
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !drop.hidden) setDrag(false); });

  return {
    add,
    focus: () => input.focus(),
    setText: (t) => { input.value = t; fit(); },
    showDrag: setDrag,
    showError,
    setRunning(on) {
      running = on;
      send.dataset.mode = on ? 'stop' : 'send';
      send.setAttribute('aria-label', on ? '멈추기' : '보내기');
      send.title = on ? '멈추기' : '';
      if (on) form.dataset.busy = ''; else delete form.dataset.busy;
      send.innerHTML = icon(on ? 'stop' : 'up', 18);
      render();
    },
  };
}
