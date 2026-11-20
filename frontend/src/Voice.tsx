import { useEffect, useRef, useState } from "react";
import { DesignScreen } from "./design/Layout";
import { chrome } from "./design/MobileStay";
import type { DesignChrome } from "./design/MobileStay";
import { Icon } from "./views";
export default function Voice({
  design,
  transcribe,
  close,
  send,
}: {
  design?: DesignChrome;
  transcribe: (blob: Blob, signal: AbortSignal) => Promise<string>;
  close: () => void;
  send: (v: string) => void;
}) {
  const [stage, setStage] = useState<
    "start" | "record" | "wait" | "review" | "error"
  >("start");
  const [value, setValue] = useState(""),
    [error, setError] = useState("");
  const active = useRef<MediaRecorder | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let stream: MediaStream | undefined;
    let timer = 0;
    const release = () => {
      clearTimeout(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
    const fail = (msg: string) => {
      release();
      if (!controller.signal.aborted) {
        setError(msg);
        setStage("error");
      }
    };
    async function record() {
      if (
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined"
      )
        throw Error(
          "Запись недоступна. Используйте HTTPS или localhost и разрешите микрофон.",
        );
      const mime = [
        "audio/webm;codecs=opus",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      if (!mime) throw Error("Браузер не поддерживает формат записи.");
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (controller.signal.aborted) {
        release();
        return;
      }
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      active.current = recorder;
      const parts: Blob[] = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size) parts.push(e.data);
      };
      recorder.onerror = () => fail("Ошибка записи микрофона.");
      recorder.onstop = async () => {
        release();
        if (controller.signal.aborted) return;
        const blob = new Blob(parts, { type: mime });
        if (!blob.size || blob.size > 5000000) {
          fail("Нужна непустая запись размером до 5 МБ.");
          return;
        }
        setStage("wait");
        try {
          const text = await transcribe(blob, controller.signal);
          if (!controller.signal.aborted) {
            setValue(text);
            setStage("review");
          }
        } catch (e) {
          fail(e instanceof Error ? e.message : "Ошибка распознавания");
        }
      };
      recorder.start();
      setStage("record");
      timer = window.setTimeout(() => {
        if (recorder.state === "recording") recorder.stop();
      }, 30000);
    }
    record().catch((e) =>
      fail(
        e.name === "NotAllowedError"
          ? "Разрешите доступ к микрофону или введите просьбу текстом."
          : e.message,
      ),
    );
    return () => {
      controller.abort();
      if (active.current?.state === "recording") active.current.stop();
      release();
    };
  }, []);
  if (design)
    return (
      <DesignScreen
        screen={stage === "review" ? 14 : stage === "wait" ? 13 : 12}
        bind={(w) => {
          const common = chrome(w, design.nav, design.clock);
          if (common) return common;
          if (w.name === "Отменить") return { onClick: close };
          if (w.name === "Отправить")
            return {
              onClick: () => send(value.trim()),
              disabled: !value.trim(),
            };
          if (w.name === "Запрос")
            return {
              content: (
                <textarea
                  aria-label="Распознанный текст"
                  className="transcript-edit"
                  maxLength={2000}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                />
              ),
            };
          if (w.name === "Алина,")
            return {
              role: "heading",
              text: () =>
                stage === "review"
                  ? "Вы сказали:"
                  : stage === "wait"
                    ? "Распознаём вашу команду"
                    : "Скажите,\nчто изменить",
            };
          if (w.name === "Попросить номер..." && stage !== "wait")
            return {
              text: () => error || "Например: «Сделай попрохладнее»",
              role: error ? "alert" : undefined,
            };
          if (w.name.startsWith("Group "))
            return {
              className: "record",
              label: "Завершить запись",
              onClick: () => {
                if (active.current?.state === "recording")
                  active.current.stop();
              },
              disabled: stage !== "record",
            };
        }}
      >
        <small className="mode-caption">{design.badge}</small>
        {design.overlay}
      </DesignScreen>
    );
  return (
    <section className="voice">
      <h1>
        {stage === "review"
          ? "Вы сказали"
          : stage === "wait"
            ? "Распознаём вашу команду"
            : "Скажите, что изменить"}
      </h1>
      {stage === "record" && <p>Например, «Сделай попрохладнее»</p>}
      {stage === "review" ? (
        <textarea
          aria-label="Распознанный текст"
          maxLength={2000}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : stage === "wait" ? (
        <img
          className="ring"
          src="/media/decor/assistant-ring.svg"
          alt="Распознаём"
        />
      ) : stage === "record" ? (
        <button
          className="record"
          aria-label="Завершить запись"
          onClick={() => {
            if (active.current?.state === "recording") active.current.stop();
          }}
        >
          <Icon name="microphone" />
        </button>
      ) : (
        <p role="status">{error || "Подключаем микрофон…"}</p>
      )}
      <footer>
        <button onClick={close}>Отменить</button>
        {stage === "record" && (
          <button
            onClick={() => {
              if (active.current?.state === "recording") active.current.stop();
            }}
          >
            Завершить запись
          </button>
        )}
        {stage === "review" && (
          <button
            className="primary"
            disabled={!value.trim()}
            onClick={() => send(value.trim())}
          >
            Отправить
          </button>
        )}
      </footer>
    </section>
  );
}
