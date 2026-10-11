-- Per-user YouTube OAuth connections. Refresh tokens are encrypted by the API
-- before storage; only the server service-role client can access this table.
create table if not exists public.youtube_connections (
  user_id uuid primary key references auth.users(id) on delete cascade,
  encrypted_refresh_token text not null,
  channel_id text,
  channel_title text,
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.youtube_connections enable row level security;
revoke all on public.youtube_connections from anon, authenticated;
