import { attachDictation } from './dictation.mjs';
const el = id => document.getElementById(id);
let token, at, previous;
async function request(path, options = {}) {
  const res = await fetch('/api/v1/' + path, {
    ...options, headers: {Authorization: 'Bearer ' + token, ...options.headers}
  });
  if (res.status === 401) {
    el('connect').hidden = false;
    el('chat').hidden = true;
    throw new Error('Откройте новый сеанс.');
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'Проверьте параметры запроса.');
  return data;
}
function showState(state) {
  el('climate').textContent = 'Установленная температура — ' + state.climate.temperature_c + ' °C';
}
el('connect').onsubmit = async event => {
  event.preventDefault();
  token = el('token').value.trim();
  try {
    const result = await request('state');
    at = result.at;
    previous = null;
    showState(result.state);
    el('token').value = '';
    el('message').value = '';
    el('status').textContent = '';
    el('connect').hidden = true;
    el('chat').hidden = false;
  } catch (e) { el('status').textContent = e.message; }
};
attachDictation(el('mic'), el('message'), el('speech'));
el('chat').onsubmit = async event => {
  event.preventDefault();
  const text = el('message').value.trim();
  if (!text || el('send').disabled) return;
  const body = JSON.stringify({text, at});
  if (previous?.body !== body) previous = {body, key: crypto.randomUUID()};
  el('send').disabled = true;
  el('status').textContent = 'Проверяем состояние номера…';
  try {
    const result = await request('messages', {method:'POST', body,
      headers:{'Content-Type':'application/json','Idempotency-Key':previous.key}});
    previous = null;
    showState(result.state);
    el('status').textContent = result.reply.text;
    if (el('message').value.trim() === text) el('message').value = '';
  } catch (e) {
    el('status').textContent = e.message;
    if (!el('chat').hidden) {
      try { showState((await request('state')).state); } catch { /* Сохраняем исходную ошибку. */ }
    }
  } finally { el('send').disabled = false; }
};
