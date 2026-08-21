# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-08-21

First release.

### The shell
- Sidebar navigation grouped by app, with per-model icons; collapses to an icon
  rail or closes entirely (`SIDEBAR_TOGGLE`), with an animated transition.
- Command palette (`⌘K`) that searches registered models and their records.
- Light / dark / system theme applied before first paint.
- Keyboard shortcuts: `/` search, `c` add, `f` filters, `[` sidebar, `t` theme,
  `⌘S` save, `?` help.
- Toast messages, sticky save bar, responsive layout, RTL stylesheet.

### Dashboard
- Per-model stat cards with a 14-day sparkline and week-over-week delta.
- Admin activity chart for the last 30 days, as server-rendered inline SVG.
- Recent-actions timeline.

### Changelist
- Sticky-header tables, a filter panel that remembers its state, removable
  filter chips and a floating bulk-action bar that appears on selection.
- `badge()`, `money()`, `progress()` and `avatar()` helpers for `list_display`.

### Forms
- Card fieldsets, collapsible sections, restyled inlines, related-object
  widgets, calendar and clock popups, `filter_horizontal` and select2.
- Delete confirmations in a dialog, fetched from Django's own confirmation
  view so permissions and the deletion tree stay server-side; falls back to the
  full page without JavaScript.
- Unsaved-changes guard on change forms.

### Authentication
- TOTP two-factor authentication (RFC 6238) implemented on the standard
  library, with QR enrolment when `segno` is installed.
- Single-use recovery codes stored as keyed hashes.
- Replay protection, attempt throttling with lockout, expiring challenges.
- A per-account security page and an optional site-wide MFA requirement.
- Styled password change and password reset flows.

[0.1.0]: https://github.com/saileshkush95/django-djadmin/releases/tag/v0.1.0
