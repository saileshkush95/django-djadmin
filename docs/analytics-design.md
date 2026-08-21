# djadmin analytics — design proposal

Status: **built, then removed on request.** The code is not in the tree; this
document is the design it was built from, kept so the work can be resumed
without redoing the thinking. Everything below was implemented and tested
before removal, so treat it as a specification with known-good numbers rather
than an untried plan.

Two changes to the plan, both at your request:

* The app lives **inside djadmin** as `djadmin.analytics` (app label
  `djanalytics`), not as a separate top-level distribution — but it is a
  separate Django *app* in every other sense: its own models, migrations,
  settings namespace, templates, static files and permissions. It does not
  import the rest of djadmin, and djadmin works completely without it. Whether
  it appears at all is decided by one INSTALLED_APPS entry, which
  `demo/config/settings_no_analytics.py` and `shop/test_optional_analytics.py`
  verify from both sides.
* Its raw tables are hidden from the sidebar (`hide_from_nav`), and excluded
  from the command palette's object search (`palette_search = False`).

Scope: lightweight, useful traffic and activity analytics for administrators.
Not a Google Analytics replacement. Explicitly out: heatmaps, session replay,
cohorts, funnels, attribution modelling, Kafka/BigQuery, websockets.

> **Tracking target: the public website, not the admin.**
> The middleware records traffic on your *site's* pages. The admin mount point
> (and static/media/health paths) is excluded by default and is not counted as
> traffic. What administrators do inside the admin is recorded separately as
> **activity** (audit), which is a different stream with different retention and
> a different permission.

---

## 1. Recommended architecture

A standalone, installable Django app — `djanalytics` — that knows nothing about
djadmin. djadmin gets a thin optional bridge.

```
src/djadmin/analytics/           # a Django app in its own right
├── apps.py       conf.py        # AnalyticsConfig, ANALYTICS settings      [1]
├── models.py     migrations/    # Visitor Session PageView Event + rollups [1]
├── identity.py                  # cookieless, rotating-salt visitor ids    [1]
├── useragent.py  sources.py     # device/browser/OS, referrer + UTM        [1]
├── geo.py        tenancy.py     # country resolution, tenant resolver      [1]
├── tracking.py   middleware.py  # the write path, and track()              [1]
├── admin.py                     # read-only tables                         [1]
├── charts.py                    # the SVG helpers the dashboard uses       [1]
├── tests/                       # 105 tests                                [1]
├── services/                    # ranges, aggregation, rollup              [2]
├── views.py      urls.py        # dashboard page + widget API              [3-5]
├── templates/djanalytics/       # dashboard + one file per widget          [3-5]
├── static/djanalytics/          # analytics.css, the optional beacon       [3-6]
└── management/commands/         # analytics_rollup, analytics_purge        [6]
```

The app owns its templates and assets, so removing it removes everything it
brought: djadmin's own stylesheet carries none of the dashboard's CSS, and the
page loads `djanalytics/css/analytics.css` itself. Every colour in that file
reads a djadmin token with a literal fallback, so the dashboard stays legible
if the app is ever used with a different admin skin.

`[n]` marks the phase that delivers each piece; phase 1 is done.

Two independent data planes:

| Plane | Source | Answers | Permission |
|---|---|---|---|
| **Traffic** | middleware on the public site (+ optional JS beacon) | visitors, sessions, page views, sources, devices, countries | `view_analytics` |
| **Activity** | Django signals (`LogEntry`, auth signals) and `track()` | who changed what, logins, custom events | `view_activity` |

Integration is one line — `"djanalytics"` in `INSTALLED_APPS` plus the
middleware. The djadmin bridge only adds a nav entry and mounts the dashboard
under the admin; nothing in `djanalytics` imports djadmin.

## 2. Django model design

Four write models plus two rollup tables.

