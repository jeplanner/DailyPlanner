# Install DailyPlanner for a New User

> Read this **alongside** `SETUP_GUIDE.md`. That file is the canonical
> step-by-step (Supabase tables, Render setup, Google Cloud, Groq).
> This document focuses on the parts that change when the **owner** is
> a different person — different GitHub, different Render account,
> different Supabase project, different Google + AI accounts.

---

## ⚠️ Read this first — security

The repo contains **no hardcoded secrets in source code**. All credentials are loaded from environment variables. **However:**

1. **`.env` exists in the local working tree of the original developer** (it is gitignored, so it is **not** in the repo, but it is on disk). It contains the original owner's live API keys — Supabase, Google Gemini, Groq, Google OAuth, Flask secret. **Do not copy that file**. The new user must generate their own credentials from scratch (steps below).

2. **Rotate the original keys** if any of them ever leave the original developer's machine (e.g. shared in chat, sent in a screenshot, posted in a support thread). Specifically:
   - Supabase → Dashboard → Project Settings → API → "Reset anon key" (also reset service-role key if used).
   - Groq → Console → API Keys → Revoke + create new.
   - Google AI Studio → API Keys → Delete + create new.
   - Google Cloud → APIs & Services → Credentials → OAuth client → "Reset client secret" (or delete and re-create).
   - Flask SECRET_KEY → just generate a new one (any random 64+ char string).

The new instance gets entirely new keys — there is no overlap.

---

## What is hardcoded in the source code (and must be edited)

The application is *almost* fully configurable via environment variables, but **two places in the repo contain values from the original owner** that need to be changed before deploying for a different person.

### 1. Family / member names in the portfolio "Held By" filter
**File:** `templates/portfolio.html`

There are **three** spots with the original owner's family names hardcoded as filter buttons and dropdown options:

```html
<!-- around line 152: portfolio Owner filter buttons -->
<button class="type-tab" onclick="filterOwner('Venghatesh',this)">Venghatesh</button>
<button class="type-tab" onclick="filterOwner('Chitra',this)">Chitra</button>
<button class="type-tab" onclick="filterOwner('Shreya',this)">Shreya</button>
<button class="type-tab" onclick="filterOwner('Sethu',this)">Sethu</button>

<!-- around line 336: "Held By" select in the add-holding modal -->
<select id="h-owner" class="fi">
  <option value="Venghatesh">Venghatesh</option>
  <option value="Chitra">Chitra</option>
  <option value="Shreya">Shreya</option>
  <option value="Sethu">Sethu</option>
</select>

<!-- around line 727: default value when editing -->
document.getElementById("h-owner").value = h.held_by || 'Venghatesh';
```

**Action:** replace those four names with the new user's family / household members (or remove the filter and set the default to the new user's name). Update all three locations consistently. The default broker on line 342 (`value="ICICI Direct"`) is also India-specific — replace if the new user uses a different broker.

### 2. Chrome extension API base URL
**Files:** `chrome_extension/background.js`, `chrome_extension/popup.js`, `chrome_extension/manifest.json`

All three hard-code the **original instance's Render URL** (`https://dailyplanner-zus3.onrender.com`). The new user will get a different Render URL.

```js
// chrome_extension/background.js  line 1
const API_BASE = "https://dailyplanner-zus3.onrender.com";

// chrome_extension/popup.js  line 1
const API_BASE = "https://dailyplanner-zus3.onrender.com";
```

```json
// chrome_extension/manifest.json  line 7
"host_permissions": ["https://dailyplanner-zus3.onrender.com/*"]
```

**Action:** after the new Render service is up, replace all three with the new user's URL (e.g. `https://newuser-dailyplanner.onrender.com`). If the chrome extension isn't going to be used, delete the `chrome_extension/` directory entirely — nothing in the Flask app depends on it.

### 3. Defaults that may or may not need editing
These are **defaults**, not personal data — but the new user might want different choices:

