-- ============================================================
--  DailyPlanner — TASKS BUCKET
--
--  A frictionless inbox for quickly captured thoughts. Users dictate
--  or type a one-liner; the in-app classifier (no external LLM) tags
--  it with one of: Health, Grocery, Portfolio, Checklist, TravelReads,
--  ProjectTask. For simple destination schemas (Grocery, Checklist),
--  the row is also routed into the destination module so the user can
--  act on it from there.
--
--  Classifier:
--    Multinomial Naive Bayes built on the fly from example sentences
--    in `tasks_bucket_examples`. Global seed rows ship with the app;
--    the user's past classifications (and manual reclassifications)
--    are appended as `source = 'user'` so the model adapts to the
--    user's vocabulary over time.
--
--  Tables:
--    tasks_bucket           — captured items + classifier output
--    tasks_bucket_examples  — labelled training sentences (global seeds
--                             + per-user history). Used as the corpus
--                             for the in-memory Naive Bayes model.
--    tasks_bucket_stats     — daily counters for the gamification strip
--
--  Soft-delete only — see project convention (memory: no-hard-delete).
--  Removed items set is_deleted = true / status = 'closed'; the rows
--  stay so analytics and undo remain possible.
--
--  Safe to re-run.
-- ============================================================

create extension if not exists pgcrypto;

-- ── tasks_bucket ────────────────────────────────────────────
create table if not exists tasks_bucket (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null,
  raw_text            text not null,
  category            text,                       -- null until classified
  confidence          numeric default 0,
  matched_keywords    jsonb default '[]'::jsonb,  -- explanation: tokens that drove the call
  status              text not null default 'pending',  -- pending|classified|unclassified|closed
  manual_override     boolean default false,
  destination_table   text,                       -- 'groceries' | 'checklist_items' | null
  destination_id      uuid,
  position            int default 0,
  classified_at       timestamptz,
  closed_at           timestamptz,
  is_deleted          boolean default false,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

create index if not exists tasks_bucket_user_active_idx
  on tasks_bucket (user_id, position, created_at desc)
  where is_deleted = false and status <> 'closed';

create index if not exists tasks_bucket_user_dest_idx
  on tasks_bucket (user_id, destination_table, destination_id)
  where destination_table is not null;

create or replace function _tasks_bucket_touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists tasks_bucket_touch_updated_at on tasks_bucket;
create trigger tasks_bucket_touch_updated_at
  before update on tasks_bucket
  for each row execute function _tasks_bucket_touch_updated_at();


-- ── tasks_bucket_examples ───────────────────────────────────
-- Training corpus for the Naive Bayes classifier.
--   user_id NULL  → global seed example (shared across users)
--   user_id set   → user's own past classification (learned)
--   source        → 'seed' or 'user' for diagnostics
create table if not exists tasks_bucket_examples (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid,
  category    text not null,
  text        text not null,
  source      text not null default 'user',
  created_at  timestamptz default now()
);

create index if not exists tasks_bucket_examples_lookup_idx
  on tasks_bucket_examples (user_id, category);


-- ── tasks_bucket_stats (gamification) ───────────────────────
create table if not exists tasks_bucket_stats (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null,
  stat_date   date not null,
  captured    int not null default 0,
  classified  int not null default 0,
  closed      int not null default 0,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create unique index if not exists tasks_bucket_stats_uniq
  on tasks_bucket_stats (user_id, stat_date);

drop trigger if exists tasks_bucket_stats_touch_updated_at on tasks_bucket_stats;
create trigger tasks_bucket_stats_touch_updated_at
  before update on tasks_bucket_stats
  for each row execute function _tasks_bucket_touch_updated_at();


-- ============================================================
--  Seed example sentences for the classifier.
--
--  Whole sentences (not single keywords) so the Naive Bayes model
--  picks up phrasing patterns ("buy X", "watch Y", "pay Z bill").
--  De-duplicated by (category, text) — re-running the migration is
--  safe because the unique index below makes the inserts idempotent.
-- ============================================================

create unique index if not exists tasks_bucket_examples_seed_uniq
  on tasks_bucket_examples (category, text)
  where user_id is null;

-- Health
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'Health', 'seed', 'go for a 30 minute walk'),
  (null, 'Health', 'seed', 'morning run before work'),
  (null, 'Health', 'seed', 'gym session legs day'),
  (null, 'Health', 'seed', 'book a doctor appointment'),
  (null, 'Health', 'seed', 'dentist checkup next month'),
  (null, 'Health', 'seed', 'meditate for 10 minutes'),
  (null, 'Health', 'seed', 'drink more water today'),
  (null, 'Health', 'seed', 'take vitamin d pills'),
  (null, 'Health', 'seed', 'check blood pressure'),
  (null, 'Health', 'seed', 'cardio workout in the evening'),
  (null, 'Health', 'seed', 'yoga stretches before bed'),
  (null, 'Health', 'seed', 'sleep before 11pm tonight'),
  (null, 'Health', 'seed', 'physio session for shoulder'),
  (null, 'Health', 'seed', 'intermittent fasting today'),
  (null, 'Health', 'seed', 'log weight this morning'),
  (null, 'Health', 'seed', 'cholesterol test next week'),
  (null, 'Health', 'seed', 'walk 10000 steps'),
  (null, 'Health', 'seed', 'breathing exercises'),
  (null, 'Health', 'seed', 'cut sugar from diet')
on conflict do nothing;

-- Grocery
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'Grocery', 'seed', 'buy milk and eggs'),
  (null, 'Grocery', 'seed', 'pick up bread on the way home'),
  (null, 'Grocery', 'seed', 'order rice and dal'),
  (null, 'Grocery', 'seed', 'tomatoes onions and ginger'),
  (null, 'Grocery', 'seed', 'fresh fruits from the supermarket'),
  (null, 'Grocery', 'seed', 'costco run this weekend'),
  (null, 'Grocery', 'seed', 'restock cooking oil'),
  (null, 'Grocery', 'seed', 'paneer and curd'),
  (null, 'Grocery', 'seed', 'chocolate for kids'),
  (null, 'Grocery', 'seed', 'wheat flour atta'),
  (null, 'Grocery', 'seed', 'bananas and apples'),
  (null, 'Grocery', 'seed', 'butter and cheese'),
  (null, 'Grocery', 'seed', 'spices masala for sambar'),
  (null, 'Grocery', 'seed', 'walmart pickup tomorrow'),
  (null, 'Grocery', 'seed', 'add to grocery list'),
  (null, 'Grocery', 'seed', 'frozen vegetables'),
  (null, 'Grocery', 'seed', 'snacks for the week'),
  (null, 'Grocery', 'seed', 'yogurt and berries')
