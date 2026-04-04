# DailyPlanner — Setup Guide for New Instance

Complete step-by-step instructions to deploy your own instance of DailyPlanner.

---

## Prerequisites

- A GitHub account
- A Supabase account (free tier works)
- A Render account (free tier works)
- A Google Cloud account (for Calendar sync + Gemini AI)
- A Groq account (free, for AI fallback)

---

## Step 1: Fork the Repository

1. Go to the GitHub repo: `https://github.com/YOUR_USERNAME/DailyPlanner`
2. Click **Fork** (top-right)
3. This creates your own copy at `https://github.com/NEW_USER/DailyPlanner`

---

## Step 2: Set Up Supabase

### 2.1 Create Project

1. Go to [supabase.com](https://supabase.com) → Sign up / Log in
2. Click **New Project**
3. Choose a name (e.g., `dailyplanner`)
4. Set a database password (save it somewhere)
5. Choose region closest to you
6. Click **Create new project** (takes ~2 minutes)

### 2.2 Get API Keys

1. Go to **Project Settings** → **API**
2. Copy these two values:
   - **Project URL** → This is your `SUPABASE_URL`
   - **anon public key** → This is your `SUPABASE_KEY`

### 2.3 Create Tables

Go to **SQL Editor** (left sidebar) → Click **New query** → Paste and run each block:

#### Core Tables

```sql
-- Users (for multi-user auth)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT true
);
CREATE INDEX idx_users_email ON users(email);

-- Daily Events (Planner V2)
CREATE TABLE daily_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    plan_date DATE NOT NULL,
    start_time TEXT,
    end_time TEXT,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'Nothing Planned',
    priority TEXT DEFAULT 'medium',
    is_deleted BOOLEAN DEFAULT false,
    google_event_id TEXT,
    quadrant TEXT,
    reminder_minutes INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_events_user_date ON daily_events(user_id, plan_date);

-- Daily Slots (Legacy V1 — kept for backward compat)
CREATE TABLE daily_slots (
    user_id TEXT NOT NULL,
    plan_date DATE NOT NULL,
    slot INTEGER NOT NULL,
    plan TEXT,
    status TEXT,
    start_time TEXT,
    end_time TEXT,
    priority TEXT,
    category TEXT,
    tags JSONB,
    priority_rank INTEGER,
    UNIQUE(user_id, plan_date, slot)
);

-- Daily Metadata
CREATE TABLE daily_meta (
    user_id TEXT NOT NULL,
    plan_date DATE NOT NULL,
    habits JSONB,
    reflection TEXT,
    untimed_tasks JSONB,
    UNIQUE(user_id, plan_date)
);

-- Eisenhower Matrix
CREATE TABLE todo_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    plan_date DATE NOT NULL,
    quadrant TEXT NOT NULL,
    task_text TEXT NOT NULL,
    is_done BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    position INTEGER DEFAULT 0,
    task_date DATE,
    task_time TEXT,
    category TEXT,
    subcategory TEXT,
    project_id UUID,
    source_task_id UUID,
    recurring_id UUID,
    delegated_to TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_todo_user_date ON todo_matrix(user_id, plan_date);

-- Recurring Tasks
CREATE TABLE recurring_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    quadrant TEXT,
    task_text TEXT,
    recurrence TEXT,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    category TEXT,
    subcategory TEXT,
    day_of_month INTEGER,
    days_of_week JSONB
);

-- Task Overrides (per-occurrence tracking)
CREATE TABLE task_overrides (
    user_id TEXT NOT NULL,
    task_id UUID,
    task_date DATE,
    status TEXT,
    completed_date DATE
);
```

#### Projects

```sql
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_archived BOOLEAN DEFAULT false,
    default_sort TEXT DEFAULT 'smart',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_projects_user ON projects(user_id);

CREATE TABLE project_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    task_text TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    priority_rank INTEGER DEFAULT 2,
    start_date DATE,
    due_date DATE,
    due_time TEXT,
    duration_days INTEGER DEFAULT 0,
    notes TEXT,
    planned_hours NUMERIC,
    actual_hours NUMERIC,
    order_index INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT false,
    is_eliminated BOOLEAN DEFAULT false,
    elimination_reason TEXT,
    delegated_to TEXT,
    is_recurring BOOLEAN DEFAULT false,
    recurrence_type TEXT,
    recurrence_days JSONB,
    recurrence_interval INTEGER,
    recurrence_end DATE,
    auto_advance BOOLEAN DEFAULT true,
    plan_date DATE,
    start_time TEXT,
    is_completed BOOLEAN DEFAULT false,
    quadrant TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_project_tasks_project ON project_tasks(project_id);
CREATE INDEX idx_project_tasks_user ON project_tasks(user_id);

CREATE TABLE project_subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES project_tasks(task_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    is_done BOOLEAN DEFAULT false,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### Health & Habits

```sql
CREATE TABLE habit_master (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT,
    goal NUMERIC,
    habit_type TEXT DEFAULT 'number',
    position INTEGER DEFAULT 9999,
    is_deleted BOOLEAN DEFAULT false,
    start_date DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE habit_entries (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    habit_id INTEGER REFERENCES habit_master(id),
    plan_date DATE NOT NULL,
    value NUMERIC,
    UNIQUE(user_id, habit_id, plan_date)
);

CREATE TABLE habit_goal_history (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER REFERENCES habit_master(id),
    goal NUMERIC,
    effective_from DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE daily_health (
    user_id TEXT NOT NULL,
    plan_date DATE NOT NULL,
    weight NUMERIC,
    height NUMERIC,
    mood TEXT,
    energy_level INTEGER,
    notes TEXT,
    goal TEXT,
    UNIQUE(user_id, plan_date)
);
```

#### Inbox, Notes, References

```sql
CREATE TABLE inbox_links (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    url TEXT,
    title TEXT,
    description TEXT,
    content_type TEXT,
    category TEXT,
    status TEXT DEFAULT 'Unread',
    is_favorite BOOLEAN DEFAULT false,
    reminder_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scribble_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT,
    content TEXT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false
);

CREATE TABLE reference_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    url TEXT,
    tags JSONB,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL
);
```

#### Google Calendar Tokens

```sql
CREATE TABLE user_google_tokens (
    user_id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    token_uri TEXT,
    client_id TEXT,
    client_secret TEXT,
    scopes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### Reference Cards

```sql
CREATE TABLE ref_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_ref_contexts_user ON ref_contexts(user_id);

CREATE TABLE ref_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    property_id UUID REFERENCES ref_contexts(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    provider TEXT NOT NULL,
    account_number TEXT,
    amount NUMERIC,
    currency TEXT DEFAULT 'INR',
    billing_cycle TEXT,
    due_day INTEGER,
    auto_pay BOOLEAN DEFAULT false,
    payment_method TEXT,
    portal_url TEXT,
    customer_id TEXT,
    notes TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_ref_cards_user ON ref_cards(user_id);

CREATE TABLE ref_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    bill_id UUID REFERENCES ref_cards(id) ON DELETE CASCADE,
    paid_date DATE,
    amount NUMERIC,
    method TEXT,
    reference TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### Portfolio

```sql
CREATE TABLE portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT,
    asset_type TEXT DEFAULT 'stock',
    exchange TEXT,
    quantity NUMERIC DEFAULT 0,
    avg_price NUMERIC DEFAULT 0,
    current_price NUMERIC,
    currency TEXT DEFAULT 'INR',
    folio_number TEXT,
    broker TEXT,
    sector TEXT,
    notes TEXT,
    held_by TEXT,
    buy_date DATE,
    sell_date DATE,
    institution TEXT,
    interest_rate NUMERIC,
    payout_type TEXT,
    compounding TEXT,
    maturity_date DATE,
    start_date DATE,
    account_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_portfolio_user ON portfolio_holdings(user_id);

CREATE TABLE portfolio_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    holding_id UUID REFERENCES portfolio_holdings(id) ON DELETE CASCADE,
    txn_type TEXT DEFAULT 'buy',
    txn_date DATE NOT NULL,
    quantity NUMERIC,
    price NUMERIC,
    amount NUMERIC,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_portfolio_txn_holding ON portfolio_transactions(holding_id);

CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    snap_date DATE NOT NULL,
    group_type TEXT NOT NULL,
    group_name TEXT NOT NULL,
    invested NUMERIC,
    current_value NUMERIC,
    xirr NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_portfolio_snap_user ON portfolio_snapshots(user_id, snap_date);
```

---

## Step 3: Set Up Render

### 3.1 Create Web Service

1. Go to [render.com](https://render.com) → Sign up / Log in
2. Click **New** → **Web Service**
3. Connect your GitHub account
4. Select the forked `DailyPlanner` repo
5. Configure:
   - **Name**: `dailyplanner` (or anything)
   - **Region**: Closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh`
   - **Plan**: Free (or Starter for always-on)

### 3.2 Set Environment Variables

In Render → Your service → **Environment** tab → Add these:

| Variable | Value | Required |
|----------|-------|----------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` (from Step 2.2) | **Yes** |
| `SUPABASE_KEY` | `eyJhbGc...` (anon key from Step 2.2) | **Yes** |
| `FLASK_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | **Yes** |
| `FLASK_ENV` | `production` | **Yes** |
| `ENCRYPTION_KEY` | Any memorable passphrase (e.g., `MySecretPhrase2026`) | **Yes** |
| `GOOGLE_API_KEY` | From Google Cloud → Gemini API key | For AI features |
| `GROQ_API_KEY` | From [groq.com](https://groq.com) → API Keys | For AI fallback |
| `GOOGLE_CLIENT_ID` | From Google Cloud → OAuth credentials | For Google Calendar |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud → OAuth credentials | For Google Calendar |
| `CRON_SECRET` | Any random string (for portfolio snapshots) | Optional |

### 3.3 Deploy

Click **Create Web Service**. Render will:
1. Pull your code from GitHub
2. Run `pip install -r requirements.txt`
3. Start the app with `bash start.sh`
4. Give you a URL like `https://dailyplanner-xxxx.onrender.com`

---

## Step 4: Get API Keys

### 4.1 Gemini AI (Google)

1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Click **Get API Key** → **Create API Key**
3. Copy the key → Set as `GOOGLE_API_KEY` in Render

### 4.2 Groq AI (fallback)

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up → **API Keys** → **Create**
3. Copy the key → Set as `GROQ_API_KEY` in Render

### 4.3 Google Calendar OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. **Enable API**: APIs & Services → Library → Search "Google Calendar API" → Enable
4. **Create OAuth**: APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
   - Application type: **Web application**
   - Authorized redirect URIs: `https://YOUR-APP.onrender.com/oauth2callback`
5. Copy **Client ID** → `GOOGLE_CLIENT_ID`
6. Copy **Client Secret** → `GOOGLE_CLIENT_SECRET`
7. **Consent Screen**: APIs & Services → OAuth consent screen → Add your email as test user

---

## Step 5: First Login

1. Visit `https://YOUR-APP.onrender.com/register`
2. Create an account (email + password)
3. Log in at `/login`
4. You're in! Start using the planner.

### Connect Google Calendar (optional)

1. Visit `https://YOUR-APP.onrender.com/google-login`
2. Sign in with your Gmail account
3. Grant calendar permissions
4. All events now auto-sync to Google Calendar

---

## Step 6: Optional — Daily Portfolio Snapshots

To get daily portfolio snapshots even when you don't open the app:

1. Set `CRON_SECRET` in Render env vars (any random string)
2. Go to [cron-job.org](https://cron-job.org) → Sign up (free)
3. Create a cron job:
   - **URL**: `https://YOUR-APP.onrender.com/api/portfolio/cron-snapshot`
   - **Method**: POST
   - **Headers**: Add `X-Cron-Secret: YOUR_CRON_SECRET_VALUE`
   - **Schedule**: Daily at 20:00 IST (14:30 UTC)

---

## Summary of All Environment Variables

| Variable | Purpose | Where to Get |
|----------|---------|-------------|
| `SUPABASE_URL` | Database URL | Supabase → Project Settings → API |
| `SUPABASE_KEY` | Database key | Supabase → Project Settings → API |
| `FLASK_SECRET_KEY` | Session encryption | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | `production` or `development` | Set manually |
| `ENCRYPTION_KEY` | Encrypts sensitive data | Choose a passphrase |
| `GOOGLE_API_KEY` | Gemini AI | Google AI Studio |
| `GROQ_API_KEY` | Groq AI (fallback) | Groq Console |
| `GOOGLE_CLIENT_ID` | Google Calendar OAuth | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Google Calendar OAuth | Google Cloud Console |
| `CRON_SECRET` | Portfolio snapshot auth | Choose any string |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | Check Render logs. Usually a missing env var. |
| Database errors | Make sure all tables are created in Supabase SQL editor. |
| Google Calendar not syncing | Visit `/google-login` to authorize. Check OAuth redirect URI matches your Render URL. |
| AI features not working | Check `GOOGLE_API_KEY` and `GROQ_API_KEY` are set. |
| Encryption errors | Make sure `ENCRYPTION_KEY` is set in Render. |
| Free tier sleeps | Render free tier sleeps after 15 min inactivity. First request takes ~30s to wake up. Upgrade to Starter ($7/mo) for always-on. |
