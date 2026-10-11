-- Add persisted render progress to existing Supabase installations.
-- Safe to run even when the column was already added by the initial schema.
alter table public.video_projects
  add column if not exists progress_percent integer not null default 0
  check (progress_percent between 0 and 100);
