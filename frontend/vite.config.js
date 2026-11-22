import { defineConfig } from "vite";
const target = process.env.SAIN_API_ORIGIN || "http://127.0.0.1:8000";
const proxy = { "/api/v1": { target, changeOrigin: true, secure: true } };
export default defineConfig({
  server: { host: "127.0.0.1", proxy },
  preview: { host: "127.0.0.1", proxy },
});
