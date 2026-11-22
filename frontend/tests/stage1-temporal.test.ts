import { test } from "node:test";
import assert from "node:assert/strict";
import { ActionApiError, instant, parseActionFailure } from "../src/api.ts";
import { verifiedReconciliation } from "../src/temporalRecovery.ts";
import { actionIssue } from "../src/actionFeedback.ts";

const at = "2026-11-12T20:45:00+03:00";
const original = parseActionFailure(409, {
  code: "ACTION_PARTIAL", operation_id: "temporal-test-op",
  attempted_at: at, confirmed_devices: ["light"],
});
assert.ok(original instanceof ActionApiError);
const issue = actionIssue(original as ActionApiError);
const room = { light: {brightness:0}, sound:{volume:20}, climate:{temperature_c:21} };
const proof = {
  verified:true, status:"partial", operation_id:"temporal-test-op",
  attempted_at:at, confirmed_devices:["light"],
  next_action_at:at, snapshot:{at,state:room},
};

test("MR-NEW-01: same real instant with different UTC offset is valid",()=>{
  assert.equal(instant("2026-11-12T17:45:00Z"), instant(at));
  const verified = verifiedReconciliation(issue, {
    ...proof, attempted_at:"2026-11-12T17:45:00+00:00",
    snapshot:{at:"2026-11-12T17:45:00Z",state:room},
  });
  assert.ok(verified);
});

test("MR-NEW-01: arbitrary HTTP 200, wrong timestamp, bad format, wrong operation cannot unlock",()=>{
  for (const variant of [
    {...proof, snapshot:{at:"2026-11-12T20:00:00+03:00",state:room}},
    {...proof, snapshot:{at:"not-a-date",state:room}},
    {...proof, attempted_at:"2026-11-12T20:00:00+03:00"},
    {...proof, operation_id:"another-operation"},
    {...proof, confirmed_devices:[]},
    {...proof, verified:false},
    {...proof, status:"done"},
    {...proof, next_action_at:"2026-11-12T20:00:00+03:00"},
    {...proof, snapshot:{at,state:{sound:{volume:20}}}},
    {...proof, snapshot:{at,state:{light:{brightness:Infinity}}}},
    null,
  ]) assert.equal(verifiedReconciliation(issue,variant),null,JSON.stringify(variant));
});

test("MR-NEW-01: unknown/malformed attempted time is never accepted as partial evidence",()=>{
  for(const bad of [undefined, "2026-11-12T20:45:00", "2026-11-12TXX:45:00+03:00",
                    "", "Bearer-secret", "2026-11-12T20:45:00+99:00"]){
    const got=parseActionFailure(409,{
      code:"ACTION_PARTIAL",operation_id:"temporal-test-op",confirmed_devices:["light"],
      attempted_at:bad,
    });
    assert.ok(!(got instanceof ActionApiError),String(bad));
  }
});
