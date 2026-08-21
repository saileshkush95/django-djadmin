# Configuration

Everything is optional. Put what you want in a `DJADMIN` dict:

```python
DJADMIN = {
    "BRAND": "Northwind",
    "ACCENT": "#5b5bd6",
    "MFA": {"REQUIRED": "superusers"},
}
```

Nested dicts merge key by key, so setting one `MFA` option keeps the defaults
for the rest.

## Branding

| Setting | Default | Meaning |
|---|---|---|
| `BRAND` | the admin site header | Name shown in the sidebar and on the login card |
| `BRAND_SHORT` | first letter of `BRAND` | The square letter mark |
| `LOGO_URL` | `None` | An image URL rendered instead of the letter mark |
| `FOOTER` | `None` | A line of text at the bottom of the sidebar |

## Appearance

| Setting | Default | Meaning |
|---|---|---|
| `ACCENT` | `"#4f46e5"` | Accent colour; everything else derives from it |
| `ACCENT_FG` | `"#ffffff"` | Text colour on top of the accent |
| `THEME` | `"auto"` | `auto` \| `light` \| `dark` — the default before a user chooses |
| `DENSITY` | `"comfortable"` | `comfortable` \| `compact` — table and form row height |

A user's own theme choice is stored in `localStorage` and applied before first
paint, so there is no flash of the wrong palette.

## Navigation

| Setting | Default | Meaning |
|---|---|---|
| `SIDEBAR` | `"expanded"` | Initial state: `expanded` \| `mini` \| `hidden` |
| `SIDEBAR_TOGGLE` | `"mini"` | What the toggle collapses *to*: `mini` (icon rail) or `hidden` |
| `NAV_ACCORDION` | `False` | `True` keeps only one app group open at a time |
| `APP_ICONS` | `{}` | `{"shop": "cart"}` |
| `MODEL_ICONS` | `{}` | `{"shop.order": "cart"}` |
| `HIDE_APPS` | `[]` | App labels to keep out of the sidebar |

An app can also keep itself out of the sidebar without any project setting:

```python
class MyAppConfig(AppConfig):
    hide_from_nav = True
```

Icons are guessed from model names when you do not set them — a model called
`Order` gets a cart, `Customer` gets people. See
[Customising](customising.md#icons) for the full list.

## Features

| Setting | Default | Meaning |
|---|---|---|
| `COMMAND_PALETTE` | `True` | The ⌘K palette |
| `DASHBOARD_STATS` | `True` | Per-model stat cards on the dashboard |
| `DASHBOARD_ANALYTICS` | `True` | Sparklines and the admin-activity chart |
| `ANALYTICS_DAYS` | `30` | Days covered by the activity chart |
| `TOASTS` | `True` | Messages as toasts rather than a banner |
| `CONFIRM_MODAL` | `True` | Delete confirmations in a dialog |
| `STICKY_SUBMIT` | `True` | The save bar follows you down long forms |

## Command palette

| Setting | Default | Meaning |
|---|---|---|
| `SEARCH_MODEL_LIMIT` | `6` | Models queried for records per keystroke |
| `SEARCH_OBJECT_LIMIT` | `5` | Records returned per model |

These bound the work one keystroke can cause. A model only takes part if its
`ModelAdmin` defines `search_fields`; see
[`palette_search`](modeladmin.md#palette_search) to exclude one.

## Two-factor authentication

```python
DJADMIN = {
    "MFA": {
        "ENABLED": True,
        "REQUIRED": False,          # False | True | "staff" | "superusers"
        "ISSUER": None,             # authenticator app label; defaults to BRAND
        "CHALLENGE_TIMEOUT": 300,   # seconds to finish the second step
        "MAX_ATTEMPTS": 5,          # wrong codes before a lockout
        "LOCKOUT_SECONDS": 300,
        "RECOVERY_CODES": 10,
    },
}
```

See [Authentication](authentication.md).