on conflict do nothing;

-- Portfolio
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'Portfolio', 'seed', 'rebalance the equity portfolio'),
  (null, 'Portfolio', 'seed', 'review monthly sip allocations'),
  (null, 'Portfolio', 'seed', 'buy nifty index etf'),
  (null, 'Portfolio', 'seed', 'check dividend received'),
  (null, 'Portfolio', 'seed', 'open a new demat account'),
  (null, 'Portfolio', 'seed', 'review zerodha holdings'),
  (null, 'Portfolio', 'seed', 'top up ppf account'),
  (null, 'Portfolio', 'seed', 'fixed deposit maturity next week'),
  (null, 'Portfolio', 'seed', 'sell underperforming stocks'),
  (null, 'Portfolio', 'seed', 'bitcoin allocation'),
  (null, 'Portfolio', 'seed', 'roth ira contribution'),
  (null, 'Portfolio', 'seed', 'review 401k contributions'),
  (null, 'Portfolio', 'seed', 'mutual fund switch'),
  (null, 'Portfolio', 'seed', 'check broker statement'),
  (null, 'Portfolio', 'seed', 'invest in bonds'),
  (null, 'Portfolio', 'seed', 'rebalancing sector weights'),
  (null, 'Portfolio', 'seed', 'sukanya samriddhi yojana annual deposit'),
  (null, 'Portfolio', 'seed', 'nps tier 1 contribution')
