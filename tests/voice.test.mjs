import {test} from 'node:test';
import assert from 'node:assert/strict';
import {attachDictation} from '../frontend/voice/dictation.mjs';

function setup(browser) {
  const button = {}, input = new EventTarget(), status = {};
  input.value = '';
  attachDictation(button, input, status, browser);
  return {button, input, status};
}
test('Без распознавания остаётся текстовый ввод', () => {
  const {button, input} = setup({});
  assert.equal(button.disabled, true);
  assert.equal(input.value, '');
});
test('Русская диктовка заполняет поле и обрабатывает отказ микрофона', async () => {
  let session;
  class Engine {
    get processLocally() { return true; }
    set processLocally(value) { assert.equal(value, true); }
    static async available() { return 'available'; }
    start() { session = this; }
  }
  const {button, input, status} = setup({SpeechRecognition: Engine});
  await button.onclick();
  assert.equal(session.lang, 'ru-RU');
  session.onresult({resultIndex: 0, results: [{isFinal:true, 0:{transcript:'Сделай попрохладнее'}}]});
  assert.equal(input.value, 'Сделай попрохладнее');
  session.onend();
  await button.onclick();
  session.onerror({error:'not-allowed'});
  session.onend();
  assert.match(status.textContent, /Доступ к микрофону закрыт/);
  assert.equal(button.disabled, false);
});
