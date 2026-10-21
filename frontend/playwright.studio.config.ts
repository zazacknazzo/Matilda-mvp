import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const runtime = mkdtempSync(join(tmpdir(), "matilda-t05-"));
export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5176",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  webServer: [
    {
      command:
        "../.venv/bin/python -m uvicorn studio_e2e_app:app --app-dir ../backend/tests --host 127.0.0.1 --port 8016",
      url: "http://127.0.0.1:8016/api/health",
      reuseExistingServer: false,
      env: {
        PYTHONPATH: "../backend",
        MATILDA_DB: join(runtime, "test.db"),
        MATILDA_CACHE_TTL: "999999999",
        MATILDA_CORS_ORIGINS: "http://127.0.0.1:5176",
      },
    },
    {
      command:
        "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5176 --strictPort",
      url: "http://127.0.0.1:5176",
      reuseExistingServer: false,
      env: { MATILDA_API_PROXY: "http://127.0.0.1:8016" },
    },
  ],
});
