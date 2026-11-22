import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, client } from "../src/api.ts";

test("HTTP 409 displays specific safe server guidance", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(
    JSON.stringify({ code: "SESSION_READ_ONLY", message: "В этом сеансе управление недоступно." }),
    { status: 409, headers: { "Content-Type": "application/json" } }
  );
  try {
    await assert.rejects(client("synthetic", new AbortController().signal)("messages"),
      (error: unknown) => error instanceof ApiError &&
        error.status === 409 && error.message.includes("управление недоступно"));
  } finally { globalThis.fetch = previous; }
});
test("secrets and internal URLs in error responses are never reflected", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(
    JSON.stringify({ message: "Bearer synthetic at https://private.invalid" }),
    { status: 403 }
  );
  try {
    await assert.rejects(client("synthetic", new AbortController().signal)("state"),
      (error: unknown) => error instanceof ApiError && error.message === "Нет доступа к этой операции.");
  } finally { globalThis.fetch = previous; }
});
