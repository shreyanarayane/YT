# Creator Studio web app

The Vercel frontend is a React + Vite single-page app. The previous Flutter
sources remain in `lib/` and the platform folders as a rollback/reference; they
are not used by the Vercel build.

## Local development

From this directory, install packages and start the app:

```powershell
npm install
npm run dev
```

The Vite config reads `API_BASE_URL`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY` from the repository-root `.env` for local builds. If
you still use Supabase's legacy public `SUPABASE_ANON_KEY` variable, it is
accepted as a fallback.
The API URL defaults to `http://127.0.0.1:8000`. Only these three public values
are embedded in the browser build; the Supabase service-role key is never
exposed.

## Vercel

- Root Directory: `frontend`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`

Add `API_BASE_URL` (your Render API URL), `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY` as Vercel Project Environment Variables, then
redeploy. Do not add `SUPABASE_SERVICE_ROLE_KEY` or other server secrets to
Vercel.

## Production build

```powershell
npm run build
```

The built site is written to `dist/`.
