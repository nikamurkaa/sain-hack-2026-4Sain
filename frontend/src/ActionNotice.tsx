import type { ActionIssue } from "./actionFeedback";

export function ActionNotice({ issue, refresh, dismiss, disabled = false }: {
  issue: ActionIssue;
  refresh: () => void;
  dismiss: () => void;
  disabled?: boolean;
}) {
  return (
    <section className={"action-notice action-" + issue.kind}
             role="alert" aria-label={issue.title} data-action-kind={issue.kind}>
      <h3>{issue.title}</h3>
      {issue.confirmed.length > 0 && (
        <p>Подтверждённо изменены: <strong>{issue.confirmed.join(", ")}</strong>.</p>
      )}
      <p>{issue.description}</p>
      <p className="action-verification" role="status">
        {issue.checked
          ? "Фактическое состояние получено. Проверьте настройки перед новым действием."
          : "Актуальное состояние не подтверждено. Последний снимок может быть устаревшим."}
      </p>
      <div className="action-notice-actions">
        <button type="button" disabled={disabled} onClick={refresh}>
          Обновить состояние номера
        </button>
        <button type="button" disabled={disabled} onClick={dismiss}>
          Закрыть уведомление
        </button>
      </div>
    </section>
  );
}
