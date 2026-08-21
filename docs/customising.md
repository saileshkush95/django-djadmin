# Customising

## Design tokens

The whole interface is driven by CSS custom properties. Override them anywhere
after djadmin's stylesheet — the simplest place is a small file added through
`{% block extrastyle %}` in your own `admin/base_site.html`:

```css
:root {
  --dj-accent: #0f766e;
  --dj-radius-lg: 6px;      /* squarer cards */
  --dj-sidebar-w: 300px;
  --dj-row-y: 7px;          /* denser tables */
}
```

The tokens worth knowing:

| Group | Tokens |
|---|---|
| Colour | `--dj-accent`, `--dj-accent-fg`, `--dj-accent-soft` |
| Surfaces | `--dj-bg`, `--dj-surface`, `--dj-surface-2`, `--dj-surface-3` |
| Lines | `--dj-border`, `--dj-border-strong` |
| Text | `--dj-text`, `--dj-text-2`, `--dj-text-3` |
| Status | `--dj-success`, `--dj-warning`, `--dj-danger`, `--dj-info` (each with a `-bg`) |
| Shape | `--dj-radius-sm`, `--dj-radius`, `--dj-radius-lg` |
| Layout | `--dj-sidebar-w`, `--dj-topbar-h`, `--dj-gap`, `--dj-row-y` |
| Type | `--dj-font`, `--dj-font-mono` |

Dark mode redefines the same tokens under `:root[data-theme="dark"]` and under
`prefers-color-scheme: dark` for `auto`. Override those selectors too if your
accent needs to differ between themes.

Setting `DJADMIN["ACCENT"]` is the shortcut for the common case — it writes the
accent tokens inline for you.

## Template overrides

djadmin's templates are ordinary admin templates. To change one, put your own
copy earlier on the template search path (an app listed before `djadmin`, or a
`DIRS` entry):

```
templates/admin/base_site.html      your branding
templates/admin/index.html          your dashboard
templates/admin/change_list.html    your changelist
```

Blocks are kept compatible with the stock admin — `content`, `object-tools`,
`breadcrumbs`, `extrastyle`, `extrahead`, `bodyclass`, `usertools`, `sidebar`,
`footer` — so third-party admin templates written against Django still work.

Per-model overrides work as they always have:

```
templates/admin/shop/product/change_form.html
```

## Icons

Set them explicitly with `icon` on a ModelAdmin, or per project:

```python
DJADMIN = {
    "APP_ICONS": {"shop": "cart"},
    "MODEL_ICONS": {"shop.order": "cart", "shop.review": "star"},
}
```

Available ids:

```
alert bookmark box calendar card cart chart chat check chevron-down
chevron-right clock columns database external file filter folder globe grid
home image key layers list logout mail menu money monitor moon pencil plus
search settings shield sparkle star sun tag trash truck user users x
```

Unset icons are guessed from the model name: `Order` → cart, `Customer` →
users, `Invoice` → card, `Review` → star, and so on. An unrecognised name gets
a neutral box.

To add your own, override `djadmin/icons.html` and add a `<symbol>` with an id
of `dji-yourname`.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `⌘K` / `Ctrl+K` | Command palette |
| `/` | Focus the changelist search |
| `c` | Add a new record |
| `f` | Toggle the filters panel |
| `[` | Collapse or expand the sidebar |
| `⇧[` | Cycle sidebar: full → icons → hidden |
| `t` | Cycle the theme |
| `⌘S` | Save the current form |
| `?` | Show the shortcuts dialog |

Single-letter shortcuts are ignored while you are typing in a field.

## JavaScript hooks

Everything is progressive enhancement; these exist for project code that wants
to join in.

```js
window.djadminToast("Saved.", "success");   // success | info | warning | error
window.djadminTheme.cycle();                // and .set("dark"), .current()
window.djadminSidebar.toggle();             // and .cycle(), .set("mini")
window.djadminPalette.open();
```

A `djadmin:ready` event fires on `document` once the interface is wired up.
