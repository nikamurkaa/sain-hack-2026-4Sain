// Добавляет диктовку к обычному полю сообщения. Вызывается после создания DOM.
export function attachDictation(button, input, status, browser = window) {
  const Engine = browser.SpeechRecognition || browser.webkitSpeechRecognition;
  const options = { langs: ['ru-RU'], processLocally: true };
  let active;
  if (!Engine || !('processLocally' in Engine.prototype) || !Engine.available) {
    button.disabled = true;
    status.textContent = 'Локальная диктовка недоступна. Введите просьбу текстом.';
    return;
  }
  button.onclick = async () => {
    if (active) {
      active.stop();
      button.disabled = true;
      return;
    }
    button.disabled = true;
    try {
      const availability = await Engine.available(options);
      if (availability === 'downloadable' && Engine.install) {
        if (!browser.confirm('Скачать русский языковой пакет для диктовки на устройстве?')) return;
        status.textContent = 'Устанавливаем русский языковой пакет…';
        if (!await Engine.install(options)) throw new Error();
      } else if (availability !== 'available') {
        throw new Error();
      }
      const recognition = new Engine();
      recognition.lang = 'ru-RU';
      recognition.processLocally = true;
      recognition.interimResults = false;
      recognition.continuous = false;
      let received = false;
      recognition.onresult = event => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (!result.isFinal) continue;
          const text = result[0].transcript.trim();
          if (!text) continue;
          input.value = [input.value.trim(), text].filter(Boolean).join(' ');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          received = true;
        }
        if (received) status.textContent = 'Проверьте текст и нажмите «Отправить».';
      };
      recognition.onerror = event => {
        received = true;
        status.textContent = event.error === 'not-allowed'
          ? 'Доступ к микрофону закрыт. Введите просьбу или разрешите доступ в браузере.'
          : 'Не удалось распознать речь. Попробуйте ещё раз или введите текст.';
      };
      recognition.onend = () => {
        active = null;
        button.disabled = false;
        button.textContent = 'Микрофон';
        if (!received) status.textContent = 'Речь не распознана. Попробуйте ещё раз.';
      };
      recognition.start();
      active = recognition;
      button.textContent = 'Остановить';
      status.textContent = 'Слушаю…';
    } catch {
      active = null;
      status.textContent = 'Диктовка сейчас недоступна. Введите просьбу текстом.';
    } finally {
      button.disabled = false;
    }
  };
}
