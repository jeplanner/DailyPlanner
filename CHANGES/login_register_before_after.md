# Login / Register — before vs. after

## Before (status quo)
- `templates/login.html` was 178 lines, of which **138 were inline `<style>`** hard-coding hex literals (`#2563eb`, `#f0f2f5`, `#fecaca`, …).
- `templates/register.html` duplicated the same CSS block (194 lines, nearly identical rules).
- No link to `design-system.css` or `components.css` — dark mode silently broke on these pages.
- Error bar rendered as a plain box; no ARIA `role` attributes; no iconography; no password show/hide; no strength meter; no inline match check.
- "Forgot password?" link didn't exist anywhere in the flow, so a locked-out user had no recovery path.
- `autocomplete` hints were missing on several fields (`email`, `current-password`, `new-password`). Password managers silently worked against the forms.

## After
- Both pages extend the token-driven `design-system.css`, shared `components.css`, and a new page-scoped `static/auth.css`.
- Zero inline `<style>` blocks. Zero hex literals. Everything references tokens (`--color-primary`, `--radius-xl`, `--shadow-lg`, …) so dark mode, focus rings, and reduced-motion work automatically.
- **Skip link** above the form for keyboard / screen-reader users.
- **Brand lockup** ("D" logo + "DailyPlanner") sits above the card — same pattern on both pages, no more giant emoji.
- **Proper field labels** replace placeholder-only labels (WCAG 2.2 ✓).
- **Show/hide password** toggle on both pages (accessible button with `aria-pressed`).
- **Strength meter** on register password, live-updates on input, ARIA-announces.
- **Inline match check** on confirm-password — shows an error under the field and blocks form submission without a second server round-trip.
- **"Forgot?"** link in the password row (placeholder — wired when email transport lands, see `DECISIONS.md` D13).
- Proper `autocomplete` hints: `email`, `current-password`, `new-password`, `name`.
- Safe-area-aware padding on phones (`padding: var(--space-3)` at ≤ 480 px).

## File-level diff, at a glance
| File | Before | After |
|---|---|---|
| `templates/login.html` | 178 lines, 138 lines of inline CSS | 95 lines, zero inline CSS |
| `templates/register.html` | 194 lines, same | 123 lines, zero inline CSS |
| `static/auth.css` | — | 155 lines, token-driven |
| `static/js/auth.js` | — | 85 lines (show/hide, strength meter, match check) |

## Accessibility receipts
Pulled from `verification.md`:
```
/login  -> ['PASS status 200', 'PASS has skip-link', 'PASS uses design-system.css',
           'PASS uses auth.css', 'PASS no inline <style>']
/register -> [same]
```

## Token examples used
```css
/* replaced inline #2563eb with */   background: var(--color-primary);
/* replaced inline 16px with */      border-radius: var(--radius-2xl);
/* replaced inline 0 4px 24px with */ box-shadow: var(--shadow-lg);
/* replaced inline transition: all with */ transition: background var(--transition-fast);
```
