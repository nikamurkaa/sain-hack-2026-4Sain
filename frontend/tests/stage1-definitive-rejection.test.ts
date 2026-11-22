import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ApiError, ActionApiError, DefinitiveApiError,
  failureCategory, parseActionFailure,
} from "../src/api.ts";

const body422={detail:[{type:"string_too_short",loc:["body","text"],msg:"Too short"}]};
const safePre={path:"messages",rejectionClass:"prehandler"};
const safeDevice={path:"devices",rejectionClass:"domain"};
const time="2026-11-12T20:45:00+03:00";

test("MR-NEW-06: only server-certified Pydantic pre-action 422 is definitive",()=>{
  const valid=parseActionFailure(422,body422,safePre);
  assert.ok(valid instanceof DefinitiveApiError);
  assert.equal(failureCategory(valid),"definitive_validation");
  for(const [body,proof] of [
    [body422,{}],
    [body422,{path:"messages"}],
    [body422,{path:"messages",rejectionClass:"arbitrary"}],
    [body422,{path:"session",rejectionClass:"prehandler"}],
    [{detail:"fake"},{path:"messages",rejectionClass:"prehandler"}],
    [{detail:[{type:"x",loc:["other"]}]},safePre],
    [{status:"error",code:"INVALID_TIME"},{}],
    [{status:"error",code:"INVALID_TIME"},{path:"messages",rejectionClass:"prehandler"}],
    [{code:"ACTION_UNCERTAIN"},safePre],
    [null,safePre],
  ] as const){
    const error=parseActionFailure(422,body,proof);
    assert.ok(!(error instanceof DefinitiveApiError),JSON.stringify([body,proof]));
    assert.equal(failureCategory(error),"unknown_rejection");
  }
});

test("MR-NEW-06: known safe domain refusal requires same-origin server proof",()=>{
  for(const code of ["INVALID_TIME","INVALID_VALUE"]) {
    const result=parseActionFailure(422,{status:"error",code,message:"Исправьте значение."},safeDevice);
    assert.ok(result instanceof DefinitiveApiError);
    assert.equal(failureCategory(result),"domain_refusal");
  }
  assert.equal(failureCategory(parseActionFailure(422,{status:"error",code:"INVALID_VALUE"},
    {path:"messages",rejectionClass:"domain"})),"unknown_rejection");
  assert.equal(failureCategory(parseActionFailure(409,{status:"error",code:"INVALID_TIME"},
    safeDevice)),"unknown_rejection");
});

test("MR-NEW-06: unknown outcome, auth and safety conflicts never masquerade as definitive",()=>{
  for(const [status,code,expected] of [
    [409,"RECOVERY_REQUIRED","recovery_required"],
    [409,"TIME_BACKWARDS","time_backwards"],
    [409,"IDEMPOTENCY_CONFLICT","idempotency_conflict"],
    [401,"SESSION_EXPIRED","authentication"],
    [403,"SESSION_READ_ONLY","authorization"],
    [429,"MESSAGE_LIMIT","rate_limited"],
    [500,"UPSTREAM_FAILURE","unknown_server"],
    [502,"UPSTREAM_UNAVAILABLE","unknown_server"],
  ] as const){
    const err=parseActionFailure(status,{status:"error",code}, {path:"messages"});
    assert.ok(err instanceof ApiError);
    assert.ok(!(err instanceof DefinitiveApiError));
    assert.equal(failureCategory(err),expected,code);
  }
  for(const code of ["ACTION_UNCERTAIN","ACTION_PARTIAL","ACTION_CONFLICT","ACTION_FAILED"]){
    const err=parseActionFailure(409,{status:"error",code,operation_id:"op-0001",
      confirmed_devices:code==="ACTION_PARTIAL"?["light"]:[],attempted_at:time});
    assert.ok(err instanceof ActionApiError);
    assert.equal(failureCategory(err),"action_"+code.slice("ACTION_".length).toLowerCase());
  }
  assert.equal(failureCategory(new DOMException("aborted","AbortError")),"transport_failure");
  assert.equal(failureCategory(new TypeError("Network failed")),"transport_failure");
  assert.equal(failureCategory(parseActionFailure(422,{detail:[{type:"x",loc:["body","text"]}]},{})),"unknown_rejection");
});

test("MR-NEW-06: secure marker never upgrades 500 or malformed action evidence",()=>{
  const err=parseActionFailure(500,body422,safePre);
  assert.ok(!(err instanceof DefinitiveApiError));
  assert.equal(failureCategory(err),"unknown_server");
  const malformed=parseActionFailure(409,{
    code:"ACTION_UNCERTAIN", operation_id:"op-0001",
    confirmed_devices:[], attempted_at:"not-iso",
  },{path:"messages",rejectionClass:"prehandler"});
  assert.ok(!(malformed instanceof ActionApiError));
  assert.equal(failureCategory(malformed),"unknown_rejection");
});
