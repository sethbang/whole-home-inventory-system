/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Separate from vite.config.ts: that file reads HTTPS certs at module-load
// time for the dev server, which isn't appropriate for the test runner.
// We only need React support + a jsdom test env here.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    globals: true,
    css: false,
    include: ['src/**/__tests__/**/*.test.{ts,tsx,js,jsx}'],
  },
});
