import { defineConfig } from "@playwright/test";
const webkit = process.env.SAIN_BROWSER === "webkit";
const firefox = process.env.SAIN_BROWSER === "firefox";
export default defineConfig({
  testDir: "tests",
  testMatch: "**/*.spec.ts",
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 375, height: 812 },
    browserName: webkit ? "webkit" : firefox ? "firefox" : "chromium",
    permissions: firefox || webkit ? [] : ["microphone"],
    launchOptions: webkit
      ? {}
      : firefox
        ? {
            firefoxUserPrefs: {
              "media.navigator.streams.fake": true,
              "media.navigator.permission.disabled": true,
            },
          }
        : {
            executablePath: process.env.CHROMIUM_PATH || undefined,
            args: [
              "--use-fake-device-for-media-stream",
              "--use-fake-ui-for-media-stream",
            ],
          },
  },
  webServer: [
    {
      command: "cd .. && python -m scripts.rehearse_client",
      // Chromium and Firefox are separate test suites. Their synthetic guest
      // tokens must not persist into each other's finite 8-session fixture.
      // Cross-process durability is independently tested with a stable DB.
      env: { SAIN_DEMO_STATE_DB: firefox
        ? ".runtime/playwright-firefox.sqlite3"
        : ".runtime/playwright-chromium.sqlite3" },
      url: "http://127.0.0.1:8765/health",
      reuseExistingServer: false,
    },
    {
      command: "python serve.py --mode rehearsal",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: false,
    },
  ],
});
