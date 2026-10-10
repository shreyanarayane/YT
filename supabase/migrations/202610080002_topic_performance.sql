-- Per-user learning scores.  This replaces the old shared
-- backend/engine/youtube-agent/data/performance.json file.
create table if not exists public.topic_performance (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  topic text not null,
  score numeric not null default 0.5 check (score >= 0 and score <= 1),
  attempts integer not null default 0 check (attempts >= 0),
  last_stats jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, topic)
);

create index if not exists topic_performance_user_score_idx
  on public.topic_performance (user_id, score desc);

alter table public.topic_performance enable row level security;
revoke all on public.topic_performance from anon, authenticated;