| Location | Default | Notes |
|---|---|---|
| `config.py:2` | `IST = ZoneInfo("Asia/Kolkata")` | Hard-coded to India Standard Time. The whole backend uses this for "today", recurring schedules, snapshot times. Change to the new user's tz if not in India. |
| `config.py:8` | `STATUSES = ["Nothing Planned", "Yet to Start", ...]` | Task statuses. Generic enough to keep. |
| `config.py:10–17` | `HABIT_LIST = ["Walking", "Water", "No Shopping", ...]` | The seed list of suggested habits. New users can ignore — they add their own. |
| `config.py:64–121` | `TRAVEL_MODE_TASKS` | Pre-filled travel checklist (closing geyser, taking laptop, etc.). Specific to the original owner's home; new user should review or empty the list. |
| `templates/portfolio.html:342` | `value="ICICI Direct"` | Default broker name. India-specific. |

None of these are credentials or personally-identifying — they are content defaults. The app works fine if you don't touch them.

### 4. Things that look hardcoded but aren't
- **Supabase URLs in `.env`** → not in source.
- **AI API keys** → loaded only from env (`os.environ.get(...)` in every code path).
- **Google OAuth client id/secret** → env-only (`routes/events.py:426–469`).
- **CRON_SECRET** → env-only.
- **Encryption key** → env-only (`utils/encryption.py:23`).
- **CSP allow-list in `middleware/security.py`** → those are CDN URLs (Quill editor, Feather icons, Yahoo Finance, AMFI). Keep as-is.
- **External API endpoints** (`yahoo finance`, `mfapi.in`, `groq.com/openai/v1`, Google OAuth URIs) → standard public endpoints, not personal.

---

## Step-by-step for the new user

### Step 0 — Prerequisites
The new user needs accounts on:

| Service | Why | Cost |
|---|---|---|
| **GitHub** | Host their fork of the code | Free |
| **Render** | Run the Flask web service | Free tier sleeps after 15 min idle; $7/mo Starter for always-on |
| **Supabase** | Postgres database | Free tier (500MB) is plenty |
| **Google Cloud** | Calendar OAuth + Gemini AI key | Free under quota |
| **Groq** | AI fallback | Free tier |
| **(Optional) cron-job.org** | Daily portfolio snapshot ping | Free |

### Step 1 — Fork the repo to the new GitHub account

1. Sign in to **the new user's GitHub** (if you're doing this for them, they need to invite you or share credentials — or you can transfer ownership later).
2. Open the **original** repo in a browser.
3. Click **Fork** (top-right) → choose the new user's account as the destination.
4. Result: `https://github.com/NEW_USERNAME/DailyPlanner`.

   **Alternative (cleaner — no upstream tie):**
   ```bash
   # Locally
   git clone https://github.com/ORIGINAL_OWNER/DailyPlanner.git tmp
   cd tmp
   rm -rf .git
   git init
   git add .
   git commit -m "Initial import"
   gh repo create NEW_USERNAME/DailyPlanner --private --source=. --push
   # or push manually to a repo created via the GitHub UI
   ```

### Step 2 — Edit the two hardcoded spots (above)

Before pushing or deploying, edit the items in **"What is hardcoded"** §1 and §2 above. Commit:

```bash
git commit -am "Personalise portfolio owners + remove old chrome ext URL"
git push
```

### Step 3 — Create the new Supabase project

1. **The new user logs in** at supabase.com (their own account).
2. Click **New project**, give it any name, save the database password somewhere safe.
3. Wait ~2 minutes.
4. **Project Settings → API**: copy
   - `Project URL` → this becomes `SUPABASE_URL`
   - `anon public key` → this becomes `SUPABASE_KEY`
