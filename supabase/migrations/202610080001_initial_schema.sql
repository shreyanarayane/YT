-- Run in the Supabase SQL Editor before deploying the API.
-- The FastAPI service uses its service-role key for all application writes;
-- browser clients use Supabase Auth only and never access these tables directly.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'Creator',
  role text not null default 'creator' check (role in ('creator', 'admin')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.seed_topics (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  topic text not null check (char_length(topic) between 1 and 255),
  created_at timestamptz not null default now(),
  unique (user_id, topic)
);

create table if not exists public.subscription_plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  price_paise integer not null check (price_paise >= 0),
  currency text not null default 'INR',
  interval_unit text not null default 'monthly' check (interval_unit in ('monthly', 'yearly')),
  razorpay_plan_id text unique,
  videos_per_month integer not null default 0 check (videos_per_month >= 0),
  max_duration_seconds integer not null default 60 check (max_duration_seconds >= 15),
  scheduled_posts_per_month integer not null default 0 check (scheduled_posts_per_month >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.user_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_id uuid not null references public.subscription_plans(id),
  razorpay_subscription_id text unique,
  razorpay_customer_id text,
  status text not null default 'created',
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_cycle_end boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.video_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  topic text not null,
  title text not null,
  description text not null default '',
  script text not null,
  voice text not null default 'en-US-GuyNeural',
  requested_duration_seconds integer,
  status text not null default 'draft',
  progress_percent integer not null default 0 check (progress_percent between 0 and 100),
  youtube_video_id text,
  privacy_status text not null default 'private',
  media_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.video_schedules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  video_project_id uuid not null references public.video_projects(id) on delete cascade,
  scheduled_for timestamptz not null,
  timezone text not null default 'Asia/Kolkata',
  privacy_status text not null default 'private',
  status text not null default 'scheduled',
  created_at timestamptz not null default now()
);

create table if not exists public.payment_webhook_events (
  id uuid primary key default gen_random_uuid(),
  provider_event_id text not null unique,
  event_type text not null,
  payload jsonb not null,
  processed_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  action text not null,
  target_type text,
  target_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists seed_topics_user_id_idx on public.seed_topics(user_id);
create index if not exists user_subscriptions_user_id_idx on public.user_subscriptions(user_id);
create index if not exists user_subscriptions_plan_id_idx on public.user_subscriptions(plan_id);
create index if not exists video_projects_user_created_idx on public.video_projects(user_id, created_at desc);
create index if not exists video_schedules_video_project_id_idx on public.video_schedules(video_project_id);
create index if not exists video_schedules_user_scheduled_idx on public.video_schedules(user_id, scheduled_for);
create index if not exists audit_logs_user_created_idx on public.audit_logs(user_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.seed_topics enable row level security;
alter table public.subscription_plans enable row level security;
alter table public.user_subscriptions enable row level security;
alter table public.video_projects enable row level security;
alter table public.video_schedules enable row level security;
alter table public.payment_webhook_events enable row level security;
alter table public.audit_logs enable row level security;

revoke all on all tables in schema public from anon, authenticated;

