import { useEffect, useRef, useState } from "react";

/** A reply must exist on the authenticated server before it can be spoken.
 * Playing cached audio NEVER retries /messages or a device command.
 */
let activeAudio: HTMLAudioElement | null = null;

export function SpeechReply({ token, replyIndex }: { token: string; replyIndex: number }) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "playing" | "error">("idle");
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState("");
  const media = useRef<HTMLAudioElement | null>(null);
  const url = useRef<string | null>(null);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    // A React component can be reused for another reply or guest without
    // unmounting. Never play a previous session's cached response.
    setStatus("idle");
    setError("");
    return () => {
      pending.current?.abort();
      pending.current = null;
      if (media.current) {
        media.current.pause();
        if (activeAudio === media.current) activeAudio = null;
        media.current.onended = null;
        media.current.onpause = null;
        media.current.src = "";
        media.current = null;
      }
      if (url.current) URL.revokeObjectURL(url.current);
      url.current = null;
    };
  }, [token, replyIndex]);

  function stop() {
    media.current?.pause();
    if (media.current) media.current.currentTime = 0;
    if (activeAudio === media.current) activeAudio = null;
    if (media.current) setStatus("ready");
  }

  async function play() {
    if (muted) return;
    if (activeAudio && activeAudio !== media.current) activeAudio.pause();
    try {
      if (!media.current) {
        const abort = new AbortController();
        pending.current = abort;
        setStatus("loading");
        setError("");
        const response = await fetch("/api/v1/speech", {
          method: "POST",
          headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
          body: JSON.stringify({ reply_index: replyIndex }),
          signal: AbortSignal.any([abort.signal, AbortSignal.timeout(90000)]),
          cache: "no-store",
          redirect: "error",
        });
        if (!response.ok || !response.headers.get("Content-Type")?.startsWith("audio/mpeg")) {
          throw new Error("TTS is unavailable");
        }
        const blob = await response.blob();
        if (!blob.size || blob.size > 5000000) throw new Error("Invalid audio");
        url.current = URL.createObjectURL(blob);
        const audio = new Audio(url.current);
        audio.preload = "auto";
        audio.onended = () => { setStatus("ready"); if (activeAudio === audio) activeAudio = null; };
        audio.onpause = () => { if (audio.currentTime < audio.duration) setStatus("ready"); };
        media.current = audio;
        pending.current = null;
      }
      const audio = media.current;
      if (!audio) throw new Error("Audio not ready");
      audio.currentTime = 0;
      audio.muted = muted;
      activeAudio = audio;
      await audio.play();
      setStatus("playing");
    } catch {
      if (!pending.current?.signal.aborted) {
        // The visible text reply stays on screen even if audio fails.
        setStatus(media.current ? "ready" : "error");
        setError("Не удалось воспроизвести голос. Текст ответа доступен.");
      }
    }
  }
  return (
    <div className="speech-reply" aria-label="Озвучивание ответа">
      <button type="button" disabled={status === "loading" || muted}
        onClick={() => void play()}>
        {status === "loading" ? "Готовим голос…" : media.current ? "Повторить ответ" : "Озвучить ответ"}
      </button>
      {media.current && (
        <button type="button" onClick={stop} disabled={status !== "playing"}>Остановить</button>
      )}
      <button type="button" aria-pressed={muted} onClick={() => {
        stop();
        setMuted((m) => !m);
      }}>{muted ? "Включить звук" : "Выключить звук"}</button>
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
