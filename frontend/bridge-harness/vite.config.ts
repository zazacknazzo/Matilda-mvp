import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  cacheDir: "../node_modules/.vite-bridge",
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5177,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8017" },
    fs: { allow: [fileURLToPath(new URL("../..", import.meta.url))] },
  },
});
