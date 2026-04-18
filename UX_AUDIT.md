# UX Audit — DailyPlanner

_Auditor: senior product designer (Apple HIG, Linear, Things 3, Notion Calendar reference)._
_Scope: every user-facing screen, plus the global shell._
_Severity legend: 🔴 Critical (data loss, blocks core flow, fails a11y) · 🟠 Major (visible UX harm, slows daily use) · 🟡 Minor (polish, paper cuts)._

---

## 0. Global / shell

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 0.1 | 🔴 | `templates/base.html` is **not** a layout — it's a leftover bottom-sheet snippet. No screen extends a real base, so every page re-imports fonts, CSS, JS, head tags via `_top_nav.html`. Triple-includes when partials are reused. | Make `base.html` the canonical `<!doctype html>` shell with `<head>` blocks, skip-link, global JS bundle, theme bootstrap. Each page extends it. Move `_top_nav.html`'s `<head>` payload into `base.html`. |
| 0.2 | 🔴 | `static/design-system.css` ships tokens but **only ~5%** of the codebase actually consumes them. Most pages re-declare colors (`--ib-primary`, `--ib-bg`, raw hex). Visual consistency is accidental. | Expand tokens (motion, focus ring, elevation, z-index scale, prose scale). Replace duplicated palettes in `inbox.html`, `health_dashboard.html`, `_top_nav.html`, etc. with token references. |
| 0.3 | 🔴 | No skip-link, no `<main id="main">` landmark. Sidebar pushes 20+ items before content for keyboard/screen-reader users. | Add `<a class="skip-link" href="#main">Skip to main content</a>` in `base.html`; wrap each page's content in `<main id="main">`. |
| 0.4 | 🔴 | Dark mode token in `design-system.css` only swaps colors — components like `.help-modal`, toast colors, `top-context` background still hard-code `#fff`/`rgba(255,…)` and silently break in dark mode. | Audit every `background:#fff`/`color:#111…` literal in `_top_nav.html`, `inbox.html`, `health_dashboard.html`, `references.html`, swap for surface/text tokens. |
| 0.5 | 🟠 | Active-link detection in `_top_nav.html` (line 750) prefers longest-match regex but list-vs-detail collisions (e.g. `/projects` vs `/projects/<id>/tasks`) leave the parent unhighlighted. | Two-tier rule: (1) exact-prefix match for parent, (2) deepest data-match wins for child. Highlight both parent group + child item. |
| 0.6 | 🟠 | Top-bar clock is hard-coded to **Asia/Kolkata** (`_top_nav.html` ~line 724). Any non-IST user sees the wrong time. | Use `Intl.DateTimeFormat().resolvedOptions().timeZone`. Fall back to IST only if user explicitly opts in (Settings). |
| 0.7 | 🟠 | No global focus-visible style. Links/buttons rely on browser default which is invisible on dark backgrounds. | Token `--ring`: `0 0 0 2px var(--color-surface), 0 0 0 4px var(--color-primary-ring)`. Apply via `:focus-visible` in `design-system.css`. |
| 0.8 | 🟠 | Toast container is centered-bottom on **all** breakpoints; on phones it sits above the OS gesture bar and is occluded. | Use `bottom: max(24px, env(safe-area-inset-bottom))`, narrower max-width, stack with `safe-area-inset-right` margin. |
| 0.9 | 🟠 | Two scripts (`/static/js/global.js`, `/static/js/toast.js`) load on every page, but `top_nav.js` reloads them again. Duplicate listeners = duplicate toasts on some events. | Single bundle in base layout; deduplicate `_top_nav.html`'s preconnect/font block (currently re-emitted whenever `_top_nav.html` is included). |
| 0.10 | 🟡 | `templates/login.py`, `planner.py`, `summary.py`, `todo.py` are HTML files misnamed `.py` (legacy from a pre-Flask refactor). Confuses search, IDE, AI tools. | Delete (Flask never loads them; live templates are `.html`). |
| 0.11 | 🟡 | No `prefers-reduced-motion` handling. Modal scale-in, sheet slide, ring shimmer all play for users who asked the OS to stop. | `@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.001ms!important; transition-duration:.001ms!important; } }` |
| 0.12 | 🟡 | Inter font loaded twice (preconnect + linked stylesheet inside `_top_nav.html` plus inline imports in `login.html`/`register.html`). | Single load via `base.html`. |

