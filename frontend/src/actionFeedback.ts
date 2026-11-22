import type { ActionApiError, ActionErrorKind } from "./api";
import { deviceNames } from "./model.ts";

export type ActionIssue = {
  kind: ActionErrorKind;
  title: string;
  description: string;
  confirmed: string[];
  checked: boolean;
  operationId: string;
};
export function actionIssue(error: ActionApiError): ActionIssue {
  const confirmed = error.confirmedDevices.map((device) => deviceNames[device]);
  const titles: Record<ActionErrorKind, string> = {
    partial: "Просьба выполнена частично",
    uncertain: "Результат просьбы пока неизвестен",
    conflict: "Обнаружено расхождение состояния номера",
    failed: "Не удалось выполнить просьбу",
  };
  const details: Record<ActionErrorKind, string> = {
    partial: "Остальные изменения не подтверждены. Не повторяйте всю просьбу: сначала проверьте текущее состояние номера.",
    uncertain: "Результат действия не установлен. Команда могла быть применена. Не отправляйте её повторно до проверки.",
    conflict: "Фактическое состояние отличается от ожидаемого. Не все изменения подтверждены; повтор может изменить уже настроенные устройства.",
    failed: "Сервис отклонил действие. Состояние номера нужно сверить, прежде чем выбирать новые настройки.",
  };
  return { kind: error.kind, title: titles[error.kind], description: details[error.kind],
           confirmed, checked: false, operationId: error.operationId };
}
