import { deviceNames } from "./model.ts";
export class ApiError extends Error {
  status: number;
  readonly code: string | null;
  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
export type DefinitiveRejectionKind = "prehandler_validation" | "domain_refusal";
/** Only a verified same-origin server response may certify no action POST began. */
export class DefinitiveApiError extends ApiError {
  readonly rejectionKind: DefinitiveRejectionKind;
  constructor(status: number, message: string, code: string, kind: DefinitiveRejectionKind) {
    super(status, message, code);
    this.name = "DefinitiveApiError";
    this.rejectionKind = kind;
  }
}
/** Dispositions are intentionally conservative: only definitive_* may
 * clear a per-request transport uncertainty, never an existing session issue.
 */
export type FailureCategory =
  | "definitive_validation" | "domain_refusal" | "action_partial" | "action_uncertain"
  | "action_conflict" | "action_failed" | "authentication" | "authorization"
  | "idempotency_conflict" | "recovery_required" | "time_backwards"
  | "rate_limited" | "transport_failure" | "unknown_server" | "unknown_rejection";
export function failureCategory(error: unknown): FailureCategory {
  if (error instanceof DefinitiveApiError) return error.rejectionKind === "prehandler_validation"
    ? "definitive_validation" : "domain_refusal";
  if (error instanceof ActionApiError) return ("action_" + error.kind) as FailureCategory;
  if (!(error instanceof ApiError)) return "transport_failure";
  if (error.status === 401) return "authentication";
  if (error.status === 403) return "authorization";
  if (error.status === 409 && error.code === "IDEMPOTENCY_CONFLICT") return "idempotency_conflict";
  if (error.status === 409 && error.code === "RECOVERY_REQUIRED") return "recovery_required";
  if (error.status === 409 && error.code === "TIME_BACKWARDS") return "time_backwards";
  if (error.status === 429) return "rate_limited";
  if (error.status >= 500) return "unknown_server";
  return "unknown_rejection";
}


/** Explicitly recognized *action* outcomes, not all HTTP 409 responses. */
export type ActionErrorKind = "partial" | "uncertain" | "conflict" | "failed";
export type ConfirmedDevice = keyof typeof deviceNames;
export class ActionApiError extends ApiError {
  readonly kind: ActionErrorKind;
  readonly code: string;
  readonly operationId: string;
  readonly confirmedDevices: readonly ConfirmedDevice[];
  readonly attemptedAt: string;
  constructor(status: number, message: string, code: string, kind: ActionErrorKind,
              operationId: string, confirmedDevices: readonly ConfirmedDevice[], attemptedAt: string) {
    super(status, message, code);
    this.name = "ActionApiError";
    this.code = code;
    this.kind = kind;
    this.operationId = operationId;
    this.confirmedDevices = Object.freeze([...confirmedDevices]);
    this.attemptedAt = attemptedAt;
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
/** Require explicit UTC-offset; comparison is by real instant, never ISO text. */
export function instant(raw: unknown): number | null {
  if (typeof raw !== "string" ||
      !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(raw)) return null;
  const ms = Date.parse(raw);
  return Number.isFinite(ms) ? ms : null;
}
function validatedOperationId(raw: unknown): raw is string {
  return typeof raw === "string" && raw.length >= 1 && raw.length <= 128 &&
    /^[A-Za-z0-9_-]+$/.test(raw) && !/(?:bearer|secret|token|password)/i.test(raw);
}
/** Never derive an action confirmation from an untrusted/error-shaped JSON body. */
export function parseActionFailure(
  status: number, value: unknown,
  proof: { rejectionClass?: string | null; path?: string } = {},
): ApiError {
  const body = object(value);
  const message = safeMessage(body) || errors[status] || "Сервис временно недоступен.";
  const code = body?.code;
  // FastAPI validation happens before /messages or /devices enters its handler.
  // HTTP 422 alone is NOT sufficient: arbitrary domain/upstream 422 must
  // remain unknown until the trusted server explicitly certifies no mutation.
  const writeRoute = proof.path === "messages" || proof.path === "devices";
  const details = body?.detail;
  const validRequestErrors = Array.isArray(details) && details.length > 0 &&
    details.length <= 20 && details.every((item: unknown) => {
      const e = object(item);
      return !!e && typeof e.type === "string" && e.type.length <= 80 &&
        Array.isArray(e.loc) && e.loc.length > 0 &&
        ["body", "header", "query", "path"].includes(e.loc[0]) &&
        e.loc.length <= 8;
    });
  if (status === 422 && writeRoute && proof.rejectionClass === "prehandler" &&
      validRequestErrors)
    return new DefinitiveApiError(status, errors[422], "REQUEST_VALIDATION", "prehandler_validation");
  if (status === 422 && writeRoute && proof.rejectionClass === "domain" &&
      body?.status === "error" &&
      (code === "INVALID_TIME" || (proof.path === "devices" && code === "INVALID_VALUE")))
    return new DefinitiveApiError(status, message, code as string, "domain_refusal");
  const kind = typeof code === "string" ? recognized[code] : undefined;
  const op = body?.operation_id;
  const rawDevices = body?.confirmed_devices;
  const attemptedAt = body?.attempted_at;
  if (status === 409 && kind && validatedOperationId(op) && instant(attemptedAt) !== null &&
      Array.isArray(rawDevices) && rawDevices.length <= 6 &&
      rawDevices.every((id: unknown) => typeof id === "string" && deviceIDs.includes(id)) &&
      new Set(rawDevices).size === rawDevices.length &&
      (kind !== "partial" || rawDevices.length > 0)) {
    return new ActionApiError(status, message, code as string, kind, op,
      rawDevices as ConfirmedDevice[], attemptedAt as string);
  }
  return new ApiError(status, message,
    body?.status === "error" && typeof code === "string" &&
    /^[A-Z][A-Z0-9_]{2,63}$/.test(code) ? code : null);
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
      throw parseActionFailure(response.status, body, {
        rejectionClass: response.headers.get("X-Sain-Rejection-Class"),
        path: path.split("?")[0],
      });
    }
    if (response.status === 204) return undefined as T;
    const data = await response.json();
    if (path === "session" && response.headers.get("X-Sain-Rehearsal") === "1")
      data.rehearsal = true;
    if (path === "session" && response.headers.get("X-Sain-Live-AI") === "1")
      data.live_ai = true;
    return data;
  };
}