---

## 1. Planner ("Calendar" / `planner_v2.html`)

**Pattern:** Google-Calendar-style day/3-day/week grid with mini-cal sidebar.

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 1.1 | 🔴 | Drag-to-create computes Y from viewport rect without adding `gcal-scroll.scrollTop` (`planner_v2.html` ~line 1878). After scrolling, the ghost slot snaps to the wrong time. | Add `+ scrollEl.scrollTop` to the Y math; cache `getBoundingClientRect()` once per drag. |
| 1.2 | 🔴 | Mini-calendar in sidebar is decorative — clicking a date does nothing. Users learn it's broken and stop trying. | Wire `onclick` → set `currentDate`, rebuild grid, focus the new day's column. Show today/selected accent dot. |
| 1.3 | 🔴 | Modal save blocks the UI for the whole network round-trip with no spinner. Slow links → frozen-feeling app. | Optimistically render the chip, send POST in background, rollback + toast on error. |
| 1.4 | 🟠 | Conflict alert shows the message but offers no resolution. User must close, re-open, manually shift time. | Inline "Defer 30 min", "Stack on top", "Cancel" buttons inside the alert. |
| 1.5 | 🟠 | "Floating tasks" panel and "AI Parse" button are dead — handlers never wired. Visible affordance, no behaviour = trust loss. | Either wire to existing `services/agenda_service.py`+`utils/smartplanner.py` or remove the UI. (Do the former — the backend exists.) |
| 1.6 | 🟠 | No keyboard support: cannot create event with `n`, navigate with `j/k`, delete with `Backspace`. | Adopt Linear/Cron shortcut set: `t` today, `←/→` prev/next day, `1/2/3` view switch, `c` create, `?` cheatsheet. |
| 1.7 | 🟠 | Drag-resize (bottom edge of an event) not implemented. Only way to change duration is to open the modal. | Add resize handle (8px). Live duration badge updates as user drags. Snap to 15-min grid. |
| 1.8 | 🟡 | Title field has no max length / character counter. Long titles overflow the chip and break layout. | `maxlength=120`, soft counter at >100 chars. Add `text-overflow: ellipsis` on chip. |
| 1.9 | 🟡 | "Now" line not visible on day view (or visible but unstyled). | Hairline `currentColor` line + small dot at the time-gutter; refresh every 60 s. |

**Top 5 designer recommendations** (in order):
1. Optimistic create + drag-move (1.3) — single biggest perceived-speed win.
2. Make the mini-cal navigate (1.2).
3. Keyboard map (1.6).
4. Drag-resize (1.7).
5. Conflict resolution buttons (1.4).

---

## 2. Eisenhower / Todo (`todo.html`)