```python
Visitor      id(uuid) tenant anon_id user? first_seen last_seen sessions_count
Session      id(uuid) tenant visitor started_at last_activity ended_at
             landing_path exit_path referrer_host source_type
             utm_source utm_medium utm_campaign
             device_type browser os country page_view_count is_bounce duration_s
PageView     id(bigint) tenant session visitor path title referrer_host
             timestamp duration_s status_code
Event        id(bigint) tenant name session? visitor? user? timestamp path
             metadata(JSONField)
```

Rollups (written by `analytics_rollup`, read by the dashboard):

```python
DailyStat        tenant date visitors new_visitors returning_visitors
                 sessions page_views bounces total_duration_s
DailyBreakdown   tenant date dimension value visitors sessions page_views
                 bounces total_duration_s
```

`DailyBreakdown` replaces the four separate `*DailyStats` tables from your
sketch: one table with a `dimension` column (`path`, `source`, `referrer`,
`country`, `device`, `browser`, `os`, `utm_source`, `event`). One schema, one
index strategy, one query shape — and adding a dimension later is a data change,
not a migration.

**Privacy by construction.** No IP address and no user agent string is stored.
`anon_id = HMAC(SECRET_KEY + daily_salt, ip + user_agent)` — a rotating daily
salt means a visitor cannot be followed across days, which keeps the module
cookie-free and consent-friendly. `user` is only set for authenticated requests.

## 3. Database indexes

```
Visitor        unique(tenant, anon_id) · (tenant, last_seen) · (user)
Session        (tenant, started_at) · (tenant, source_type, started_at)
               (visitor, started_at) · (tenant, country, started_at)
PageView       (tenant, timestamp) · (tenant, path, timestamp) · (session)
Event          (tenant, name, timestamp) · (tenant, timestamp) · (user, timestamp)
DailyStat      unique(tenant, date)
DailyBreakdown unique(tenant, date, dimension, value) · (tenant, dimension, date)
```

Every dashboard query starts with `tenant + a date column`, so every index is
led by exactly that. `path` is indexed with the timestamp because "top pages in
a range" is the one non-time-only grouping that runs on raw data.

## 4. Aggregation strategy

Three tiers, chosen automatically:

1. **Small installs (< ~100k page views/month, the default).** Query raw tables
   with `TruncHour/Day/Week` + `GROUP BY`, cached. No rollup job to operate.
2. **Rollups (`ANALYTICS["ROLLUPS"] = True`, or `"auto"` above a row threshold).**
   `analytics_rollup` recomputes whole days idempotently (safe to re-run, safe
   to backfill). Ranges older than today read `DailyStat` / `DailyBreakdown`;
   today reads raw and is added on. Dashboard cost becomes O(days), not O(hits).
3. **Retention.** Raw `PageView` older than `RAW_RETENTION_DAYS` (default 90) is
   deleted once its day is rolled up. Rollups are kept indefinitely — they are
   tiny.

Granularity is derived from the range, exactly as you specified: ≤ 1 day →
hourly, 2–31 days → daily, > 31 days → weekly, > 6 months → monthly. Bucketing
happens in SQL; raw rows never reach Python.

## 5. API design

Server-rendered first paint, then independent widget refreshes.

```
GET  /admin/analytics/                     the dashboard page
GET  /admin/analytics/api/overview         metric cards + comparison
GET  /admin/analytics/api/traffic          time series (metric=visitors|sessions|page_views)
GET  /admin/analytics/api/pages            top pages
GET  /admin/analytics/api/sources          traffic sources
GET  /admin/analytics/api/devices          device breakdown
GET  /admin/analytics/api/browsers         browser breakdown
GET  /admin/analytics/api/os               OS breakdown
GET  /admin/analytics/api/countries        country breakdown
GET  /admin/analytics/api/events           event counts
GET  /admin/analytics/api/activity         admin activity feed (audit)
GET  /admin/analytics/api/realtime         active-now count + last few hits
POST /analytics/collect/                   optional JS beacon (off by default)
```

