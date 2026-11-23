import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

// Execute actual TSX with controlled React hooks, fetch().blob() and Audio.play().
// No real credentials, external services, or microphone are required.
const here = path.dirname(fileURLToPath(import.meta.url));
const original = readFileSync(path.resolve(here, "../src/SpeechReply.tsx"), "utf8");
const js = ts.transpileModule(original, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
}).outputText;

function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: Error) => void;
  const promise = new Promise<T>((ok, no) => { resolve = ok; reject = no; });
  return { promise, resolve, reject };
}

function harness(latePlay = false) {
  let pos = 0, cleanup: (() => void) | undefined, deps: unknown[] | undefined, guest = "A";
  const slots: any[] = [], events: string[] = [];
  const blobs: ReturnType<typeof deferred<Blob>>[] = [];
  const plays: string[] = [], urls: string[] = [], revoked: string[] = [], signals: AbortSignal[] = [];
  const playPromises: ReturnType<typeof deferred<void>>[] = [];
  let pauses = 0;
  const hooks = {
    useState(value: unknown) {
      const id = pos++;
      if (!(id in slots)) slots[id] = value;
      return [slots[id], (next: any) => {
        slots[id] = typeof next === "function" ? next(slots[id]) : next;
        events.push(guest + ":" + String(slots[id]));
      }];
    },
    useRef(value: unknown) {
      const id = pos++;
      if (!(id in slots)) slots[id] = { current: value };
      return slots[id];
    },
    useEffect(effect: () => (() => void) | undefined, next: unknown[]) {
      pos++;
      if (!deps || next.some((item, i) => item !== deps?.[i])) {
        cleanup?.();
        cleanup = effect();
        deps = next;
      }
    },
  };
  const node = (type: string, props: Record<string, any>) => ({ type, props });
  const sandbox = {
    exports: {} as Record<string, any>,
    require: (name: string) => name === "react" ? hooks : { jsx: node, jsxs: node },
    URL: {
      createObjectURL: (_blob: Blob) => { const name = "blob:test-" + (urls.length + 1); urls.push(name); return name; },
      revokeObjectURL: (name: string) => { revoked.push(name); },
    },
    Audio: class {
      currentTime = 0; duration = 100; muted = false; preload = "";
      onpause: (() => void) | null = null; onended: (() => void) | null = null;
      src: string;
      constructor(src: string) { this.src = src; }
      play() {
        plays.push(guest);
        if (latePlay) { const d = deferred<void>(); playPromises.push(d); return d.promise; }
        return Promise.resolve();
      }
      pause() { pauses++; this.onpause?.(); }
    },
    AbortController, AbortSignal, Promise, Error, console,
    fetch: async (_url: string, options: { signal: AbortSignal }) => {
      signals.push(options.signal);
      const d = deferred<Blob>(); blobs.push(d);
      return { ok: true, headers: { get: () => "audio/mpeg" }, blob: () => d.promise };
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  const SpeechReply = sandbox.exports.SpeechReply;
  function render(id: string, replyIndex = 0) {
    pos = 0; guest = id;
    return SpeechReply({ token: "guest-" + id, replyIndex });
  }
  function firstButton(tree: any) {
    const found: any[] = [];
    function visit(el: any) {
      if (!el || typeof el !== "object") return;
      if (el.type === "button") found.push(el);
      const kids = el.props?.children;
      if (Array.isArray(kids)) kids.forEach(visit); else visit(kids);
    }
    visit(tree);
    return found[0];
  }
  async function tick() { for (let i = 0; i < 16; i++) await Promise.resolve(); }
  return { render, firstButton, tick, unmount: () => cleanup?.(), blobs, plays, urls, revoked,
    signals, playPromises, events, get status() { return slots[0]; }, get pauses() { return pauses; } };
}

test("P1: late blob from guest A never plays for guest B; B can play its own reply", async () => {
  const h = harness();
  h.firstButton(h.render("A")).props.onClick();
  await h.tick();
  assert.equal(h.blobs.length, 1);
  h.render("B");
  assert.equal(h.signals[0].aborted, true);
  h.blobs[0].resolve({ size: 500 } as Blob);
  await h.tick();
  assert.deepEqual(h.plays, []);
  assert.deepEqual(h.urls, []);
  assert.equal(h.status, "idle");
  h.firstButton(h.render("B")).props.onClick();
  await h.tick();
  h.blobs[1].resolve({ size: 500 } as Blob);
  await h.tick();
  assert.deepEqual(h.plays, ["B"]);
  assert.equal(h.status, "playing");
  h.unmount();
  assert.deepEqual(h.revoked, h.urls);
});

test("P1: changing replyIndex invalidates pending blob without creating audio", async () => {
  const h = harness();
  h.firstButton(h.render("A", 0)).props.onClick();
  await h.tick();
  h.render("A", 1);
  h.blobs[0].resolve({ size: 500 } as Blob);
  await h.tick();
  assert.equal(h.plays.length, 0);
  assert.equal(h.urls.length, 0);
  assert.equal(h.status, "idle");
});

test("P1: pending Audio.play completion cannot change UI of another guest", async () => {
  const h = harness(true);
  h.firstButton(h.render("A")).props.onClick();
  await h.tick();
  h.blobs[0].resolve({ size: 500 } as Blob);
  await h.tick();
  assert.deepEqual(h.plays, ["A"]);
  h.render("B");
  const before = h.events.length;
  h.playPromises[0].resolve();
  await h.tick();
  assert.equal(h.status, "idle");
  assert.equal(h.events.length, before);
  assert.ok(h.pauses > 0);
  assert.deepEqual(h.revoked, h.urls);
});

test("P1: unmounted voice response cannot update UI from late rejected blob", async () => {
  const h = harness();
  h.firstButton(h.render("A")).props.onClick();
  await h.tick();
  h.unmount();
  const before = h.events.length;
  h.blobs[0].reject(new Error("late failure"));
  await h.tick();
  assert.equal(h.events.length, before);
  assert.deepEqual(h.plays, []);
});