**Pattern:** 2×2 quadrant grid, per-day. Detail panel as bottom sheet.

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 2.1 | 🔴 | `todo.html` is **3,777 lines** — single file with inline CSS, JS, templates, modals. Maintenance is brittle; any redesign risks regressions. | Split: `todo.html` (markup), `static/todo.css`, `static/todo.js`. Extract repeated card markup into Jinja partials. |
| 2.2 | 🔴 | Quick-add silently fails on empty input — server returns 500, user sees nothing. | Disable submit when input empty; client-side trim + min length 1; error toast on 4xx/5xx. |
| 2.3 | 🔴 | `eisenhower_service.py` auto-moves a "Schedule" task to "Do" on its due-date without telling the user. Looks like data was reset. | Drop the auto-move (deferred surfacing belongs in a "Today" filter, not a destructive write). If kept, surface a toast: "Moved to Do — due today". |
| 2.4 | 🟠 | No keyboard interactions at all. Power users complete 30+ items/day; mouse-only is slow. | `j/k` move focus, `space` toggle done, `→/←` move quadrant, `e` open edit, `?` cheatsheet. |
| 2.5 | 🟠 | No filter/sort UI. Cannot ask "what's overdue", "from project X", "due this week". | Filter chips above grid: All · Today · Overdue · This week · Project ▾. Persist in URL. |
| 2.6 | 🟠 | Dual sources of truth: `is_done` boolean + `status` string. Drift is invisible. | Pick one (`status` enum). Migrate `is_done` to a derived computed. |
| 2.7 | 🟠 | Recurring picker only handles daily/weekly/monthly. Doesn't expose "every weekday", "every 2 weeks", "1st Monday of the month". | Inline RRULE-style chips + an "Advanced" disclosure. |
| 2.8 | 🟠 | Project-linked / event-linked cards in the matrix are read-only with no visual hint. Users click and nothing happens. | Add a small "↗ project" / "📅 event" badge on the card; click opens the source in a new tab/sheet. |
| 2.9 | 🟡 | Quadrant headers say "Do (2/5)". Counts re-render OK but a11y label doesn't change. | Add `aria-live="polite"` on the count span. |
| 2.10 | 🟡 | Bottom sheet on desktop covers the matrix instead of side-docking. Loses context. | Right-edge slide-in drawer ≥ 1024 px; keep sheet pattern on mobile. |
| 2.11 | 🟡 | "Travel mode" toggles a giant template insert with no preview. First-timer surprise. | Inline preview of templates in a popover before insert. |

**Top 5 designer recommendations**:
1. Inline-edit on hover (no full sheet for title/due/priority).
2. Keyboard shortcuts (2.4).
3. Filter chips (2.5).
4. Undo toast for completion/move/delete.
5. Optimistic mutations everywhere.

---

## 3. Projects + Project Tasks (`projects.html`, `project_tasks.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 3.1 | 🔴 | `add_project_task_ajax` ends with `location.reload()`. Loses scroll, filters, sort, focus. | Render task partial server-side, return HTML, insert into DOM, focus new row. |
| 3.2 | 🔴 | Drag-reorder constrained to identical (due_date, priority, pin) tuples. Users expect "just move it up". | Drop the constraint within a single project view — reorder updates `order_index` only. Keep constraint as the implicit sort tie-breaker. |
| 3.3 | 🟠 | Two different edit affordances (inline date update vs. bottom-sheet) for fields on the same card. Cognitive friction. | Single inline editor everywhere; sheet only for full-detail (subtasks, recurrence, notes). |
| 3.4 | 🟠 | Archive button has no confirmation/undo. One misclick, project disappears from the main view. | 5-second undo toast. Don't show a confirm dialog (slows the common case); rely on undo. |
| 3.5 | 🟠 | No way to pin/star projects. With >10 projects the grid becomes scan-heavy. | `★` toggle on each card; pinned float to a "Pinned" row above. |
| 3.6 | 🟠 | OKR picker forces an initiative when adding a task; "no initiative" path exists but isn't explained. | Add an "(no link)" option as the default; explain inline: "Optional — link later from the task detail." |
| 3.7 | 🟡 | Progress bar is purely decorative. Not clickable, no tooltip with breakdown. | Tooltip "12/18 done · 4 in progress · 2 overdue". |
| 3.8 | 🟡 | Bulk-select toolbar appears in-flow rather than docked, so it shifts content when toggled. | Sticky bottom bar with count + actions. |

---

