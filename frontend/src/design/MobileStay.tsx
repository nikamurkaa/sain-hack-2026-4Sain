import { useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import {
  describe,
  deviceNames,
  periodAt,
  periods,
  time,
  titles,
} from "../model";
import type {
  Catalog,
  Period,
  Prepared,
  Room,
  Session,
  Snapshot,
} from "../model";
import { Plan } from "../views";
import { DesignScreen, rect } from "./Layout";
import type { Binding, Widget } from "./Layout";

const media = matchMedia("(max-width: 649px)");
function subscribe(listener: () => void) {
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
export function useMobile() {
  return useSyncExternalStore(subscribe, () => media.matches);
}
export type Navigation = {
  back: () => void;
  menu: () => void;
  profile: () => void;
};
export function chrome(
  widget: Widget,
  nav: Navigation,
  clock?: string,
): Binding | undefined {
  if (widget.name === "menu-02") return { label: "Меню", onClick: nav.menu };
  if (widget.name === "arrow-back")
    return { label: "Назад", onClick: nav.back };
  if (widget.name === "notification-01")
    return { label: "Сведения о сеансе", onClick: nav.menu };
  if (widget.name.startsWith("Ellipse 15188"))
    return { label: "Профиль гостя", onClick: nav.profile };
  if (widget.texts[0]?.font === "Inter" && widget.box[1] < 30)
    return { text: () => clock ?? "—" };
}
export function Hit({
  label,
  onClick,
  box,
  disabled,
}: {
  label: string;
  onClick: () => void;
  box: number[];
  disabled?: boolean;
}) {
  return (
    <button
      className="design-hit"
      aria-label={label}
      style={rect(box)}
      onClick={onClick}
      disabled={disabled}
    />
  );
}
type Props = {
  page: "room" | "chat" | "virtual" | "welcome" | "plan";
  info: Session;
  prepared: Prepared;
  catalog: Catalog;
  snapshot: Snapshot | null;
  preview: Snapshot | null;
  period: Period;
  points: Partial<Record<Period, string>>;
  select: (p: Period) => void;
  go: (p: "room" | "chat" | "plan" | "virtual" | "profile" | "voice") => void;
  openSetting?: (id: string) => void;
  navigation: Navigation;
  overlay: ReactNode;
  badge: string;
  liveNote: string;
  previewError: string;
  retryPreview: () => void;
  allowed: boolean;
  draft: string;
  setDraft: (s: string) => void;
  pending: { text: string } | null;
  busy: boolean;
  error: string;
  send: (text: string) => void;
  retry: () => void;
  dismiss: () => void;
};
const periodIndex = (p: Period) => periods.indexOf(p);
const fixed = (value: string): Binding => ({ text: () => value });
const deviceLabels = new Map(
  Object.entries(deviceNames).map(([id, name]) => [name, id]),
);
export function deviceId(w: Widget) {
  if (!w.controls?.length && !deviceLabels.has(w.name)) return;
  return w.texts.map((t) => deviceLabels.get(t.value)).find(Boolean);
}
export function deviceLevel(id: string, room: Room | undefined) {
  if (!room?.[id]) return null;
  const value = room[id];
  switch (id) {
    case "climate":
      return (Number(value.temperature_c) - 16) / 10;
    case "light":
      return Number(value.brightness) / 100;
    case "sound":
      return Number(value.volume) / 100;
    case "curtains":
      return Number(value.position) > 0 ? 1 : 0;
    case "dnd":
      return value.enabled ? 1 : 0;
    default:
      return null;
  }
}
export function MobileStay(p: Props) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const room = p.snapshot?.state,
    mode = periodIndex(periodAt(p.info.at));
  const last = p.info.history.at(-1);
  const screen =
    p.page === "welcome"
      ? 11
      : p.page === "plan"
        ? 1 + periodIndex(p.period) * 2
        : p.page === "room"
          ? 2 + mode * 2
          : p.page === "virtual"
            ? 17 + periodIndex(p.period)
            : p.error
              ? p.info.history.length
                ? 28
                : 16
              : p.pending
                ? 25
                : last?.reply.response_class === "refused"
                  ? p.info.history.length === 1
                    ? 15
                    : 27
                  : last
                    ? p.info.history.length === 1
                      ? 10
                      : 26
                    : 9;
  const displayName = p.prepared.guest.profile.display_name;
  const guest =
    typeof displayName === "string" && displayName.trim()
      ? displayName.trim().slice(0, 20) +
        (displayName.trim().length > 20 ? "…" : "") +
        ",\n"
      : "";
  const status = p.info.source === "final" ? "Финальный номер" : "Демо-номер";
  const selectPeriod = (availability: boolean) => (
    <div className="design-tabs">
      {periods.map((k) => (
        <button
          key={k}
          aria-pressed={p.period === k}
          disabled={availability && !p.points[k]}
          onClick={() => p.select(k)}
        >
          {titles[k]}
        </button>
      ))}
    </div>
  );
  const history = (
    <dialog
      className="history-panel"
      aria-label="История диалога"
      ref={(node) => {
        if (node && !node.open) node.showModal();
      }}
      onCancel={() => setHistoryOpen(false)}
    >
      <button onClick={() => setHistoryOpen(false)}>Закрыть историю</button>
      <div role="log">
        {p.info.history.map((h, i) => (
          <article key={i} className="exchange">
            <p>{h.utterances.join(" ")}</p>
            <p>{h.reply.text}</p>
          </article>
        ))}
      </div>
    </dialog>
  );
  function bind(w: Widget): Binding | undefined {
    const common = chrome(w, p.navigation, time(p.info.at));
    if (common) return common;
    const name = w.name,
      value = w.texts[0]?.value ?? "";
    if (name === "Алина,") {
      if (p.page === "virtual") return { role: "heading" };
      const title =
        p.page === "plan"
          ? "Ваш план на " +
            { morning: "утро", day: "день", evening: "вечер", night: "ночь" }[
              p.period
            ]
          : p.page === "welcome"
            ? "Добро пожаловать\nв SAIN Smart Room"
            : "Ваш номер";
      return {
        ...fixed(
          guest + (guest ? title[0].toLowerCase() + title.slice(1) : title),
        ),
        role: "heading",
      };
    }
    if (name.startsWith("Номер 412")) return fixed(status);
    if (name === "Заселиться") return { onClick: () => p.go("plan") };
    if (name === "В номер") return { onClick: () => p.go("room") };
    if (p.page === "plan") {
      if (name === "Карточка режима")
        return {
          text: (s, i) =>
            i === 0 ? s : time(p.info.at) + " · " + time(p.info.until),
        };
      if (w.box[1] > 320 && w.box[1] < 700) return { hidden: true };
    }
    if (name === "Slider" && p.page === "room")
      return {
        level: deviceLevel("light", room),
        className: "independent-meter",
      };
    const id = deviceId(w);
    if (id && p.page !== "virtual") {
      return {
        className: "device",
        label: deviceNames[id],
        role: p.openSetting ? undefined : "group",
        onClick: p.openSetting ? () => p.openSetting!(id) : undefined,
        text: (s) =>
          s === deviceNames[id] ? s : describe(id, room?.[id], p.catalog),
        level: deviceLevel(id, room),
      };
    }
    if (p.page === "welcome" && name.startsWith("Timeline Card")) {
      const values = ["climate", "light", "curtains"];
      return {
        text: (s, i) =>
          i < 3 ? describe(values[i], room?.[values[i]], p.catalog) : s,
      };
    }
    if (p.page === "room" && name.startsWith("Для "))
      return { label: "Диалог с номером", onClick: () => p.go("chat") };
    if (p.page === "room" && w.texts.some((t) => t.value === "Уже настроен"))
      return {
        className: "hero-card",
        text: (s, i) =>
          i === 0 ? s : p.liveNote || (room ? s : "Загружаем состояние…"),
      };
    if (p.page === "virtual") {
      if (name.startsWith("утро-ночь")) return { content: selectPeriod(true) };
      if (name.startsWith("Timeline Card")) {
        if (p.previewError || !p.points[p.period]) return { hidden: true };
        const state = p.preview?.state;
        const ids = ["climate", "light", "sound", "alarm", "curtains"];
        return {
          className: "rows",
          level: deviceLevel("curtains", state),
          text: (s, i) =>
            w.texts[i].font === "Unbounded"
              ? describe(
                  ids[Math.min(4, Math.floor(w.texts[i].box[1] / 50))],
                  state?.[ids[Math.min(4, Math.floor(w.texts[i].box[1] / 50))]],
                  p.catalog,
                )
              : deviceLabels.has(s)
                ? s
                : "",
        };
      }
      if (value === titles[p.period])
        return { text: (s, i) => (i === 2 ? "(виртуальное время)" : s) };
    }
    if (p.page !== "chat") return;
    if (name === "Сделай попрохладнее")
      return {
        hidden: !p.allowed,
        onClick: () => p.send("Сделай попрохладнее"),
      };
    if (name === "Запрос")
      return {
        className: "latest-request",
        text: () => p.pending?.text ?? last?.utterances.join(" ") ?? "",
      };
    if (name === "Ответ") {
      if (p.error)
        return {
          role: "alert",
          className: "delivery-error",
          text: (s, i) => (i === 0 ? p.error : s),
          children: (
            <Hit
              label="Повторить"
              box={[w.texts[1].box[0] - 28, w.texts[1].box[1] - 15, 165, 49]}
              onClick={p.retry}
              disabled={p.busy}
            />
          ),
        };
      return {
        onClick: !p.busy && last ? () => setHistoryOpen(true) : undefined,
        label: !p.busy && last ? "Открыть полный ответ" : undefined,
        role: p.busy ? "status" : undefined,
        className: "reply " + (last?.reply.response_class ?? ""),
        text: () => (p.busy ? "Выполняю просьбу…" : (last?.reply.text ?? "")),
      };
    }
    if (name === "Диалог" && p.info.history.length)
      return {
        onClick: () => setHistoryOpen(true),
        label: "Диалог · История сообщений",
      };
    if (name === "Поле ввода")
      return {
        hidden: !p.allowed,
        content: (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              p.send(p.draft);
            }}
            className="design-composer"
          >
            <input
              aria-label="Просьба"
              placeholder="Попросить номер..."
              value={p.draft}
              maxLength={2000}
              disabled={p.busy || !!p.pending}
              onChange={(e) => p.setDraft(e.target.value)}
            />
            <button
              type="button"
              aria-label="Голосовой ввод"
              disabled={
                !!p.pending || !p.info.actions.includes("transcription")
              }
              onClick={() => p.go("voice")}
            />
            <button
              aria-label="Отправить просьбу"
              disabled={p.busy || !!p.pending || !p.draft.trim()}
            />
          </form>
        ),
      };
  }
  return (
    <DesignScreen screen={screen} bind={bind}>
      <small className="mode-caption">
        {p.info.rehearsal ? "Репетиция · демо" : p.info.source === "final"
          ? "Финальный гость · просмотр" : "Демо-номер · управление"}
      </small>
      {p.page === "plan" && (
        <div className="personal-plan">
          {selectPeriod(false)}
          <Plan steps={p.prepared.scenario.steps} period={p.period} />
        </div>
      )}
      {p.page === "virtual" &&
        (p.previewError ? (
          <div className="read-failure" role="alert">
            {p.previewError}
            <button onClick={() => p.go("plan")}>Посмотреть план</button>
            <button onClick={p.retryPreview}>Повторить чтение</button>
          </div>
        ) : !p.points[p.period] ? (
          <p className="read-failure">Период вне проживания.</p>
        ) : !p.preview ? (
          <p className="read-failure">Загружаем состояние…</p>
        ) : null)}
      {p.liveNote && p.page !== "virtual" && (
        <p role="status" className="last-reading">
          {p.liveNote}
        </p>
      )}
      {p.page === "chat" && !p.allowed && (
        <p className="read-caption">Сеанс доступен только для просмотра.</p>
      )}
      {p.page === "chat" && p.error && (
        <button
          className="dismiss-message"
          disabled={p.busy}
          onClick={p.dismiss}
        >
          Закрыть
        </button>
      )}
      {historyOpen && p.page === "chat" && history}
      {p.overlay}
    </DesignScreen>
  );
}
export type DesignChrome = {
  nav: Navigation;
  overlay: ReactNode;
  badge: string;
  clock: string;
};
