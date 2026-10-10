# Production architecture

## Responsibility boundaries

```text
React + Vite web client
  -> Supabase Auth: sign-up, sign-in, session refresh
  -> FastAPI API: authenticated application requests only
       -> Supabase Postgres: tenant data and audit records
       -> Razorpay: hosted checkout and signed webhooks
       -> Render worker: TTS, MoviePy/FFmpeg, Pexels, YouTube upload
```

The browser client contains only the Supabase project URL and publishable key. It never
receives a database password, Supabase service key, Razorpay secret, Pexels
key, Google OAuth refresh token, or YouTube client secret.

## FastAPI responsibilities

FastAPI is required for privileged work that must not run in the browser:

- verifies Supabase access tokens and resolves the current user
- checks plan limits before starting any render or schedule
- creates Razorpay subscriptions and verifies Razorpay webhook signatures
- encrypts and uses per-user YouTube OAuth refresh tokens
- starts and monitors background rendering/upload jobs
- writes audit records and applies admin-only actions

Only `/health`, Supabase sign-in endpoints, and the signed Razorpay webhook are
public. Every other API route requires a valid user session; administrator
routes require an application role checked on the server.

## Database safety rule

Supabase Postgres is the canonical application database. FastAPI uses the
server-only service-role key with Supabase PostgREST for database operations;
Flutter never receives that key or connects with a database password. Do not
reconnect the legacy integer-ID SQLAlchemy models to the Supabase tables: user
ownership is based on Supabase Auth UUIDs. Existing local SQLite files are not
read or migrated automatically.

## Deployable services

1. **Web**: React + Vite static bundle behind HTTPS.
2. **API**: FastAPI, stateless, with strict CORS and environment-only secrets.
3. **Worker**: a separate Python worker/container for MoviePy/FFmpeg, TTS and
   scheduled YouTube publishing. Do not run long renders in an HTTP request.
4. **Supabase**: Auth, Postgres, and Storage for generated media metadata.
5. **Razorpay**: hosted recurring checkout; webhooks enter FastAPI only.

## Migration order

1. Supabase Auth is integrated with the browser client; FastAPI validates its access token.
2. Supabase Postgres/PostgREST is the canonical database, with UUID ownership
   linked to `auth.users` and schema managed by the SQL migrations.
3. Move generated media to private Supabase Storage with owner-specific access.
4. Introduce a queue-backed worker and schedule runner.
5. Enable real Razorpay plans only after webhook and entitlement tests pass.
