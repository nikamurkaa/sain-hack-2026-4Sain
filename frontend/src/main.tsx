import { createRoot } from "react-dom/client";
import { useEffect, useMemo, useRef, useState } from "react";
import { client, ApiError } from "./api";
import { moments, periodAt, periods, titles, time } from "./model";
import type {
  Session,
  Prepared,
  Snapshot,
  Reply,
  Room,
  Catalog,
  Period,
} from "./model";
import { Hero, Icon, Devices, Plan, Settings, Detail } from "./views";
import Voice from "./Voice";
import { MobileStay, useMobile } from "./design/MobileStay";
import { DesignScreen } from "./design/Layout";
import "./style.css";

type Page =
  | "welcome"
  | "plan"
  | "room"
  | "chat"
  | "virtual"
  | "settings"
  | "voice"
  | "profile";
type Attempt = { text: string; at: string; key: string };
const pageNames = {
  welcome: "Заселение",
  plan: "Ваш план",
  room: "Мой номер",
  chat: "Диалог",
  virtual: "Виртуальное время",
  profile: "Профиль гостя",
};
const problem = (e: unknown) =>
  e instanceof ApiError
    ? e.message
    : "Не удалось получить ответ. Проверьте подключение.";
function App() {
  const [token, setToken] = useState(""),
    [input, setInput] = useState("");
  if (!token)
    return (
      <main className="entry">
        <div>
          <small>SAIN / SMART ROOM</small>
          <h1>
            Добро пожаловать
            <br />в ваш номер
          </h1>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim()) {
              setToken(input.trim());
              setInput("");
            }
          }}
        >
          <label>
            Временный токен гостя
            <input
              autoComplete="off"
              type="password"
              required
              maxLength={128}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          <button className="primary">
            Подключиться <Icon name="arrow-right" />
          </button>
        </form>
      </main>
    );
  return <Stay key={token} token={token} leave={() => setToken("")} />;
}
function Stay({ token, leave }: { token: string; leave: () => void }) {
  const mobile = useMobile();
  const controller = useMemo(() => new AbortController(), []),
    api = useMemo(() => client(token, controller.signal), [token, controller]);
  const [revision, reload] = useState(0),
    [info, setInfo] = useState<Session>(),
    [prepared, setPrepared] = useState<Prepared>(),
    [catalog, setCatalog] = useState<Catalog>({ devices: [], tracks: [] });
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [stale, setStale] = useState(false),
    [expired, setExpired] = useState(false);
  const [page, setPage] = useState<Page>("welcome"),
    [menu, setMenu] = useState(false),
    [period, setPeriod] = useState<Period>("evening"),
    [device, setDevice] = useState("climate");
  const [preview, setPreview] = useState<Snapshot | null>(null),
    [previewError, setPreviewError] = useState(""),
    [previewVersion, setPreviewVersion] = useState(0);
  const [draft, setDraft] = useState(""),
    [pending, setPending] = useState<Attempt | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const liveRevision = useRef(0),
    lock = useRef(false),
    chatLog = useRef<HTMLDivElement>(null),
    follow = useRef(true);
  const expiredError = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      setExpired(true);
      setPage("welcome");
      setPending(null);
      setDraft("");
      return true;
    }
    return false;
  };
  useEffect(() => () => controller.abort(), [controller]);
  useEffect(() => {
    let current = true;
    const initialRead = liveRevision.current;
    let timer = 0;
    setError("");
    setExpired(false);
    setInfo(undefined);
    setPrepared(undefined);
    setSnapshot(null);
    setStale(false);
    (async () => {
      const [session, view, cat] = await Promise.all([
        api<Session>("session"),
        api<Prepared>("prepared"),
        api<Catalog>("catalog"),
      ]);
      if (!current) return;
      setInfo(session);
      setPrepared(view);
      setCatalog(cat);
      setSnapshot(view.last_confirmed);
      setStale(true);
      setPeriod(periodAt(session.at));
      timer = window.setTimeout(() => {
        setExpired(true);
        setPage("welcome");
        setPending(null);
        setDraft("");
      }, session.expires_in * 1000);
      if (session.actions.includes("state"))
        try {
          const live = await api<Snapshot>("state");
          if (current && initialRead === liveRevision.current) {
            setSnapshot(live);
            setStale(false);
          }
        } catch (e) {
          if (current) expiredError(e);
        }
    })().catch((e) => {
      if (current && !expiredError(e)) setError(problem(e));
    });
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [api, revision]);
  const steps = prepared?.scenario.steps ?? [];
  const points = useMemo(
    () =>
      info && prepared
        ? moments(
            String(prepared.guest.stay.check_in_at ?? info.at),
            info.until,
            prepared.scenario.steps,
          )
        : {},
    [info, prepared],
  );
  useEffect(() => {
    if (page !== "virtual" || !points[period] || expired) return;
    let current = true;
    setPreview(null);
    setPreviewError("");
    const reading = new AbortController();
    api<Snapshot>("state?" + new URLSearchParams({ at: points[period]! }), {
      signal: reading.signal,
    })
      .then((v) => {
        if (current) setPreview(v);
      })
      .catch((e) => {
        if (current) {
          expiredError(e);
          setPreviewError(problem(e));
        }
      });
    return () => {
      current = false;
      reading.abort();
    };
  }, [api, page, period, points, expired, previewVersion]);
  useEffect(() => {
    const el = chatLog.current;
    if (el && follow.current) el.scrollTop = el.scrollHeight;
  }, [pending, busy, info?.history.length, error, page]);
  const [navigationId] = useState(() => crypto.randomUUID());
  useEffect(() => {
    // History entries contain only view names and a per-mount nonce.
    history.replaceState({ navigationId, view: "welcome" }, "");
    const restore = (event: PopStateEvent) => {
      const state = event.state;
      const view =
        state?.navigationId === navigationId ? state.view : "welcome";
      const known = [
        "welcome",
        "room",
        "plan",
        "chat",
        "virtual",
        "profile",
        "settings",
        "voice",
      ];
      if (view === "settings" && typeof state.device === "string")
        setDevice(state.device);
      setPage(known.includes(view) ? view : "welcome");
      setMenu(false);
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, [navigationId]);
  function go(next: Page, selectedDevice = device) {
    if (next !== page)
      history.pushState(
        { navigationId, view: next, device: selectedDevice },
        "",
      );
    setMenu(false);
    setPage(next);
    window.scrollTo(0, 0);
  }
  const allowed =
    !!info &&
    info.source === "dev" &&
    !info.read_only &&
    info.can_send_requests &&
    info.actions.includes("message") &&
    !expired;
  async function send(text: string, retry?: Attempt) {
    if (
      !allowed ||
      !info ||
      !text.trim() ||
      lock.current ||
      (!retry && pending)
    )
      return;
    lock.current = true;
    liveRevision.current++;
    setBusy(true);
    follow.current = true;
    setError("");
    go("chat");
    const attempt = retry ?? {
      key: crypto.randomUUID(),
      at: info.at,
      text: text.trim(),
    };
    setPending(attempt);
    try {
      const result = await api<{ reply: Reply; state: Room }>("messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": attempt.key,
        },
        body: JSON.stringify({ at: attempt.at, text: attempt.text }),
      });
      if (
        !result.state ||
        !["done", "refused"].includes(result.reply?.response_class)
      )
        throw Error("response");
      setSnapshot({ at: attempt.at, state: result.state });
      setStale(false);
      setDraft("");
      setPending(null);
      setInfo(
        (prev) =>
          prev && {
            ...prev,
            at: attempt.at,
            history: [
              ...prev.history,
              {
                at: attempt.at,
                utterances: [attempt.text],
                reply: result.reply,
              },
            ],
          },
      );
    } catch (e) {
      if (expiredError(e)) return;
      setError(problem(e));
      setDraft(attempt.text);
      setStale(true);
      try {
        const recovery = { signal: AbortSignal.timeout(4000) };
        const updated = await api<Session>("session", recovery);
        // Recover authoritative history when the response to a command was lost.
        setInfo(updated);
        const delivered = updated.history.length > info.history.length &&
          updated.history.at(-1)?.utterances.join(" ") === attempt.text;
        if (delivered) {
          setPending(null);
          setError("");
          setDraft("");
        }
        if (updated.actions.includes("state")) {
          const live = await api<Snapshot>("state", recovery);
          setSnapshot(live);
          setStale(false);
        }
      } catch (err) {
        expiredError(err);
      }
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  if (mobile && expired)
    return (
      <DesignScreen
        screen={29}
        bind={(w) => {
          if (w.name === "Переподключиться")
            return { onClick: () => reload((n) => n + 1) };
          if (w.name === "Отменить")
            return { label: "Подключить новый сеанс", onClick: leave };
          if (["menu-02", "notification-01", "arrow-back"].includes(w.name))
            return { onClick: leave, label: "К подключению" };
          if (w.texts[0]?.font === "Inter")
            return { text: () => (info ? time(info.at) : "—") };
          return;
        }}
      />
    );
  if (mobile && !error && (!info || !prepared))
    return (
      <DesignScreen
        screen={24}
        bind={(w) => {
          if (w.name === "Алина,") return { text: () => "Ваш номер" };
          if (w.box[1] < 30 && w.texts.length) return { text: () => "—" };
          if (w.name === "Номер 413") return { role: "status" };
          if (["menu-02", "notification-01", "arrow-back"].includes(w.name))
            return { onClick: leave, label: "К подключению" };
        }}
      />
    );
  if (expired)
    return (
      <main className="entry ended">
        <h1>Сеанс завершён</h1>
        <p>Для продолжения нужен действующий доступ.</p>
        <button className="primary" onClick={() => reload((n) => n + 1)}>
          Переподключиться
        </button>
        <button onClick={leave}>Подключить новый сеанс</button>
      </main>
    );
  if (!info || !prepared)
    return (
      <main className="shell loading">
        <h1>Ваш номер</h1>
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button onClick={() => reload((n) => n + 1)}>Повторить</button>
            <button onClick={leave}>Другой сеанс</button>
          </>
        ) : (
          <>
            <div className="skeleton hero" />
            <div className="skeleton-grid">
              {[0, 1, 2, 3].map((i) => (
                <div className="skeleton" key={i} />
              ))}
            </div>
            <div className="skeleton" />
            <p role="status">Загружаем комнату…</p>
          </>
        )}
      </main>
    );
  const badge =
    (info.rehearsal ? "Репетиция · " : "") +
    (info.source === "final"
      ? "Финальный гость · просмотр"
      : "Демонстрационный номер" + (allowed ? " · управление" : " · просмотр"));
  const mode = titles[periodAt(info.at)],
    liveNote = stale
      ? snapshot
        ? "Последнее подтверждение на " + time(snapshot.at)
        : "Живое состояние недоступно"
      : "";
  const selectPeriod = (v: Period) => {
    if (v !== period) {
      setPreview(null);
      setPeriod(v);
    }
  };
  const tabs = (onlyAvailable: boolean) => (
    <div className="periods" aria-label="Период">
      {periods.map((p) => (
        <button
          key={p}
          aria-pressed={p === period}
          disabled={onlyAvailable && !points[p]}
          onClick={() => selectPeriod(p)}
        >
          {titles[p]}
        </button>
      ))}
    </div>
  );
  const openSetting =
    allowed && !pending && !busy
      ? (id: string) => {
          setDevice(id);
          go("settings", id);
        }
      : undefined;
  const navigationMenu = menu && (
    <nav
      aria-label="Навигация по номеру"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setMenu(false);
          document
            .querySelector<HTMLButtonElement>('button[aria-label="Меню"]')
            ?.focus();
        }
      }}
    >
      {Object.entries(pageNames).map(([key, label]) => (
        <button
          key={key}
          autoFocus={key === "welcome"}
          onClick={() => go(key as Page)}
        >
          {label}
        </button>
      ))}
      <button
        disabled={busy}
        onClick={async () => {
          try {
            await api<void>("session", { method: "DELETE" });
            leave();
          } catch (e) {
            if (expiredError(e)) leave();
            else {
              setError(problem(e));
              go("chat");
            }
          }
        }}
      >
        Сменить сеанс
      </button>
    </nav>
  );
  const nav = {
    back: () =>
      go(
        page === "welcome"
          ? "profile"
          : page === "room"
            ? "plan"
            : page === "voice"
              ? "chat"
              : page === "plan"
                ? "welcome"
                : "room",
      ),
    menu: () => setMenu(!menu),
    profile: () => go("profile"),
  };
  const design = { nav, overlay: navigationMenu, badge, clock: time(info.at) };
  if (mobile && ["room", "welcome", "plan", "chat", "virtual"].includes(page))
    return (
      <MobileStay
        page={page as "room" | "welcome" | "plan" | "chat" | "virtual"}
        info={info}
        prepared={prepared}
        catalog={catalog}
        snapshot={snapshot}
        preview={preview}
        period={period}
        points={points}
        select={selectPeriod}
        go={go}
        openSetting={openSetting}
        navigation={nav}
        overlay={navigationMenu}
        badge={badge}
        liveNote={liveNote}
        previewError={previewError}
        retryPreview={() => setPreviewVersion((v) => v + 1)}
        allowed={allowed}
        draft={draft}
        setDraft={setDraft}
        pending={pending}
        busy={busy}
        error={error}
        send={send}
        retry={() => {
          if (pending) void send(pending.text, pending);
        }}
        dismiss={() => {
          setError("");
          setPending(null);
          setDraft("");
        }}
      />
    );
  const controls = (
    <Devices room={snapshot?.state} catalog={catalog} open={openSetting} />
  );
  const chat = (
    <section className="chat">
      <h2>Диалог</h2>
      <div
        className="log"
        role="log"
        ref={chatLog}
        onScroll={(e) => {
          const el = e.currentTarget;
          follow.current =
            el.scrollHeight - el.scrollTop - el.clientHeight < 50;
        }}
      >
        {!info.history.length && !pending && (
          <div className="suggest">
            <img
              className="ring"
              alt=""
              src="/media/decor/assistant-ring.svg"
            />
            {allowed && (
              <button
                disabled={!allowed}
                onClick={() => send("Сделай попрохладнее")}
              >
                Сделай попрохладнее
              </button>
            )}
          </div>
        )}
        {info.history.map((h, i) => (
          <div className="exchange" key={i}>
            <p className="request">{h.utterances.join(" ")}</p>
            <div className="answer">
              <img alt="" src="/media/decor/assistant-ring.svg" />
              <p className={"reply " + h.reply.response_class}>
                {h.reply.text}
              </p>
            </div>
          </div>
        ))}
        {pending && (
          <div className="exchange">
            <p className="request">{pending.text}</p>
            {busy && !error && (
              <p className="reply" role="status">
                Выполняю просьбу…
              </p>
            )}
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
            {pending && (
              <>
                <button
                  disabled={busy || !allowed}
                  onClick={() => send(pending.text, pending)}
                >
                  Повторить
                </button>
                <button
                  disabled={busy}
                  onClick={() => {
                    setError("");
                    setPending(null);
                    setDraft("");
                  }}
                >
                  Закрыть
                </button>
              </>
            )}
          </div>
        )}
      </div>
      {allowed ? (
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <input
            aria-label="Просьба"
            maxLength={2000}
            placeholder="Попросить номер…"
            value={draft}
            disabled={!!pending}
            onChange={(e) => setDraft(e.target.value)}
          />
          <button
            type="button"
            aria-label="Голосовой ввод"
            disabled={!!pending || !info.actions.includes("transcription")}
            onClick={() => go("voice")}
          >
            <Icon name="microphone" />
          </button>
          <button
            aria-label="Отправить просьбу"
            disabled={!!pending || !draft.trim()}
          >
            <Icon name="send" />
          </button>
        </form>
      ) : (
        <p>Сеанс доступен только для просмотра.</p>
      )}
    </section>
  );
  return (
    <main
      data-period={
        page === "plan" || page === "virtual" ? period : periodAt(info.at)
      }
      className={"shell page-" + page + (error ? " has-error" : "")}
    >
      {!(
        mobile &&
        (page === "voice" ||
          (page === "settings" &&
            ["climate", "alarm", "sound"].includes(device)))
      ) && (
        <header>
          <button
            aria-label="Назад"
            onClick={() =>
              go(
                page === "welcome"
                  ? "profile"
                  : page === "room"
                    ? "plan"
                    : page === "voice"
                      ? "chat"
                      : page === "plan"
                        ? "welcome"
                        : "room",
              )
            }
          >
            <Icon name="arrow-back" />
          </button>
          <small>{badge}</small>
          <button
            aria-label="Меню"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Icon name="more" />
          </button>
        </header>
      )}
      {!(
        mobile &&
        (page === "voice" ||
          (page === "settings" &&
            ["climate", "alarm", "sound"].includes(device)))
      ) && navigationMenu}
      {page === "welcome" && (
        <section className="welcome">
          <h1>
            Добро пожаловать
            <br />в SAIN Smart Room
          </h1>
          <p>Ваш номер подготовлен к заселению</p>
          <Hero
            period={period}
            title="Номер готов"
            detail="По вашему сценарию"
          />
          <Devices
            room={snapshot?.state}
            catalog={catalog}
            ids={["climate", "light", "curtains"]}
            list
          />
          {liveNote && <p>{liveNote}</p>}
          <button className="primary bottom" onClick={() => go("plan")}>
            Заселиться <Icon name="arrow-right" />
          </button>
        </section>
      )}
      {page === "profile" && (
        <section>
          <h1>Профиль гостя</h1>
          <p>Доступные данные помогают подготовить номер к вашему приезду.</p>
          <Detail data={prepared.guest.profile} catalog={catalog} />
          <h2>Предпочтения</h2>
          <Detail data={prepared.guest.preferences} catalog={catalog} />
          <details className="technical-details">
            <summary>Технические сведения о проживании</summary>
            <small>Гость: {prepared.guest.user_id}</small>
            <small>Заезд: {info.stay_id}</small>
          </details>
        </section>
      )}
      {page === "plan" && (
        <section>
          <h1>
            Ваш план
            <br />
            на{" "}
            {
              { morning: "утро", day: "день", evening: "вечер", night: "ночь" }[
                period
              ]
            }
          </h1>
          {tabs(false)}
          <Plan steps={steps} period={period} />
          <button className="primary bottom" onClick={() => go("room")}>
            В номер <Icon name="arrow-right" />
          </button>
        </section>
      )}
      {(page === "room" || page === "chat") && (
        <div className="dashboard">
          <section>
            <h1>{page === "room" ? "Мой номер" : "Ваш номер"}</h1>
            <small>{info.source === "final" ? "Финальный гость · просмотр" : "Демонстрационный номер"}</small>
            {page === "room" && (
              <Hero
                period={periodAt(info.at)}
                title={mode}
                detail={"Время номера · " + time(info.at)}
              />
            )}
            {controls}
            {liveNote && <p role="status">{liveNote}</p>}
            {page === "room" && (
              <button className="wave" onClick={() => go("virtual")}>
                <Icon name="sunrise" />
                Виртуальное время <Icon name="chevron" />
              </button>
            )}
          </section>
          {page === "chat" ? (
            chat
          ) : (
            <>
              <button
                className="primary mobile-chat"
                onClick={() => go("chat")}
              >
                Диалог с номером <Icon name="arrow-right" />
              </button>
              <div className="desktop-chat">{chat}</div>
            </>
          )}
          <aside>
            <h2>План проживания</h2>
            {tabs(false)}
            <Plan steps={steps} period={period} />
          </aside>
        </div>
      )}
      {page === "virtual" && (
        <section>
          <h1>Мой номер</h1>
          <Hero
            period={period}
            title={titles[period]}
            detail="Виртуальное время · просмотр"
          />
          {tabs(true)}
          {previewError ? (
            <div role="alert">
              {previewError}
              <p>Персональный план доступен по расписанию.</p>
              <button onClick={() => go("plan")}>Посмотреть план</button>
              <button onClick={() => setPreviewVersion((v) => v + 1)}>
                Повторить чтение
              </button>
            </div>
          ) : points[period] ? (
            <>
              <small>
                {preview ? "Виртуальный момент: " + preview.at.slice(0, 16).replace("T", " · ") : "Загружаем состояние симулятора…"}
              </small>
              <Devices room={preview?.state} catalog={catalog} list />
            </>
          ) : (
            <p>Период вне проживания.</p>
          )}
        </section>
      )}
      {page === "settings" && snapshot && (
        <Settings
          design={mobile ? design : undefined}
          key={device}
          id={device}
          values={snapshot.state[device] ?? {}}
          catalog={catalog}
          submit={send}
        />
      )}
      {page === "voice" && allowed && (
        <Voice
          design={mobile ? design : undefined}
          close={() => go("chat")}
          send={send}
          transcribe={async (blob, signal) => {
            try {
              return (
                await api<{ text: string }>("transcriptions", {
                  method: "POST",
                  body: blob,
                  headers: { "Content-Type": blob.type },
                  signal,
                })
              ).text;
            } catch (e) {
              expiredError(e);
              throw Error(problem(e));
            }
          }}
        />
      )}
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
