# India SaaS foundation

The backend now supports Razorpay subscription records, signed Razorpay webhooks,
role-protected plan administration, per-user video ownership, and plan gates.
It is deliberately configured with subscription enforcement off until test-mode
checkout and webhooks have been verified.

## First administrator

In PowerShell, set the bootstrap variables for the process that starts Uvicorn:

```powershell
$env:ADMIN_BOOTSTRAP_USERNAME = "owner"
$env:ADMIN_BOOTSTRAP_EMAIL = "owner@example.com"
$env:ADMIN_BOOTSTRAP_PASSWORD = "use-a-long-unique-password"
```

Start the backend once, sign in with that account, then remove the bootstrap
password from your environment. The application stores only its password hash.
Do not use the former `admin/admin123` or demo credentials.

## Razorpay test mode

1. Set Razorpay **test-mode** `RAZORPAY_KEY_ID` (`rzp_test_...`) and
  `RAZORPAY_KEY_SECRET` in Render. The plan initializer rejects live keys.
2. Sign in with an administrator account and open **Plan & billing**. Select
  **Set up test plans** to create Starter (₹199), Creator (₹499), and Studio
  (₹1,499) monthly plans, along with their app-side limits and Razorpay IDs.
3. Enable the recurring payment methods supported by your Razorpay account in
  its dashboard. Razorpay Checkout displays only methods eligible for that
  account and customer; the app never collects payment details.
4. Add `POST /api/billing/webhooks/razorpay` as a Razorpay test-mode webhook
  and set its secret as `RAZORPAY_WEBHOOK_SECRET` in Render.
5. Subscribe from the billing page and complete a Razorpay test checkout.
6. Confirm Razorpay sends an authenticated webhook, then set
   `BILLING_ENFORCE_SUBSCRIPTIONS=true`.

Never put Razorpay secrets, JWT secrets, Google OAuth secrets, or payment data
in Flutter code or Git. Razorpay hosts checkout, so the application never
handles card or UPI details.

## Before enabling automatic publishing

Scheduled posting records are stored, but a production scheduler and encrypted,
per-user Google OAuth token vault are still required before any automated
uploads are enabled. Do not use the current single `backend/engine/youtube-agent/token.json`
for customer accounts: it belongs to one Google account and is not multi-tenant.

Deploy with PostgreSQL, HTTPS, a worker queue, an encrypted secret store,
restricted CORS origins, backups, monitoring, and a privacy/deletion policy.

## Supabase Postgres

Supabase Postgres is the only application database. FastAPI accesses it through
Supabase PostgREST using `SUPABASE_URL` and the server-only
`SUPABASE_SERVICE_ROLE_KEY`; the database password and `DATABASE_URL` are not
used. Apply the SQL files in `supabase/migrations/` before starting the API.
The service health endpoint checks the Supabase `video_projects` table. Existing
local SQLite files are left untouched, but are no longer read or written by
the application and are not migrated automatically.

## Deployment folders

- **Render backend:** use the repository root as the service root. Build with
  `pip install -r backend/requirements.txt` and start with
  `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Set the Render health
  check path to `/health` (the API also answers `HEAD /` for platform probes).
- **Vercel frontend:** set the project root directory to `frontend`, framework
  preset to Vite, install command to `npm ci`, build command to `npm run build`,
  and output directory to `dist`. Add `API_BASE_URL` (your Render API URL),
  `SUPABASE_URL`, and `SUPABASE_PUBLISHABLE_KEY` as Vercel project environment
  variables (`SUPABASE_ANON_KEY` is accepted as a public-key fallback). Never
  pass the Supabase service-role key to the frontend build.
- Set `CORS_ALLOW_ORIGINS` on Render to the comma-separated Vercel site origins
  (for example, the production domain and any preview domain you intentionally
  allow). Production defaults to no browser origins when this is unset.
- Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and the bootstrap admin
  values as Render environment variables. Remove the bootstrap password after
  the first administrator is created.

The API and video-generation engine are together under `backend/`; the React +
Vite web app is under `frontend/` (legacy Flutter sources remain there but are
not part of the Vercel build). The root `.env` is for local development only;
configure Vercel environment variables in its project settings instead.
