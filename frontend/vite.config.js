import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  // Read the repository-root .env for local dev, but explicitly expose only
  // browser-safe values. Never prefix/expose all SUPABASE_* variables: that
  // would risk bundling SUPABASE_SERVICE_ROLE_KEY into the public app.
  const env = loadEnv(mode, path.resolve(here, '..'), '');
  const value = (key, fallback = '') => process.env[key] || env[key] || fallback;

  return {
    plugins: [react()],
    define: {
      __API_BASE_URL__: JSON.stringify(value('API_BASE_URL', 'http://127.0.0.1:8000')),
      __SUPABASE_URL__: JSON.stringify(value('SUPABASE_URL')),
      __SUPABASE_PUBLISHABLE_KEY__: JSON.stringify(value('SUPABASE_PUBLISHABLE_KEY')),
    },
  };
});
