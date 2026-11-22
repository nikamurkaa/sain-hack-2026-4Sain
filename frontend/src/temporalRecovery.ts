import { instant } from "./api.ts";
import type { ActionIssue } from "./actionFeedback";
import type { Reconciliation, Snapshot } from "./model";

function object(v: unknown): Record<string, unknown> | null {
  return v !== null && typeof v === "object" && !Array.isArray(v)
    ? v as Record<string, unknown> : null;
}
/** A 200 response does not prove that it belongs to the pending operation.
 * Require the same ID, kind, confirmed-device set and UTC instant for BOTH
 * server-declared attempted_at and the returned snapshot.at.
 */
export function verifiedReconciliation(issue: ActionIssue, raw: unknown):
    { snapshot: Snapshot; nextActionAt: string } | null {
  const data = object(raw), snap = object(data?.snapshot),
    state = object(snap?.state);
  if (!data || !snap || !state || data.verified !== true ||
      data.operation_id !== issue.operationId ||
      data.status !== issue.kind ||
      instant(issue.attemptedAt) === null ||
      instant(data.attempted_at) !== instant(issue.attemptedAt) ||
      instant(snap.at) !== instant(issue.attemptedAt) ||
      instant(data.next_action_at) === null ||
      (instant(data.next_action_at) as number) < (instant(issue.attemptedAt) as number))
    return null;
  const named = data.confirmed_devices;
  if (!Array.isArray(named) || named.length !== issue.confirmed.length ||
      !named.every((id: unknown) => typeof id === "string" &&
        id in ({ light:1, climate:1, sound:1, curtains:1, alarm:1, dnd:1 }))) return null;
  for (const id of named as string[]) {
    if (!object(state[id])) return null;
  }
  // Confirmed device identity is bound to the original issue, not merely
  // present in the newly returned snapshot. Use a stable label map.
  const localized: Record<string,string> = {
    light:"Свет",climate:"Климат",sound:"Звук",curtains:"Шторы",
    alarm:"Будильник",dnd:"Не беспокоить"
  };
  if (named.some((id: string) => !issue.confirmed.includes(localized[id])) ||
      new Set(named).size !== named.length) return null;
  if (Object.keys(state).length === 0 ||
      Object.values(state).some(v => {
        const values = object(v);
        return !values || Object.values(values).some(x => x !== null &&
          typeof x !== "string" && typeof x !== "boolean" &&
          !(typeof x === "number" && Number.isFinite(x)));
      })) return null;
  return { snapshot: snap as unknown as Snapshot, nextActionAt: data.next_action_at as string };
}