Shared query parameters: `range` (`today`, `yesterday`, `last_7_days`,
`last_30_days`, `this_week`, `last_week`, `this_month`, `last_month`,
`this_year`, `custom`), `start` / `end` for custom, `compare=previous|none`,
`granularity=auto|hour|day|week|month`, `limit`, plus per-widget filters.

Every endpoint returns **aggregates only** — never raw rows — and each one
accepts `?format=fragment` to return rendered HTML instead of JSON, so widgets
work with JavaScript disabled and charts stay server-rendered SVG (the approach
already used on the djadmin dashboard: no chart library, no CDN).

## 6. Dashboard component structure

```
AnalyticsPage
├── RangeBar          range select + "compared with <previous period>" + Active now ●
├── MetricCards       Visitors · Sessions · Page views · New users ·
│                     Returning · Avg session · Bounce rate  (value, Δ%, vs prev)
├── TrafficChart      metric toggle, auto granularity, hover values
├── TopPages          page · views · visitors · avg duration · bounce (paged, top 10)
├── Sources           direct/search/social/referral/email/other + UTM detail
├── Devices | Browsers | OS      horizontal bars + %
├── Countries         table + bar, top 10
├── RecentActivity    "Anonymous visitor viewed /pricing · 3m ago"
└── UserAnalytics     total / active / new today / this week / this month, login trend
```

Each widget is a self-contained template + one aggregation function + one URL.
Adding a widget never touches another one.

## 7. Tracking strategy

**Server-side (default, no JavaScript).** `AnalyticsMiddleware` records a page
view when *all* of these hold: `GET`, 2xx, HTML response, path not excluded, UA
not a known bot. Default exclusions: the admin mount point, `STATIC_URL`,
`MEDIA_URL`, `/health`, `/favicon.ico`, `robots.txt`, and anything in
`ANALYTICS["EXCLUDE_PREFIXES"]`. Sessions close after 30 minutes of inactivity;
a session with one page view and no second hit is a bounce.

**Server-side events.**

```python
from djanalytics import analytics

analytics.track("product_created", user=request.user, request=request,
                metadata={"product_id": product.id})
```

`request` is optional — events work from management commands and tasks too.
Built-in receivers record `user_login`, `user_logout`, `login_failed`, and mirror
admin `LogEntry` rows into the activity feed.

**Browser beacon (optional, off by default).** A ~1KB `analytics.js` posting to
`/analytics/collect/` — only needed for pages served from a CDN/cache that the
middleware never sees, or for SPA route changes.

**Bots** are matched against a short UA pattern list and dropped before any
write.

## 8. Caching strategy

```
analytics:v{schema_version}:{tenant}:{widget}:{start}:{end}:{granularity}:{filters_hash}
```

| Data | TTL |
|---|---|
| Range entirely in the past | 10 minutes |
| Range including today | 60 seconds |
| Realtime / active now | 10 seconds |

`schema_version` is bumped by the rollup job, which invalidates every derived
value in one move without scanning keys. Uses Django's cache framework, so
LocMem works in development and Redis in production with no code change.

## 9. Permission strategy

Permissions live on a permissions-only model in the app:

```
analytics.view_analytics   traffic dashboard
analytics.view_activity    who-did-what audit feed
analytics.view_users       user-level and login analytics
analytics.view_revenue     reserved for commerce metrics
```

Each widget declares the permission it needs; the dashboard renders only the
widgets the user may see, and each API endpoint re-checks server-side (a missing
permission is a 403, not a hidden div). Superusers pass implicitly. Staff
without `view_analytics` do not see the nav entry at all.

## 10. Performance considerations

- **One query per widget, maximum.** No `count()` per card — the overview is a
  single grouped query returning every metric for both periods.
- **Never fetch raw rows for a chart.** All bucketing and top-N happens in SQL.
- **The write path stays cheap**: one INSERT (page view) plus one UPDATE
  (session `last_activity`) per tracked request, on indexes that are all
  append-friendly. `ANALYTICS["SAMPLE_RATE"]` can drop a fraction of hits on
  very high-traffic sites, and an optional queue hook defers writes when a task
  backend is configured.
