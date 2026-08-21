# Authentication

djadmin adds time-based two-factor authentication (TOTP) to the admin login,
along with recovery codes and a per-account security page. It is implemented on
the standard library — `hmac`, `hashlib`, `secrets` — so there is no
authentication dependency to audit or keep patched.

Codes work with 1Password, Google Authenticator, Aegis, Authy and anything else
that speaks RFC 6238.

## Turning it on

It is on by default and opt-in per user: nothing changes until someone enrols.

```python
DJADMIN = {"MFA": {"ENABLED": True}}
```

For QR codes on the setup page:

```bash
pip install "django-djadmin[mfa]"
```

Without `segno` the setup page shows the secret in manual-entry form instead,
which every authenticator accepts.

## For a user

**User menu → Security** shows the state of the account: password, two-factor,
recovery codes.

1. **Turn on** walks through a QR code and asks for a live code, which proves
   the pairing works before anything is switched on.
2. **Ten recovery codes** are shown once, and only once. They are stored as
   keyed hashes, so the plain text exists for exactly that one page render.
3. On the next sign-in, the password step is followed by a six-digit code.
   "I lost my device" swaps the form for a recovery code, and each code works
   once.

## Requiring it

```python
DJADMIN = {"MFA": {"REQUIRED": "superusers"}}
```

| Value | Who must enrol |
|---|---|
| `False` | nobody (default) |
| `True` | everyone who can reach the admin |
| `"staff"` | users with `is_staff` |
| `"superusers"` | users with `is_superuser` |

A user in scope who has not enrolled is redirected to the setup page from any
admin URL, and cannot turn two-factor off again. The setup, security, logout,
password-change and jsi18n URLs stay reachable so the redirect cannot trap
anyone in a loop.

## How the login flow works

1. The password is checked by Django's own `AdminAuthenticationForm`.
2. If the account has a confirmed authenticator, the user is **not** logged in.
   The verified user id, the auth backend and the `next` URL are parked in the
   session, and the browser is redirected to the second step.
3. A correct code (or recovery code) completes the login through
   `django.contrib.auth.login`, which cycles the session key.
4. The parked challenge expires after `CHALLENGE_TIMEOUT` seconds (default 300).

Between steps two and three the user is anonymous: no session is authenticated,
so an abandoned challenge leaves nothing behind.

## What is stored, and what is not

| Stored | Not stored |
|---|---|
| The TOTP secret, per user | Anything derived from your password |
| A keyed hash of each recovery code | The recovery codes themselves |
| The last accepted TOTP counter | Any IP address or user agent |
| Timestamps: created, confirmed, last used | |

The secret is stored so codes can be verified; treat the database as
credential-bearing and encrypt it at rest if your threat model calls for it.

## Attack resistance

**Replay.** Every accepted code's counter is recorded, and a counter is never
accepted twice. A code shoulder-surfed inside its 30-second window is already
spent.

**Brute force.** Five wrong codes (`MAX_ATTEMPTS`) lock further attempts for
five minutes (`LOCKOUT_SECONDS`), keyed by user and client address. Six digits
is a million combinations; without a limit that is minutes of guessing.

**Clock drift.** One step either side of now is accepted — 90 seconds total.

**Timing.** Comparisons use `hmac.compare_digest` and Django's
`constant_time_compare`.

**Recovery-code hashing.** Codes are hashed with `salted_hmac` (SECRET_KEY as
the pepper), not a password hasher. They carry ~60 bits of entropy, so there is
nothing to brute-force offline — and verifying ten pbkdf2 hashes on every login
would add seconds for no gain.

## Managing other people's devices

Superusers can see enrolled authenticators at
`/admin/djadmin/mfadevice/` — who has two-factor on, when it was added, when it
was last used, and how many recovery codes remain. Secrets are never shown and
nothing is editable; the only action is **Revoke**, which forces that user to
enrol again. The list is deliberately kept out of the sidebar.

## Password reset

The admin's login page links to a reset flow when one is routed. djadmin styles
all four pages; wiring them is four URLs:

```python
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/password_reset/", auth_views.PasswordResetView.as_view(),
         name="admin_password_reset"),
    path("admin/password_reset/done/", auth_views.PasswordResetDoneView.as_view(),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(),
         name="password_reset_complete"),
    path("admin/", admin.site.urls),
]
```

The link appears by itself once `admin_password_reset` resolves.
