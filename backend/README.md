# Backend deployment

This directory contains the FastAPI service and the video-generation engine in
`engine/youtube-agent/`.

For Render, keep the repository root as the service root because the API is
imported as the `backend` Python package. Use:

- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health` (preferred). `HEAD /` is also accepted for platform probes.

Configure secrets and settings in Render's environment panel. At minimum,
provide `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_ENV=production`,
and `CORS_ALLOW_ORIGINS`. FastAPI verifies Supabase Auth sessions and uses the
service-role key only on the server for database writes; never place that key
in React or any browser build. The root `.env` is for local development only.

Apply the SQL files in `supabase/migrations/` through the Supabase SQL Editor
in order before deploying. For an existing database, run each new migration
even if an earlier schema file has already been applied. New customer data is stored through Supabase PostgREST;
SQLite is not part of the application data path.

For YouTube uploads, configure the server-only Google OAuth environment
variables documented in `PRODUCTION_SETUP.md`, apply
`supabase/migrations/202610110002_youtube_connections.sql`, and have each
creator connect their own channel in Settings. Refresh tokens are encrypted
before storage; never use the legacy shared `token.json` for web customers.

Video rendering is limited to one in-process build at a time and defaults to
720-pixel-wide output to reduce peak memory. Set `VIDEO_MAX_WIDTH` on the host
to a value such as `1080` only if the instance has enough RAM. Render progress
is now updated from MoviePy's encoder frame callback; builds with no heartbeat
for 15 minutes are marked failed rather than shown as rendering forever.
