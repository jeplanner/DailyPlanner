-- ============================================================
--  DailyPlanner — LOCK DOWN every public table with RLS.
--
--  Context: the publishable/anon Supabase key was committed to
--  public git history. Without RLS, that key grants anyone on
--  the internet full read access to every table — including
--  user_google_tokens (OAuth refresh tokens).
--
--  This migration enables Row Level Security on every table in
--  schema `public` AND adds NO policies. With RLS on and zero
--  policies, anon/publishable keys see nothing; only requests
--  authenticated with the service_role key (used by the Flask
--  backend) can read or write.
--
--  Architecture note: this app's Flask backend is the ONLY
--  client of Supabase — no browser code talks to PostgREST
--  directly. So locking the anon key out of everything is the
--  correct posture. The backend must use SUPABASE_KEY set to a
--  service_role key (kept in env vars, never committed).
--
--  Safe to re-run: enabling RLS on a table that already has it
--  is a no-op.
-- ============================================================

do $$
declare
  t text;
begin
  for t in
    select tablename
    from pg_tables
    where schemaname = 'public'
  loop
    execute format('alter table public.%I enable row level security', t);
    raise notice 'RLS enabled on public.%', t;
  end loop;
end $$;

-- Verification query — run after the block above. Every row
-- should show rowsecurity = true. Any row showing false means
-- a new table was added since this migration; re-run it.
--
--   select schemaname, tablename, rowsecurity
--   from pg_tables
--   where schemaname = 'public'
--   order by tablename;
