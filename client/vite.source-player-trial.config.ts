import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

// Separate interactive entry. No default app config, proxy or dotenv.
export default defineConfig({
  envDir: false,
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5178, strictPort: true },
  preview: { host: '127.0.0.1', port: 5178, strictPort: true },
  build: {
    outDir: 'dist-source-player-trial',
    rollupOptions: { input: fileURLToPath(new URL('./source-player-trial.html', import.meta.url)) },
  },
});
