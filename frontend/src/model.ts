export type Values = Record<string, string | number | boolean | null>;
export type Room = Record<string, Values>;
export type Snapshot = { at: string; state: Room };
export type Step = { at: string; device_id: string; values: Values };
export type Reply = { text: string; response_class: "done" | "refused" };
export type Exchange = { at: string; utterances: string[]; reply: Reply };
export type Session = {
  rehearsal?: boolean;
  source: "dev" | "final";
  stay_id: string;
  at: string;
  until: string;
  expires_in: number;
  read_only: boolean;
  can_send_requests: boolean;
  actions: string[];
  history: Exchange[];
  connection_status: string;
};
export type Guest = {
  user_id: string;
  stay: Values;
  profile: Values;
  preferences: Record<string, unknown>;
};
export type Prepared = {
  guest: Guest;
  scenario: { steps: Step[] };
  last_confirmed: Snapshot | null;
};
export type Catalog = {
  tracks: { track_id: string; title: string }[];
  devices: {
    device_id: string;
    fields: {
      field_id: string;
      value_schema: { minimum?: number; maximum?: number };
    }[];
  }[];
};
export const periods = ["morning", "day", "evening", "night"] as const;
export type Period = (typeof periods)[number];
export const titles = {
  morning: "Утро",
  day: "День",
  evening: "Вечер",
  night: "Ночь",
};
export const deviceNames: Record<string, string> = {
  light: "Свет",
  climate: "Климат",
  curtains: "Шторы",
  sound: "Звук",
  alarm: "Будильник",
  dnd: "Не беспокоить",
};
export const time = (stamp: string) => stamp.slice(11, 16);
export function periodAt(stamp: string): Period {
  const h = Number(stamp.slice(11, 13));
  return h < 6 || h >= 23
    ? "night"
    : h < 10
      ? "morning"
      : h < 18
        ? "day"
        : "evening";
}
// Use timestamps supplied by the simulator, preserving the hotel offset.
export function moments(
  start: string,
  end: string,
  steps: Step[],
): Partial<Record<Period, string>> {
  const choices: Partial<Record<Period, string>> = {};
  for (const stamp of [start, ...steps.map((s) => s.at), end]) {
    if (
      Date.parse(stamp) >= Date.parse(start) &&
      Date.parse(stamp) <= Date.parse(end)
    )
      choices[periodAt(stamp)] ??= stamp;
  }
  // Include unscheduled periods inside the stay without inventing events.
  const offset = start.slice(-6),
    sign = offset[0] === "-" ? -1 : 1;
  const minutes =
    sign * (Number(offset.slice(1, 3)) * 60 + Number(offset.slice(4, 6)));
  for (
    let ms = Math.ceil(Date.parse(start) / 3600000) * 3600000;
    ms <= Date.parse(end);
    ms += 3600000
  ) {
    const local =
      new Date(ms + minutes * 60000).toISOString().slice(0, 19) + offset;
    choices[periodAt(local)] ??= local;
  }
  return choices;
}
export function describe(id: string, v: Values = {}, catalog?: Catalog) {
  switch (id) {
    case "light":
      return v.brightness == null ? "—" : v.brightness + " %";
    case "climate":
      return v.temperature_c == null ? "—" : v.temperature_c + " °C";
    case "sound":
      return v.volume === 0
        ? "Выключен"
        : catalog?.tracks.find((t) => t.track_id === v.track_id)?.title ||
            String(v.track_id ?? "—");
    case "curtains":
      return v.position === 0
        ? "Закрыты"
        : v.position === 100
          ? "Открыты"
          : v.position == null
            ? "—"
            : v.position + " %";
    case "alarm":
      return v.at === null
        ? "Выключен"
        : typeof v.at === "string"
          ? time(v.at)
          : "—";
    case "dnd":
      return typeof v.enabled === "boolean"
        ? v.enabled
          ? "Включён"
          : "Выключен"
        : "—";
    default:
      return "—";
  }
}
// The dataset stores internal preference IDs; never surface known IDs as
// raw English strings in the guest-facing profile.
export function preferenceItemLabel(value: string): string {
  const translations: Record<string, string> = {
    temperature: "Температура",
    tracks: "Звуки",
    volume: "Громкость",
    timer: "Таймер звука",
    alarm_mode: "Режим пробуждения",
    neutral: "Умеренная температура",
    normal: "Умеренная температура",
    cool: "Прохлада",
    warm: "Тепло",
    both: "Свет и звук",
    light: "Свет",
    sound: "Звук",
    morning: "Утро",
    evening: "Вечер",
    day: "День",
    night: "Ночь",
  };
  return translations[value] ?? fieldNames[value] ?? value.replaceAll("_", " ");
}
export const fieldNames: Record<string, string> = {
  temperature_c: "Температура, °C",
  brightness: "Яркость, %",
  color_temperature_k: "Температура света, K",
  position: "Открытие штор, %",
  track_id: "Звук",
  volume: "Громкость, %",
  timer_minutes: "Таймер, мин",
  at: "Время",
  window_minutes: "Окно, мин",
  mode: "Режим",
  enabled: "Не беспокоить",
  timezone: "Домашний часовой пояс",
  chronotype: "Хронотип",
  goal: "Цель",
  weekday_bedtime: "Обычное время сна",
  weekday_wake_time: "Обычное время пробуждения",
  temperature: "Климат",
  tracks: "Треки",
  timer: "Таймер",
  alarm_mode: "Способ пробуждения",
  sources: "Источники",
  defaults: "Значения по умолчанию",
  home: "Дома",
  morning: "Утро",
  yesterday: "Прошлый заезд",
  favorite_track_ids: "Любимые звуки",
  light_sensitive: "Чувствительность к свету",
  gentle_alarm: "Мягкое пробуждение",
  dislikes: "Что не нравится",
  source_id: "Источник",
  quote: "Подтверждение предпочтения",
  sleep_preferences: "Привычки сна",
  user_id: "Идентификатор гостя",
  display_name: "Имя",
};
