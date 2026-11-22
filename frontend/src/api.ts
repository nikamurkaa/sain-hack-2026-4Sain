import { deviceNames } from "./model.ts";
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Explicitly recognized *action* outcomes, not all HTTP 409 responses. */
export type ActionErrorKind = "partial" | "uncertain" | "conflict" | "failed";
export type ConfirmedDevice = keyof typeof deviceNames;
export class ActionApiError extends ApiError {
  readonly kind: ActionErrorKind;
  readonly code: string;
  readonly operationId: string;
  readonly confirmedDevices: readonly ConfirmedDevice[];
  constructor(status: number, message: string, code: string, kind: ActionErrorKind,
              operationId: string, confirmedDevices: readonly ConfirmedDevice[]) {
    super(status, message);
    this.name = "ActionApiError";
    this.code = code;
    this.kind = kind;
    this.operationId = operationId;
    this.confirmedDevices = Object.freeze([...confirmedDevices]);
  }
}
const errors: Record<number, string> = {
  401: "Срок доступа истёк.",
  402: "Дневной бюджет исчерпан до 00:00 МСК. Доступен текстовый ввод.",
  403: "Нет доступа к этой операции.",
  409: "Конфликт сеанса или неизвестный результат.",
  413: "Запись больше 5 МБ.",
  415: "Формат записи не поддерживается.",
  422: "Проверьте данные запроса.",
  429: "Достигнут лимит. Подождите минуту.",
};
function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : null;
}
function safeMessage(body: Record<string, unknown> | null): string {
  const message = body?.message;
  return typeof message === "string" && message.length <= 240 &&
    !/[\r\n]|https?:\/\/|Bearer|sk-[a-z0-9]|traceback|api[_-]?key|token=/i.test(message)
      ? message.trim() : "";
}
const recognized: Record<string, ActionErrorKind> = {
  ACTION_PARTIAL: "partial",
  ACTION_UNCERTAIN: "uncertain",
  ACTION_CONFLICT: "conflict",
  ACTION_FAILED: "failed",
};
const deviceIDs = Object.keys(deviceNames);
function validatedOperationId(raw: unknown): raw is string {
  return typeof raw === "string" && raw.length >= 1 && raw.length <= 128 &&
    /^[A-Za-z0-9_-]+$/.test(raw) && !/(?:bearer|secret|token|password)/i.test(raw);
}
/** Never derive an action confirmation from an untrusted/error-shaped JSON body. */
export function parseActionFailure(status: number, value: unknown): ApiError {
  const body = object(value);
  const message = safeMessage(body) || errors[status] || "Сервис временно недоступен.";
  const code = body?.code;
  const kind = typeof code === "string" ? recognized[code] : undefined;
  const op = body?.operation_id;
  const rawDevices = body?.confirmed_devices;
  if (status === 409 && kind && validatedOperationId(op) &&
      Array.isArray(rawDevices) && rawDevices.length <= 6 &&
      rawDevices.every((id: unknown) => typeof id === "string" && deviceIDs.includes(id)) &&
      new Set(rawDevices).size === rawDevices.length &&
      (kind !== "partial" || rawDevices.length > 0)) {
    return new ActionApiError(status, message, code as string, kind, op,
      rawDevices as ConfirmedDevice[]);
  }
  return new ApiError(status, message);
}
export function client(token: string, signal: AbortSignal) {
  return async function request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const response = await fetch("/api/v1/" + path, {
      ...options,
      signal: AbortSignal.any([
        signal,
        options.signal ?? signal,
        AbortSignal.timeout(90000),
      ]),
      cache: "no-store",
      redirect: "error",
      headers: { ...options.headers, Authorization: "Bearer " + token },
    });
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => ({}));
      throw parseActionFailure(response.status, body);
    }
    if (response.status === 204) return undefined as T;
    const data = await response.json();
    if (path === "session" && response.headers.get("X-Sain-Rehearsal") === "1")
      data.rehearsal = true;
    return data;
  };
}
