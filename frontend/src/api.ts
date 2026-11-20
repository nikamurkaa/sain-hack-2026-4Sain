export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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
      // Prefer the server's precise response, but never echo secrets or traces.
      const explanation =
        body && typeof body === "object" && "message" in body &&
        typeof body.message === "string" && body.message.length <= 240 &&
        !/[\\r\\n]|https?:\\/\\/|Bearer|sk-[a-z0-9]|traceback|api[_-]?key|token=/i.test(body.message)
          ? body.message.trim()
          : "";
      throw new ApiError(
        response.status,
        explanation || errors[response.status] || "Сервис временно недоступен.",
      );
    }
    if (response.status === 204) return undefined as T;
    const data = await response.json();
    if (path === "session" && response.headers.get("X-Sain-Rehearsal") === "1")
      data.rehearsal = true;
    return data;
  };
}
