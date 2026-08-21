"""Multi-factor authentication helpers: policy, session state and throttling."""

import time

from django.contrib.auth import get_user_model, login as auth_login
from django.core.cache import cache
from django.urls import NoReverseMatch, reverse
from django.utils.crypto import constant_time_compare

from .conf import get_config

#: Session key holding the half-finished login (password accepted, code pending).
CHALLENGE_SESSION_KEY = "_djadmin_mfa_challenge"
#: Session key holding the not-yet-confirmed secret during enrolment.
SETUP_SESSION_KEY = "_djadmin_mfa_setup_secret"


def options():
    return get_config()["MFA"]


def is_enabled():
    return bool(options()["ENABLED"])


def get_device(user, confirmed=True):
    """The user's authenticator, or None."""
    if user is None or not user.is_authenticated:
        return None
    from .models import MFADevice

    device = MFADevice.objects.filter(user=user).first()
    if device is None or (confirmed and not device.confirmed):
        return None
    return device


def has_mfa(user):
    return get_device(user) is not None


def is_required(user):
    """Does policy demand MFA for this user?"""
    if not is_enabled():
        return False
    required = options()["REQUIRED"]
    if required is True:
        return True
    if required == "superusers":
        return bool(getattr(user, "is_superuser", False))
    if required == "staff":
        return bool(getattr(user, "is_staff", False))
    return False


def should_challenge(user):
    """True when this login must be completed with a second factor."""
    return is_enabled() and has_mfa(user)


# -- the pending-login challenge -----------------------------------------


def begin_challenge(request, user, redirect_to=""):
    """Park a password-verified user until they pass the second factor."""
    request.session[CHALLENGE_SESSION_KEY] = {
        "user_id": str(user.pk),
        "backend": getattr(user, "backend", ""),
        "started": time.time(),
        "redirect_to": redirect_to or "",
    }
    request.session.modified = True


def get_challenge(request):
    """The pending challenge, or None when absent or expired."""
    data = request.session.get(CHALLENGE_SESSION_KEY)
    if not isinstance(data, dict):
        return None
    if time.time() - data.get("started", 0) > options()["CHALLENGE_TIMEOUT"]:
        clear_challenge(request)
        return None
    return data


def challenge_user(request):
    """The user behind the pending challenge, or None."""
    data = get_challenge(request)
    if not data:
        return None
    User = get_user_model()
    user = User.objects.filter(pk=data["user_id"]).first()
    if user is None or not user.is_active:
        clear_challenge(request)
        return None
    return user


def clear_challenge(request):
    if CHALLENGE_SESSION_KEY in request.session:
        del request.session[CHALLENGE_SESSION_KEY]
        request.session.modified = True


def complete_challenge(request, user):
    """Finish the login the password step started."""
    data = get_challenge(request) or {}
    clear_challenge(request)
    backend = data.get("backend") or None
    auth_login(request, user, backend=backend)
    return data.get("redirect_to") or ""


# -- brute-force throttling ----------------------------------------------


def _throttle_key(identifier, request):
    ip = (request.META.get("REMOTE_ADDR") or "?").replace(" ", "")
    return f"djadmin:mfa:attempts:{identifier}:{ip}"


def attempts_left(identifier, request):
    used = cache.get(_throttle_key(identifier, request), 0)
    return max(0, options()["MAX_ATTEMPTS"] - used)


def is_locked(identifier, request):
    return attempts_left(identifier, request) <= 0


def register_failure(identifier, request):
    key = _throttle_key(identifier, request)
    try:
        used = cache.incr(key)
    except ValueError:
        used = 1
        cache.set(key, used, options()["LOCKOUT_SECONDS"])
    if used >= options()["MAX_ATTEMPTS"]:
        # Re-set to refresh the lockout window once the limit is reached.
        cache.set(key, used, options()["LOCKOUT_SECONDS"])
    return used


def reset_failures(identifier, request):
    cache.delete(_throttle_key(identifier, request))


# -- enforcement ---------------------------------------------------------


def exempt_urls(site_name="admin"):
    """Admin URLs that must stay reachable while MFA is outstanding."""
    names = (
        "logout",
        "djadmin_security",
        "djadmin_mfa_setup",
        "djadmin_mfa_disable",
        "djadmin_mfa_recovery",
        "djadmin_mfa_verify",
        "password_change",
        "password_change_done",
        "jsi18n",
    )
    urls = set()
    for name in names:
        try:
            urls.add(reverse(f"{site_name}:{name}"))
        except NoReverseMatch:
            continue
    return urls


def enforcement_redirect(request, site_name="admin"):
    """URL to send an under-protected user to, or None when all is well."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not is_required(user):
        return None
    if has_mfa(user):
        return None
    if request.path in exempt_urls(site_name):
        return None
    try:
        return reverse(f"{site_name}:djadmin_mfa_setup")
    except NoReverseMatch:
        return None


def verify_url(site_name="admin"):
    try:
        return reverse(f"{site_name}:djadmin_mfa_verify")
    except NoReverseMatch:
        return reverse("admin:djadmin_mfa_verify")
