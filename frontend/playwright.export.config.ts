import { defineConfig } from "@playwright/test";
const python =
  process.env.MATILDA_TEST_PYTHON ||
  (process.platform === "win32"
    ? "../.venv/Scripts/python.exe"
    : "../.venv/bin/python");

export default defineConfig({
  testDir: "./lesson-harness/tests",
  testMatch: "export.spec.ts",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5174",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  webServer: [
    {
      command: `"${python}" -X utf8 ../backend/tests/studio_export_harness.py`,
      url: "http://127.0.0.1:8001/healthz",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command:
        "node node_modules/vite/bin/vite.js --config lesson-harness/vite.config.ts",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
