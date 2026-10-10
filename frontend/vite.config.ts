import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.VITE_PROXY_TARGET || 'http://localhost:8000';
  return {
    plugins: [react()],
    resolve: { alias: { '@': path.resolve(__dirname, './src') } },
    // Fire TV WebViews are Chromium-based but can lag behind desktop — keep output conservative.
    build: { target: ['es2019', 'chrome80'], sourcemap: false, chunkSizeWarningLimit: 900 },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/mcp': { target, changeOrigin: true },
      },
    },
  };
});
