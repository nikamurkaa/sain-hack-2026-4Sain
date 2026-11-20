import {
  DesignScreen,
  Shapes,
  ResponsiveWidget,
  layouts,
} from "./design/Layout";
import { chrome, Hit, deviceId, deviceLevel } from "./design/MobileStay";
import type { DesignChrome } from "./design/MobileStay";
import { useState } from "react";
import {
  describe,
  deviceNames,
  fieldNames,
  preferenceItemLabel,
  periodAt,
  time,
  titles,
} from "./model";
import type { Room, Step, Catalog, Period, Values } from "./model";
export function Icon({ name }: { name: string }) {
  return (
    <img
      className="icon"
      alt=""
      src={"/media/icons/" + (name === "dnd" ? "moon" : name) + ".svg"}
    />
  );
}
export function Hero({
  period,
  title,
  detail,
}: {
  period: Period;
  title: string;
  detail: string;
}) {
  const screen = { morning: 2, day: 4, evening: 6, night: 8 }[period];
  const widget = layouts[screen - 1].blocks.find((w) =>
    w.texts.some((t) => t.value === "Уже настроен"),
  )!;
  return (
    <div className="desktop-hero">
      <Shapes screen={screen} />
      <ResponsiveWidget
        screen={screen}
        widget={widget}
        bind={{
          text: (s, i) =>
            i === 0
              ? Object.values(titles).includes(title)
                ? s
                : title
              : detail,
        }}
      />
    </div>
  );
}
export function Devices({
  room,
  catalog,
  open,
  list = false,
  ids = Object.keys(deviceNames),
}: {
  ids?: string[];
  room?: Room;
  catalog: Catalog;
  open?: (key: string) => void;
  list?: boolean;
}) {
  if (!list) {
    const screen = 9,
      cards = layouts[screen - 1].blocks.filter((w) => deviceId(w));
    return (
      <div className="devices desktop-devices">
        <Shapes screen={screen} />
        {cards.map((w) => {
          const id = deviceId(w)!;
          return (
            <ResponsiveWidget
              key={id}
              screen={screen}
              widget={w}
              bind={{
                className: "device" + (id === "sound" ? " device-sound" : ""),
                label: deviceNames[id] + ": " + describe(id, room?.[id], catalog),
                title: id === "sound" ? describe(id, room?.[id], catalog) : undefined,
                onClick: open && room ? () => open(id) : undefined,
                level: deviceLevel(id, room),
                text: (s) =>
                  s === deviceNames[id] ? s : describe(id, room?.[id], catalog),
              }}
            />
          );
        })}
      </div>
    );
  }
  return (
    <div className={list ? "rows" : "devices"}>
      {ids.map((id) => {
        const name = deviceNames[id];
        const v = room?.[id] ?? {},
          value = describe(id, v, catalog);
        const amount =
          id === "climate"
            ? (Number(v.temperature_c) - 16) * 10
            : id === "light"
              ? Number(v.brightness)
              : id === "sound"
                ? Number(v.volume)
                : null;
        return (
          <button
            className="device"
            key={id}
            disabled={!open || !room}
            onClick={() => open?.(id)}
          >
            <Icon name={id} />
            <span>
              <small>{name}</small>
              <strong>{value}</strong>
            </span>
            {!list && room && (id === "dnd" || id === "curtains") && (
              <i
                aria-hidden
                className={
                  "switchmark " +
                  (v.enabled === true || Number(v.position) > 0 ? "on" : "")
                }
              />
            )}
            {!list && amount !== null && Number.isFinite(amount) && (
              <i
                className="meter"
                style={
                  {
                    "--level": Math.min(100, Math.max(0, amount)) + "%",
                  } as React.CSSProperties
                }
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
export function Detail({
  data, catalog, depth = 0,
}: {
  data: Record<string, unknown>;
  catalog?: Catalog;
  depth?: number;
}) {
  const readable = (key: string, value: unknown): string => {
    const terms: Record<string, string> = {
      neutral: "Умеренная температура", normal: "Умеренная температура",
      cool: "Предпочитает прохладу", warm: "Предпочитает тепло",
      both: "Свет и звук", light: "Свет", sound: "Звук",
      morning: "Утро", evening: "Вечер", day: "День", night: "Ночь",
    };
    if (typeof value === "boolean") return value ? "Да" : "Нет";
    if (typeof value === "number" && key === "temperature_c") return value + " °C";
    if (typeof value === "number" && ["volume", "brightness", "position"].includes(key))
      return value + " %";
    if (typeof value === "number" && ["timer", "timer_minutes", "window_minutes"].includes(key))
      return value + " мин";
    if (typeof value === "string" && catalog?.tracks) {
      const track = catalog.tracks.find((item) => item.track_id === value);
      if (track) return track.title;
    }
    if (typeof value === "string")
      return terms[value] ?? preferenceItemLabel(value);
    return String(value);
  };
  return (
    <dl className="preferences">
      {Object.entries(data)
        .filter(([, v]) => v != null && v !== "" &&
          (typeof v !== "object" || Object.keys(v).length > 0))
        .map(([k, v]) => (
          <div key={k}>
            <dt>{fieldNames[k] ?? k.replaceAll("_", " ")}</dt>
            <dd>
              {typeof v === "object" ? (
                Array.isArray(v) ? (
                  v.map((item, index) => item !== null && typeof item === "object"
                    ? depth < 3
                      ? <div className="preference-entry" key={index}>
                          <Detail data={item as Record<string, unknown>}
                                  catalog={catalog} depth={depth + 1} />
                        </div>
                      : <span key={index}>Дополнительные сведения</span>
                    : <span key={index}>
                        {index > 0 ? ", " : ""}{readable(k, item)}
                      </span>)
                ) : depth < 3 ? (
                  <Detail data={v as Record<string, unknown>}
                          catalog={catalog} depth={depth + 1} />
                ) : "Дополнительные сведения"
              ) : readable(k, v)}
            </dd>
          </div>
        ))}
    </dl>
  );
}
export function Plan({ steps, period }: { steps: Step[]; period: Period }) {
  const events = steps
    .filter((s) => periodAt(s.at) === period)
    .sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  return (
    <>
      <div
        className="wave"
        style={{ backgroundImage: "url(/media/decor/" + period + "-wave.svg)" }}
      >
        <Icon
          name={
            period === "day" ? "sun" : period === "morning" ? "sunrise" : "moon"
          }
        />
        <strong>{titles[period]}</strong>
      </div>
      <div className="timeline">
        {events.length ? (
          events.map((s, i) => (
            <article key={i}>
              <time>{time(s.at)}</time>
              <div>
                <Icon name={s.device_id} />
                <section>
                  <b>{deviceNames[s.device_id]}</b>
                  <small>
                    {Object.entries(s.values)
                      .map(([field, value]) => {
                        const units: Record<string, string> = {
                          brightness: "%",
                          position: "%",
                          volume: "%",
                          timer_minutes: " мин",
                          window_minutes: " мин",
                          temperature_c: " °C",
                          color_temperature_k: " K",
                        };
                        if (field === "at" && typeof value === "string")
                          return time(value);
                        if (field === "enabled")
                          return value ? "Включить" : "Выключить";
                        if (field === "mode")
                          return (
                            {
                              both: "Свет и звук",
                              light: "Свет",
                              sound: "Звук",
                            }[String(value)] ?? String(value)
                          );
                        return String(value ?? "—") + (units[field] ?? "");
                      })
                      .join(" · ")}
                  </small>
                </section>
              </div>
            </article>
          ))
        ) : (
          <p>В этот период автоматических изменений не запланировано.</p>
        )}
      </div>
    </>
  );
}
export function Settings({
  design,
  id,
  values,
  catalog,
  submit,
  apply,
}: {
  design?: DesignChrome;
  id: string;
  values: Values;
  catalog: Catalog;
  submit: (text: string) => void;
  apply: (id: string, values: Values) => void;
}) {
  const [val, set] = useState(
    String(
      {
        climate: values.temperature_c,
        alarm: typeof values.at === "string" ? time(values.at) : "",
        sound: values.track_id,
        light: values.brightness,
        curtains: values.position,
        dnd: String(values.enabled === true),
      }[id] ?? "",
    ),
  );
  const [field, choose] = useState("track_id");
  const [alarmMode, setAlarmMode] = useState(String(values.mode ?? "both"));
  const modes: Record<string, string> = {
    both: "свет и звук",
    light: "свет",
    sound: "звук",
  };
  const numeric =
    id === "climate" ||
    id === "light" ||
    id === "curtains" ||
    (id === "sound" && field === "volume");
  const range = catalog.devices
    .find((d) => d.device_id === id)
    ?.fields.find(
      (f) =>
        f.field_id ===
        {
          climate: "temperature_c",
          light: "brightness",
          curtains: "position",
          sound: field,
        }[id],
    )?.value_schema;
  const phrase = () =>
    ({
      climate: "Установи температуру " + val + " градусов",
      light: "Установи яркость " + val + " процентов",
      curtains: "Открой шторы на " + val + " процентов",
      alarm: "Разбуди меня в " + val + ", режим " + modes[alarmMode],
      dnd: (val === "true" ? "Включи" : "Выключи") + " режим не беспокоить",
      sound:
        field === "volume"
          ? "Установи громкость " + val + " процентов"
          : "Включи звук " +
            catalog.tracks.find((t) => t.track_id === val)?.title,
    })[id]!;
  const save = () => {
    if (id === "climate") return apply(id, { temperature_c: Number(val) });
    if (id === "light") return apply(id, { brightness: Number(val) });
    if (id === "curtains") return apply(id, { position: Number(val) });
    if (id === "sound") return apply(id, field === "volume" ? { volume: Number(val) } : { track_id: val });
    if (id === "alarm") return apply(id, { at: val, mode: alarmMode });
    if (id === "dnd") return apply(id, { enabled: val === "true" });
  };
  if (design && ["climate", "alarm", "sound"].includes(id)) {
    const frame = id === "climate" ? 21 : id === "alarm" ? 22 : 23;
    const selectedTrack = catalog.tracks.find(
      (t) => t.track_id === (field === "track_id" ? val : values.track_id),
    );
    return (
      <DesignScreen
        screen={frame}
        bind={(w) => {
          const common = chrome(w, design.nav, design.clock);
          if (common) return common;
          const name = w.name;
          if (name === "Алина,") return { role: "heading" };
          if (name === "Сохранить")
            return {
              onClick: save,
              disabled: !val,
              text:
                id === "sound"
                  ? () =>
                      field === "volume"
                        ? "Сохранить громкость"
                        : "Сохранить трек"
                  : undefined,
            };
          if (id === "climate") {
            if (name === "22 °C")
              return {
                className: "degree-reading",
                text: () => describe(id, values, catalog).replace(" °C", "°C"),
              };
            if (name.startsWith("утро-ночь"))
              return {
                text: (v, i) => (i === 0 ? "" : v),
                children: (
                  <>
                    <input
                      className="degree-value"
                      aria-label="Температура"
                      type="number"
                      step="0.5"
                      min={range?.minimum ?? 16}
                      max={range?.maximum ?? 26}
                      value={val}
                      onChange={(e) => set(e.target.value)}
                    />
                    <Hit
                      label="Уменьшить температуру"
                      box={[0, 0, 64, 62]}
                      disabled={Number(val) <= (range?.minimum ?? 16)}
                      onClick={() =>
                        set(
                          String(
                            Math.max(range?.minimum ?? 16, Number(val) - 0.5),
                          ),
                        )
                      }
                    />
                    <Hit
                      label="Увеличить температуру"
                      box={[193, 0, 64, 62]}
                      disabled={Number(val) >= (range?.maximum ?? 26)}
                      onClick={() =>
                        set(
                          String(
                            Math.min(range?.maximum ?? 26, Number(val) + 0.5),
                          ),
                        )
                      }
                    />
                  </>
                ),
              };
            if (name === "Ответ") {
              if (w.box[1] > 420) return { hidden: true };
              return {
                text: () => "Сохранить",
                onClick: save,
                disabled:
                  !val ||
                  Number(val) < (range?.minimum ?? 16) ||
                  Number(val) > (range?.maximum ?? 26),
              };
            }
          }
          if (id === "alarm") {
            if (name.startsWith("утро-ночь"))
              return {
                content: (
                  <input
                    aria-label="Время пробуждения"
                    className="alarm-value"
                    type="time"
                    value={val}
                    onChange={(e) => set(e.target.value)}
                  />
                ),
              };
            if (name.startsWith("Timeline Card")) {
              if (w.texts[0].value === "Повтор")
                return { text: () => "Повтор недоступен", level: null };
              if (w.texts[0].value === "Звук")
                return {
                  text: (v, i) => (i === 0 ? "Сигнал" : ""),
                  children: (
                    <select
                      className="choice-value"
                      aria-label="Сигнал"
                      value={alarmMode}
                      onChange={(e) => setAlarmMode(e.target.value)}
                    >
                      {Object.entries(modes).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ),
                };
              return {
                text: (_, i) =>
                  i === 0
                    ? "Окно пробуждения"
                    : String(values.window_minutes ?? "—") + " мин",
              };
            }
          }
          if (id === "sound") {
            if (name.startsWith("утро-ночь"))
              return {
                content: (
                  <select
                    className="track-value"
                    aria-label="Трек"
                    value={selectedTrack?.track_id ?? ""}
                    onChange={(e) => {
                      choose("track_id");
                      set(e.target.value);
                    }}
                  >
                    {catalog.tracks.map((t) => (
                      <option key={t.track_id} value={t.track_id}>
                        {t.title}
                      </option>
                    ))}
                  </select>
                ),
              };
            if (name.startsWith("image "))
              return {
                hidden: !selectedTrack?.title
                  .toLowerCase()
                  .includes("перфоратор"),
              };
            if (name === "Component 12")
              return {
                level: Number(field === "volume" ? val : values.volume) / 100,
                children: (
                  <input
                    className="volume-range"
                    aria-label="Громкость"
                    type="range"
                    min={0}
                    max={100}
                    value={Number(field === "volume" ? val : values.volume)}
                    onChange={(e) => {
                      choose("volume");
                      set(e.target.value);
                    }}
                  />
                ),
              };
            if (name === "22 °C")
              return {
                text: () =>
                  String(field === "volume" ? val : (values.volume ?? "—")) +
                  "%",
              };
            if (name.startsWith("Timeline Card"))
              return {
                text: (v, i) =>
                  i === 0
                    ? v
                    : String(values.timer_minutes ?? "—") + " мин · просмотр",
              };
          }
        }}
      >
        <small className="mode-caption">{design.badge}</small>
        {id === "alarm" && values.at && (
          <button
            className="alarm-cancel"
            onClick={() => submit("Отмени будильник")}
          >
            Выключить будильник
          </button>
        )}
        {design.overlay}
      </DesignScreen>
    );
  }
  return (
    <form
      className="settings"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <h1>
        <Icon name={id} />
        {deviceNames[id]}
      </h1>
      <small>Сейчас в номере</small>
      <h2>{describe(id, values, catalog)}</h2>
      {id === "sound" && (
        <label>
          Настройка
          <select
            value={field}
            onChange={(e) => {
              choose(e.target.value);
              set(String(values[e.target.value] ?? ""));
            }}
          >
            <option value="track_id">Трек</option>
            <option value="volume">Громкость</option>
          </select>
        </label>
      )}
      {numeric ? (
        <label>
          {
            fieldNames[
              {
                climate: "temperature_c",
                light: "brightness",
                curtains: "position",
                sound: "volume",
              }[id]!
            ]
          }
          <span className="stepper">
            {id === "climate" && (
              <button
                type="button"
                aria-label="Уменьшить температуру"
                disabled={Number(val) <= Number(range?.minimum)}
                onClick={() =>
                  set(String(Math.max(range?.minimum ?? 16, Number(val) - 0.5)))
                }
              >
                −
              </button>
            )}
            <input
              type="number"
              required
              step={id === "climate" ? 0.5 : 1}
              min={range?.minimum}
              max={range?.maximum}
              value={val}
              onChange={(e) => set(e.target.value)}
            />
            {id === "climate" && (
              <button
                aria-label="Увеличить температуру"
                type="button"
                disabled={Number(val) >= Number(range?.maximum)}
                onClick={() =>
                  set(String(Math.min(range?.maximum ?? 26, Number(val) + 0.5)))
                }
              >
                +
              </button>
            )}
          </span>
          {id !== "climate" && (
            <input
              aria-label="Шкала"
              type="range"
              value={val}
              min={range?.minimum}
              max={range?.maximum}
              onChange={(e) => set(e.target.value)}
            />
          )}
        </label>
      ) : id === "alarm" ? (
        <label>
          Время пробуждения
          <input
            required
            type="time"
            value={val}
            onChange={(e) => set(e.target.value)}
          />
        </label>
      ) : id === "sound" ? (
        <label>
          Трек
          <select value={val} onChange={(e) => set(e.target.value)}>
            {catalog.tracks.map((t) => (
              <option value={t.track_id} key={t.track_id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <label>
          Установить режим
          <select value={val} onChange={(e) => set(e.target.value)}>
            <option value="true">Включить</option>
            <option value="false">Выключить</option>
          </select>
        </label>
      )}
      {id === "alarm" && (
        <>
          <label>
            Сигнал
            <select
              value={alarmMode}
              onChange={(e) => setAlarmMode(e.target.value)}
            >
              {Object.entries(modes).map(([mode, title]) => (
                <option key={mode} value={mode}>
                  {title}
                </option>
              ))}
            </select>
          </label>
          <small>
            Окно пробуждения: {String(values.window_minutes ?? "—")} мин ·
            Повтор недоступен
          </small>
          {values.at && (
            <button type="button" onClick={() => submit("Отмени будильник")}>
              Выключить будильник
            </button>
          )}
        </>
      )}
      {id === "sound" && (
        <small>
          Таймер текущего звука: {String(values.timer_minutes ?? "—")} мин
        </small>
      )}
      <button className="primary" disabled={!val}>
        Сохранить
      </button>
    </form>
  );
}
