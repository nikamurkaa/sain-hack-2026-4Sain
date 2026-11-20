import { defineConfig } from "@playwright/test";
const firefox = process.env.SAIN_BROWSER === "firefox";
export default defineConfig({
  testDir: "tests",
  testMatch: "**/*.spec.ts",
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 375, height: 812 },
    browserName: firefox ? "firefox" : "chromium",
    permissions: firefox ? [] : ["microphone"],
    launchOptions: firefox
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
