/** Actual Chromium + two real uvicorn processes + persistent SQLite store.
 * Browser reload must reattach with the SAME guest token and display actual
 * confirmed devices/history. No official provider calls or private data.
 */
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { chromium, expect } from "@playwright/test";

const root = resolve(process.cwd(), "..");
const tmp = mkdtempSync(join(tmpdir(), "sain-browser-persist-"));
const backendUrl = "http://127.0.0.1:8765";
const clientUrl = "http://127.0.0.1:4173";
const env = { ...process.env, SAIN_DEMO_STATE_DB: join(tmp, "demo.sqlite3"), SAIN_CI: "1" };
delete env.SAIN_DEMO_CRASH_PROBE;
const procs = [];
let browser;

const start = (args, cwd = root) => {
  const child = spawn(process.env.SAIN_PYTHON || "python", args, {
    cwd, env, stdio: ["ignore", "ignore", "pipe"],
  });
  let errors = "";
  child.stderr.on("data", (buf) => { errors = (errors + String(buf)).slice(-3000); });
  child.failureContext = () => errors;
  procs.push(child);
  return child;
};
async function ready(url, child) {
  for (let i = 0; i < 140; i++) {
    if (child.exitCode !== null) throw new Error("Server exited: " + child.failureContext());
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(550) });
      if (response.ok) return;
    } catch (_) { /* transient local connection refusal */ }
    await delay(170);
  }
  throw new Error("Server not ready: " + url + "\n" + child.failureContext());
}
async function stop(child, force = false) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const end = new Promise((resolveEnd) => child.once("exit", resolveEnd));
  child.kill(force ? "SIGKILL" : "SIGTERM");
  await Promise.race([end, delay(6000)]);
  if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
}
async function issueGuest() {
  const response = await fetch(backendUrl + "/api/v1/sessions", {
    method: "POST",
    headers: { Authorization: "Bearer offline-team", "Content-Type": "application/json" },
    body: JSON.stringify({ source: "dev", stay_id: "stay_test" }),
  });
  if (response.status !== 201) throw new Error("Cannot issue synthetic guest " + response.status);
  return (await response.json()).session_token;
}
async function attach(page, token) {
  await page.goto(clientUrl);
  await page.getByLabel("Временный токен гостя").fill(token);
  await page.getByRole("button", { name: "Подключиться", exact: true }).click();
  await expect(page.getByRole("button", { name: "Заселиться" })).toBeVisible();
}
async function go(page, label) {
  await page.getByRole("button", { name: "Меню" }).click();
  await page.getByRole("navigation").getByRole("button", { name: label, exact: true }).click();
}
const climate = (page) => page.locator(".device").filter({ hasText: "Климат" });
try {
  let backend = start(["-m", "scripts.rehearse_client"]);
  await ready(backendUrl + "/health", backend);
  const frontend = start(["frontend/serve.py", "--mode", "rehearsal"]);
  await ready(clientUrl, frontend);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  const token = await issueGuest();
  await attach(page, token);
  await page.getByRole("button", { name: "Заселиться" }).click();
  await page.getByText("В номер", { exact: true }).click();
  await climate(page).click();
  await page.getByRole("spinbutton").fill("21");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(climate(page)).toContainText("21 °C");
  await go(page, "Диалог");
  await page.getByRole("button", { name: "Сделай попрохладнее" }).click();
  await expect(climate(page)).toContainText("20 °C");
  const before = await (await fetch(backendUrl + "/api/v1/session", {
    headers: { Authorization: "Bearer " + token },
  })).json();
  if (before.history.length < 2) throw new Error("Missing confirmed guest history");

  // Real forced process exit, new operating-system process, same unchanged token.
  await stop(backend, true);
  backend = start(["-m", "scripts.rehearse_client"]);
  await ready(backendUrl + "/health", backend);
  await page.reload(); // Browser must explicitly reattach; no token is stored.
  await attach(page, token);
  await go(page, "Мой номер");
  await expect(climate(page)).toContainText("20 °C");
  await go(page, "Диалог");
  await page.getByRole("button", { name: "Диалог · История сообщений" }).click();
  await expect(page.locator(".exchange")).toHaveCount(before.history.length);
  await page.screenshot({ path: join(root, "frontend", "evidence", "persistence-reopened.png"), fullPage: true });

  // Browser switch to another token cannot inherit first guest's settings.
  const nextToken = await issueGuest();
  await go(page, "Сменить сеанс");
  await attach(page, nextToken);
  await go(page, "Мой номер");
  await expect(climate(page)).not.toContainText("20 °C");
  console.log("BROWSER_PERSISTENCE: PASS — actual Chromium, forced backend exit, same guest token, restored climate/history, guest isolation");
} finally {
  if (browser) await browser.close();
  for (const proc of procs.reverse()) await stop(proc, true);
  rmSync(tmp, { recursive: true, force: true });
}