- **A budget, enforced by tests**: the dashboard makes ≤ 10 queries cold and ≤ 2
  warm; `assertNumQueries` guards it so a regression fails CI.
- **The admin app never pays for analytics**: excluded paths short-circuit the
  middleware before any database work.

### Multi-tenancy

Every model carries a `tenant` column, populated by a resolver you configure:

```python
ANALYTICS = {"TENANT_RESOLVER": "myapp.tenancy.current_tenant"}  # default: django.contrib.sites, else None
```

Every query filters on the resolved tenant, so one tenant's data can never
appear in another's dashboard. With no tenancy configured the column is a
constant and the indexes behave exactly as a single-tenant install would.

---

## Proposed phases

Each phase ends with passing tests and a reviewable diff. Nothing starts until
you approve the phase.

| Phase | Deliverable |
|---|---|
| ~~1. Foundation~~ ✅ | app skeleton, four models + two rollups, migrations, indexes, settings, `track()`, middleware, bot/exclusion rules, UA + referrer classification, geo and tenancy resolvers, read-only admin |
| ~~2. Aggregation~~ ✅ | `services/ranges.py`, `services/aggregation.py`, versioned cache layer, query-count tests |
| ~~3. Dashboard core~~ ✅ | analytics page, range bar with comparison, seven metric cards, traffic chart with metric toggle and automatic granularity |
| ~~4. Breakdowns~~ ✅ | top pages, sources (+UTM), devices, browsers, OS, countries, events; JSON + HTML-fragment API for every widget |
| ~~5. Activity & realtime~~ ✅ | activity feed with an action filter, event feed, user + login analytics, "active now" with 30s polling |
| ~~6. Scale & polish~~ ✅ | `analytics_rollup` and `analytics_purge` commands, tenancy resolver, four permissions, optional JS beacon |

## Phase 1: what shipped, and the defaults it assumed

You had not answered the four questions, so phase 1 took the recommended
defaults; all four are settings, so nothing is locked in.

- **Country**: CDN header first (`CF-IPCountry`, `X-Country-Code`), optional
  GeoIP2 second (`ANALYTICS["GEOIP"]`), `""` (Unknown) otherwise.
- **Tenancy**: `django.contrib.sites` when installed, single tenant otherwise;
  override with `ANALYTICS["TENANT_RESOLVER"]`.
- **Retention**: `RAW_RETENTION_DAYS = 90` (the setting exists; the purge lands
  in phase 6).
- **Beacon**: server-side only. No JavaScript is served.

Measured on the demo: an excluded request (admin, static, bot, POST) costs
**0 queries**; a tracked page view costs **5**. Both numbers are asserted by
tests, so a regression fails the suite.

## Two definitions worth knowing

**"Returning" means a visitor with more than one session in the period.**
Because visitor ids rotate daily, that reads as *came back the same day*. It is
the honest limit of cookieless measurement, and the reason the dashboard never
claims month-over-month loyalty. Raw queries and rollups use the same
definition, so the two always agree.

**Rollup sums are near-exact, not approximations by design.** Summing daily
unique visitors equals the range total precisely because ids rotate daily — a
person genuinely is a different visitor tomorrow. The only drift comes from
sessions that straddle midnight, which appear in both days (well under 1% in
the demo data).

## Open settings, all with defaults

- **Country**: CDN header first (`CF-IPCountry`, `X-Country-Code`), optional
  GeoIP2 second (`ANALYTICS["GEOIP"]`), `""` (Unknown) otherwise.
- **Tenancy**: `django.contrib.sites` when installed, single tenant otherwise;
  override with `ANALYTICS["TENANT_RESOLVER"]`.
- **Retention**: `RAW_RETENTION_DAYS = 90`, enforced by `analytics_purge`.
- **Beacon**: shipped but inert until you route a URL to it.
