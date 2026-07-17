import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: `http://${env.VITE_BACKEND_HOST || "localhost"}:8000`,
          changeOrigin: true,
        },
      },
    },
  };
});