5. **SQL Editor → New query**: paste **all** the `CREATE TABLE` blocks from `SETUP_GUIDE.md` Step 2.3. Run them.
6. **Add the soft-delete columns** that the recent refactor expects (these are missing from `SETUP_GUIDE.md`):
   ```sql
   alter table portfolio_holdings     add column if not exists is_deleted  boolean default false;
   alter table portfolio_holdings     add column if not exists deleted_at  timestamptz;
   create index if not exists idx_portfolio_holdings_live on portfolio_holdings (user_id) where is_deleted = false;

   alter table portfolio_transactions add column if not exists is_deleted  boolean default false;
   alter table portfolio_transactions add column if not exists deleted_at  timestamptz;
   ```

### Step 4 — Get the AI keys (new accounts)

1. **Google Gemini key** (from Google AI Studio):
   - https://aistudio.google.com → sign in with the new user's Google account → **Get API Key** → **Create API Key in new project** → copy.
   - This becomes `GOOGLE_API_KEY`.
2. **Groq key**:
   - https://console.groq.com → sign up with new user's email → **API Keys** → **Create** → copy.
   - This becomes `GROQ_API_KEY`.

### Step 5 — Set up Google Calendar OAuth (new project)

1. https://console.cloud.google.com (sign in as the new user).
2. Top bar → project dropdown → **New Project** → name it `dailyplanner-NAME` → create.
3. **APIs & Services → Library** → search **"Google Calendar API"** → **Enable**.
4. **APIs & Services → OAuth consent screen** →
   - User type: **External** → Create.
   - App name: `DailyPlanner`. Support email: new user's email.
   - **Scopes**: add `https://www.googleapis.com/auth/calendar.events`.
   - **Test users**: add the new user's Gmail address.
5. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Web application**.
   - Authorized redirect URIs: `https://NEW_RENDER_URL.onrender.com/oauth2callback` (you will know the URL after Step 6 — you can come back and edit).
   - Save the **Client ID** → `GOOGLE_CLIENT_ID`.
   - Save the **Client Secret** → `GOOGLE_CLIENT_SECRET`.

### Step 6 — Create the Render web service

1. https://render.com → sign in as the new user (or invite them as collaborator).
2. **New → Web Service** → connect GitHub → pick the new fork.
3. Settings:
   - **Name**: `NEW_USERNAME-dailyplanner` (this becomes your URL: `https://NEW_USERNAME-dailyplanner.onrender.com`).
   - **Region**: closest to the new user.
   - **Branch**: `main`.
   - **Runtime**: `Python 3`.
   - **Build command**: `pip install -r requirements.txt`.
   - **Start command**: `bash start.sh`.
   - **Plan**: Free is OK for a try-out; pick Starter ($7/mo) if you don't want the 15-min sleep.

4. Before clicking **Create**, scroll down to **Environment Variables** and add these:

   | Variable | Value | Where to get it |
   |---|---|---|
   | `SUPABASE_URL` | from Step 3 | Supabase API page |
   | `SUPABASE_KEY` | from Step 3 | Supabase API page |
   | `FLASK_SECRET_KEY` | generate now | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `FLASK_ENV` | `production` | literal |
   | `ENCRYPTION_KEY` | a passphrase you can remember | any string ≥ 16 chars (e.g. `MyHouseholdPlanner-2026!`) — **write it down**, losing it means losing access to encrypted Vault/portfolio fields |
   | `GOOGLE_API_KEY` | from Step 4 | Google AI Studio |
   | `GROQ_API_KEY` | from Step 4 | Groq Console |
   | `GOOGLE_CLIENT_ID` | from Step 5 | Google Cloud Credentials |
   | `GOOGLE_CLIENT_SECRET` | from Step 5 | Google Cloud Credentials |
   | `CRON_SECRET` | random string | only needed if doing daily snapshots (Step 9) |

5. Click **Create Web Service**. Wait for the first deploy (~5 min).
6. Note the URL Render gave you (e.g. `https://newuser-dailyplanner.onrender.com`).

### Step 7 — Update Google OAuth redirect URI

Go back to the Google Cloud OAuth client (Step 5) and **edit** the redirect URI to use the **actual** Render URL from Step 6: `https://NEW_RENDER_URL.onrender.com/oauth2callback`. Save.