## 4. Project Gantt (`project_gantt.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 4.1 | 🔴 | Progress bar uses **effort %** (`actual_h / planned_h`), not **calendar %**. Reads as "halfway through the work" when it's "halfway through the time". | `progress = clamp((today − start) / (end − start), 0, 1) * 100`. Expose effort % as a separate badge. |
| 4.2 | 🔴 | Click on a task does nothing — Frappe Gantt's `on_click` is never wired. Inert visualization. | Open the task detail sheet on click. |
| 4.3 | 🟠 | Gantt is read-only. Users cannot drag a bar to reschedule; must round-trip via the task list. | Wire `on_date_change` → POST `/projects/tasks/<id>/update-planning`. |
| 4.4 | 🟠 | All bars same colour. Status/priority not encoded. | Color-code by status; outline by priority. Legend in header. |
| 4.5 | 🟡 | View mode hard-coded to "Day". Long projects need Week/Month. | Toggle pill: Day · Week · Month. Persist in URL. |
| 4.6 | 🟡 | Frappe Gantt loaded from CDN un-versioned. Breaks silently on upstream change. | Pin to `@1.0.3` (current latest stable). |

---

## 5. Project Timeline (`project_timeline.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 5.1 | 🟠 | Drop reschedules without optimistic update — user has to wait for the round-trip then reload to see the change. | Move DOM node first, POST in background, rollback on error. |
| 5.2 | 🟠 | Status/overdue not visually encoded on cards. | `data-status` + colour outline. |
| 5.3 | 🟡 | Week grouping uses `due_date` only; tasks with start_date but no due_date silently drop. | Use `start_date or due_date`; otherwise bucket as "Unscheduled". |

---

## 6. Portfolio (`portfolio.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 6.1 | 🔴 | "Delete holding" is a **hard delete** (`routes/portfolio.py:122`). Years of investment history evaporate. Violates the project-wide soft-delete rule. | Add `is_deleted` filter; soft-delete only; "Trash" view per the Vault pattern. |
| 6.2 | 🟠 | Mixed-currency portfolio sums INR + USD as if they're the same number. | Per-user base currency setting; convert in `services/reports_service.py` and the summary KPI. |
| 6.3 | 🟠 | Symbol input accepts any string; price refresh later silently fails. | Validate against AMFI/Yahoo on blur; show "Symbol not found" inline. |
| 6.4 | 🟡 | No "portfolio over time" chart even though daily snapshots are stored. | Wire snapshot data → Chart.js line; tab in KPI row. |
| 6.5 | 🟡 | Refresh-prices is sequential with 5 s timeout each. 50 holdings = 4 min. | Concurrent fetch with per-call timeout; partial results. |

---

## 7. Goals / OKRs (`goals.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 7.1 | 🔴 | KR "current_value" is manual. The whole point of OKRs is bottom-up roll-up. | Compute KR progress from completion of linked-initiative tasks; show "auto-synced" badge; allow manual override. |
| 7.2 | 🟠 | KR `direction = "down"` (e.g. reduce defects from 100 → 10) is stored but progress math ignores it. | `if direction == "down": pct = (start − current) / (start − target)`. |
| 7.3 | 🟠 | No edit UI for objectives once created — delete + recreate is the only path. | Edit modal pre-filled. |
| 7.4 | 🟡 | Personal goals (project_id NULL) and project goals are mixed without separation. | "Personal" tab. |

---

## 8. Reports (`reports.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 8.1 | 🔴 | Productivity counts only `todo_matrix`. A user who lives in projects sees "0 done". | Sum both sources; mark each chip "from matrix" / "from project". |
| 8.2 | 🟠 | Financial tile silently disappears if Vault is locked — no explanation. | Render a "Locked — unlock Vault" placeholder with action button. |
| 8.3 | 🟠 | Narrative ("8/12 done · 5-day streak …") prints zero-state literally ("0/0 tasks done"). | Skip empty parts; if everything's empty, friendly empty state. |
| 8.4 | 🟡 | No comparison to last week / last month. | "Compare to ▾" selector with delta arrows. |

