import { defineConfig } from "@playwright/test";
const python =
  process.env.MATILDA_TEST_PYTHON ||
  (process.platform === "win32"
    ? "../.venv/Scripts/python.exe"
    : "../.venv/bin/python");
export default defineConfig({
  testDir: "./generation-harness/tests",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  webServer: [
    {
      command: `"${python}" -X utf8 ../backend/tests/generation_harness.py`,
      url: "http://127.0.0.1:8017/test/stats",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command:
        "node node_modules/vite/bin/vite.js --config generation-harness/vite.config.ts",
      url: "http://127.0.0.1:5177",
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