### Step 8 — Create the first user account

1. Open `https://NEW_RENDER_URL.onrender.com/register` in a browser.
2. Register with the new user's email + password (≥ 8 chars).
3. Log in at `/login`.
4. (Optional) Visit `/google-login` and grant Google Calendar permissions.

### Step 9 — (Optional) Daily portfolio snapshots

If the new user wants automatic daily portfolio snapshots:

1. Make sure `CRON_SECRET` is set in Render (from Step 6 — pick any random string).
2. https://cron-job.org → sign up.
3. Create a cron job:
   - URL: `https://NEW_RENDER_URL.onrender.com/api/portfolio/cron-snapshot`
   - Method: **POST**
   - Header: `X-Cron-Secret: <the value of CRON_SECRET>`
   - Schedule: daily, e.g. 20:00 in their local timezone.

### Step 10 — (Optional) Chrome extension

If the new user uses the Chrome extension:
1. Edit `chrome_extension/background.js`, `popup.js`, and `manifest.json` per **"What is hardcoded"** §2 above.
2. Open Chrome → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → pick the `chrome_extension/` folder.

---

## Verification checklist

After Step 8, the new user should be able to:

- [ ] Visit `/` and see "Today's Plan" without an error.
- [ ] `/login` and `/register` look correct (these were just redesigned — see the recent `SUMMARY.md`).
- [ ] `/calendar` loads the day grid.
- [ ] `/todo` loads the Eisenhower matrix.
- [ ] `/projects` loads the project list.
- [ ] `/health` loads (it'll be empty until habits are added).
- [ ] `/portfolio` loads (empty list — no holdings yet).
- [ ] `/refcards` prompts for a vault password (first-time setup).
- [ ] **Top-right clock** shows the new user's local timezone abbreviation, not "IST" (the recent refactor made this auto-detect).
- [ ] An add-event in the calendar saves and re-renders.
- [ ] A test reflection on `/summary?view=daily` plus "AI Summary" returns text (verifies `GOOGLE_API_KEY` / `GROQ_API_KEY` work).

If any step 500's: Render → service → **Logs** tab. The most common errors are missing env vars — every required var is listed above.

---

## Cleanup tips

1. **Delete `.env` locally** if you cloned the repo to a machine you'll work on for the new user. Use a fresh `.env` with the new user's keys, never copy the old one.
   ```bash
   rm .env
   # then create your own:
   cat > .env <<EOF
   SUPABASE_URL=https://...new...supabase.co
   SUPABASE_KEY=...new...
   FLASK_SECRET_KEY=...new random...
   GOOGLE_API_KEY=...new...
   GROQ_API_KEY=...new...
   GOOGLE_CLIENT_ID=...new...
   GOOGLE_CLIENT_SECRET=...new...
   ENCRYPTION_KEY=...new passphrase...
   FLASK_ENV=development
   EOF
   ```
2. `.env` is already in `.gitignore` — confirm with `git check-ignore .env` (should print `.env`).
3. Don't commit screenshots or logs that contain the URL `gidpxopleslvmrrycood.supabase.co` — that's the original instance's Supabase project. The new user has nothing to do with it.

---

## TL;DR

1. **Source code has no hardcoded secrets.** All keys come from env vars.
2. **Two manual edits in the source** are needed for a different user: portfolio owner names (`templates/portfolio.html`, 3 spots) and the chrome extension's API base URL (3 files).
3. **Everything else is just signing up to fresh accounts** (GitHub, Supabase, Render, Google Cloud, Groq) and pasting the new credentials into Render's environment variables panel.
4. **One config-not-credential note:** `config.py` defaults to `Asia/Kolkata` timezone — change for non-India users.
5. **After the recent refactor:** also run the `alter table` SQL in Step 3.6 (adds `is_deleted` columns to portfolio tables — required for the new soft-delete code path).