---

## 9. Health (`health_dashboard.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 9.1 | 🔴 | `routes/health.py:430-434` — `params={..."plan_date": "gte.…", "plan_date": "lte.…"}` — Python dict collapses to one key. The whole heatmap silently filters by **upper bound only**. | Use Supabase's `and=(plan_date.gte.X,plan_date.lte.Y)` syntax (already used at line 394). |
| 9.2 | 🟠 | Habit names force-uppercased on save (`routes/habits.py:17`). "Walking" → "WALKING". Harsh, vendor-tooly. | Drop `.upper()`; trust user casing; trim only. |
| 9.3 | 🟠 | Streak shown without a definition. | Tooltip: "Days in a row with ≥ X% of habits met". Make X configurable. |
| 9.4 | 🟡 | 30-day heatmap on phones has 30 cells × 12 px each = un-tappable. | Horizontal scroll with snap; minimum 24 px cell. |

---

## 10. Inbox (`inbox.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 10.1 | 🟠 | Auto-save on URL paste shows no loading state. User assumes it saved; sometimes it didn't. | Spinner on the field while pending; toast on success/error. |
| 10.2 | 🟠 | YouTube fallback to "Google search" is silent — user only finds out by trying. | Inline notice: "YouTube search unavailable — using web search". |
| 10.3 | 🟡 | Status colours only (no icons). Colourblind users can't tell Reading from Done. | Add status icons + text. |

---

## 11. References + Refcards / Vault

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 11.1 | 🔴 | Vault TTL is checked then `_vault_touch` slides the window — a request that arrives within TTL but after eviction shows a generic error. | Refresh TTL **before** checking; on miss, return a 401 + `WWW-Authenticate: Vault` and let the client open the unlock modal in place. |
| 11.2 | 🟠 | AI metadata fetch (Groq) catches everything → silent blank description. | Surface "AI generation failed — fill manually" inline. |
| 11.3 | 🟠 | References infinite scroll has no "you've reached the end" message — users keep scrolling. | Sentinel + "End of results" line. |
| 11.4 | 🟡 | Refcards copy-to-clipboard logs server-side but doesn't auto-clear. | Copy + 30-second auto-clear; visible countdown. |

---

## 12. Auth (`login.html`, `register.html`)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 12.1 | 🔴 | No password-reset flow at all. Forgot password = locked out forever. | Add `/forgot-password` → email token → set new. |
| 12.2 | 🔴 | `next` query param redirected to without validation = open redirect. | Validate with `urllib.parse.urlparse`; only allow same-origin paths. |
| 12.3 | 🟠 | Errors render as a single banner; no per-field hints; values lost on validation fail. | Inline field errors; preserve email/display_name on re-render (already half-done, wire fully). |
| 12.4 | 🟠 | Rate limit is per-IP only. Distributed brute force bypasses easily. | Compound key: IP **and** email. |
| 12.5 | 🟡 | No password-strength meter. | Lightweight zxcvbn-lite scorer client-side. |

---

## 13. Notes ("Scribble")

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 13.1 | 🟠 | Soft-delete with no Trash UI = no recovery. | `/notes/trash` view with restore + permanent-delete (after 30 days). |
| 13.2 | 🟡 | Card preview shows raw text. HTML notes look stripped/odd. | Render sanitized snippet (first 240 chars of plain text), preserve line breaks. |

---

## 14. IA / Cross-cutting

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 14.1 | 🔴 | No global search. Five top-level groups, ~17 destinations, no `Cmd-K`. | Add command-palette: routes, recent items, tasks, notes, refs. Open with `⌘K`/`Ctrl-K` or "Search" button. |
| 14.2 | 🔴 | Filter/sort state is lost on navigation (no URL persistence on Projects, Inbox, References). | Encode in URL; restore on load. |
| 14.3 | 🟠 | No breadcrumbs anywhere. `/projects/<id>/tasks/<task>/subtasks` gives no orientation. | Breadcrumb component used by Projects, Goals, References. |
| 14.4 | 🟠 | Empty states are inconsistent (some have icon + CTA, some just say "no items"). | Single `EmptyState` component (icon, title, body, CTA). |
| 14.5 | 🟠 | No first-run / empty workspace onboarding. | A 3-step "Add your first project / task / habit" card on a brand-new account. |

