import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '#': path.resolve(__dirname, './src'),
    },
  },
  root: "src",
  define: {
    'process.env': {
      LLM_EVALUATOR_API_BASE_URL: 'http://localhost:8887/api/v1/e'
    }
  }
});