on conflict do nothing;

-- Checklist (daily life action items / chores / errands)
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'Checklist', 'seed', 'call mom this evening'),
  (null, 'Checklist', 'seed', 'reply to email from manager'),
  (null, 'Checklist', 'seed', 'pay electricity bill before friday'),
  (null, 'Checklist', 'seed', 'recharge mobile plan'),
  (null, 'Checklist', 'seed', 'submit tax documents'),
  (null, 'Checklist', 'seed', 'renew car insurance'),
  (null, 'Checklist', 'seed', 'mortgage payment due'),
  (null, 'Checklist', 'seed', 'send reminder to vendor'),
  (null, 'Checklist', 'seed', 'follow up with school'),
  (null, 'Checklist', 'seed', 'schedule team meeting'),
  (null, 'Checklist', 'seed', 'doctor appointment confirmation call'),
  (null, 'Checklist', 'seed', 'pick up dry cleaning'),
  (null, 'Checklist', 'seed', 'water the plants'),
  (null, 'Checklist', 'seed', 'pay rent on the first'),
  (null, 'Checklist', 'seed', 'change passwords'),
  (null, 'Checklist', 'seed', 'book flight tickets'),
  (null, 'Checklist', 'seed', 'send birthday card to dad'),
  (null, 'Checklist', 'seed', 'school pickup at 3pm')
on conflict do nothing;

-- TravelReads (queued things to watch / read / listen)
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'TravelReads', 'seed', 'watch this youtube video later'),
  (null, 'TravelReads', 'seed', 'read the latest essay on substack'),
  (null, 'TravelReads', 'seed', 'listen to lex fridman podcast'),
  (null, 'TravelReads', 'seed', 'finish the kindle book'),
  (null, 'TravelReads', 'seed', 'documentary about cosmos'),
  (null, 'TravelReads', 'seed', 'newsletter from morning brew'),
  (null, 'TravelReads', 'seed', 'hbr article on leadership'),
  (null, 'TravelReads', 'seed', 'audiobook for the commute'),
  (null, 'TravelReads', 'seed', 'tutorial on system design'),
  (null, 'TravelReads', 'seed', 'whitepaper on llm scaling'),
  (null, 'TravelReads', 'seed', 'movie recommendation from a friend'),
  (null, 'TravelReads', 'seed', 'series finale to watch'),
  (null, 'TravelReads', 'seed', 'blog post bookmarked'),
  (null, 'TravelReads', 'seed', 'lecture on quantum computing'),
  (null, 'TravelReads', 'seed', 'paper on cancer immunotherapy')
on conflict do nothing;

-- ProjectTask (build / ship / refactor / engineering work items)
insert into tasks_bucket_examples (user_id, category, source, text) values
  (null, 'ProjectTask', 'seed', 'fix login bug on mobile'),
  (null, 'ProjectTask', 'seed', 'refactor the user service'),
  (null, 'ProjectTask', 'seed', 'design the new dashboard'),
  (null, 'ProjectTask', 'seed', 'write spec for billing flow'),
  (null, 'ProjectTask', 'seed', 'implement the search feature'),
  (null, 'ProjectTask', 'seed', 'deploy to production'),
  (null, 'ProjectTask', 'seed', 'open a pr for the migration'),
  (null, 'ProjectTask', 'seed', 'merge main into feature branch'),
  (null, 'ProjectTask', 'seed', 'launch the new pricing page'),
  (null, 'ProjectTask', 'seed', 'rollout feature flag to 50 percent'),
  (null, 'ProjectTask', 'seed', 'sprint planning notes'),
  (null, 'ProjectTask', 'seed', 'jira ticket for retry logic'),
  (null, 'ProjectTask', 'seed', 'standup blockers to mention'),
  (null, 'ProjectTask', 'seed', 'milestone review with leads'),
  (null, 'ProjectTask', 'seed', 'kickoff for analytics revamp'),
  (null, 'ProjectTask', 'seed', 'document the api endpoints'),
  (null, 'ProjectTask', 'seed', 'write tests for the parser')
on conflict do nothing;