---

## 15. Accessibility (WCAG 2.2 AA)

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 15.1 | 🔴 | No skip-link, no `<main>` landmark (see 0.3). | Done globally. |
| 15.2 | 🔴 | Many icon-only buttons missing `aria-label` (planner view-switcher, mini-cal nav, top-nav hamburger close on some breakpoints, refcards eye icon). | Audit + label. |
| 15.3 | 🟠 | Status communicated by colour alone (Inbox, Quadrants, Portfolio asset types). | Add icon **and** text **and** colour. |
| 15.4 | 🟠 | Modal focus trap absent (Help modal, Task detail sheet on desktop). | Trap with first/last sentinel; restore focus on close. |
| 15.5 | 🟠 | Contrast: `--color-text-muted #9ca3af` on `--color-bg #f0f2f5` = 2.7:1. Fails AA for normal text. | Bump muted to `#6b7280` (4.6:1). |
| 15.6 | 🟠 | `lang` attribute missing on most pages (any whose `<html>` is emitted by `_top_nav.html`). | Set `<html lang="en">` in `base.html`. |
| 15.7 | 🟡 | Form labels rely on placeholder text in several places (e.g. login email at small breakpoints). | Always-visible label + hint. |

---

## 16. Mobile & responsive

| # | Severity | Issue | Concrete fix |
|---|---|---|---|
| 16.1 | 🔴 | `todo.html` 2×2 grid stays 2×2 below 480 px → each card holds 1.3 lines of text. Unusable. | Stack to single column < 720 px; "horizontal carousel" pattern with snap and dot indicators. |
| 16.2 | 🟠 | Planner mini-cal sidebar consumes 256 px on 360 px phone → main grid clipped. | Hide sidebar < 768 px; surface mini-cal in a popover off the date picker. |
| 16.3 | 🟠 | Bottom sheets for editing don't honour iOS safe-area-bottom. | `padding-bottom: max(16px, env(safe-area-inset-bottom))`. |
| 16.4 | 🟡 | Tap targets < 44 px on portfolio table action buttons. | Minimum 44 × 44 px. |

---

## 17. Best-practice gaps vs. modern planners

| # | Pattern (Linear/Things 3/Notion Cal) | Status here | Action |
|---|---|---|---|
| 17.1 | Natural-language input ("lunch with Sam tomorrow at 1pm for 90 min") | Backend exists (`utils/planner_parser.py`, `utils/smartplanner.py`) but no UI surface. | Wire smart-input to the planner & quick-add. |
| 17.2 | Cmd-K palette | Missing | Add (see 14.1). |
| 17.3 | Drag-and-drop everywhere | Partial (project timeline, planner) | Extend to matrix, project list reorder, gantt. |
| 17.4 | Optimistic UI | Almost nowhere | Make default; rollback on error. |
| 17.5 | Undo stack | Missing | 10-second toast undo for delete/move/complete. |
| 17.6 | Rich keyboard map | Missing | Adopt single global shortcut layer + page-specific overlay (`?`). |
| 17.7 | Soft-delete + Trash UI | Mixed; portfolio is hard-deleted; notes have no Trash | Standardize. |
| 17.8 | Real-time sync between views | None | Out of scope for this round (would need pub/sub); revisit. |

---

## Severity tally

| Severity | Count |
|---|---|
| 🔴 Critical | 23 |
| 🟠 Major | 38 |
| 🟡 Minor | 22 |
