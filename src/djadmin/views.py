"""Authentication views: the second factor, enrolment and the security page.

Each view takes the :class:`~djadmin.sites.DjadminSite` it belongs to so that
it can render inside the normal admin chrome (and so a project can run more
than one admin site).
"""

from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from . import mfa, qr, totp
from .conf import get_config
from .forms import PasswordConfirmForm, RecoveryCodeForm, TokenForm
from .models import MFADevice


class DjadminLoginView(LoginView):
    """Django's login view, paused for a second factor when one is enrolled."""

    def form_valid(self, form):
        user = form.get_user()
        if mfa.should_challenge(user):
            mfa.begin_challenge(self.request, user, self.get_success_url())
            return HttpResponseRedirect(mfa.verify_url(getattr(self.request, "current_app", "admin")))
        return super().form_valid(form)


def _issuer(site):
    config = get_config()
    return config["MFA"]["ISSUER"] or config["BRAND"] or str(site.site_header)


def _context(site, request, title, **extra):
    context = {**site.each_context(request), "title": title, "subtitle": None}
    context.update(extra)
    return context


def _safe_redirect(request, url, fallback):
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return fallback


# -- second factor at login ----------------------------------------------


def mfa_verify(request, site):
    """Second step of login: a TOTP code, or a recovery code."""
    user = mfa.challenge_user(request)
    login_url = reverse(f"{site.name}:login")
    if user is None:
        return redirect(login_url)

    device = mfa.get_device(user)
    if device is None:  # MFA was removed while the challenge was open
        mfa.complete_challenge(request, user)
        return redirect(reverse(f"{site.name}:index"))

    use_recovery = "recovery" in request.GET or "recovery_code" in request.POST
    form_class = RecoveryCodeForm if use_recovery else TokenForm
    identifier = f"user:{user.pk}"
    locked = mfa.is_locked(identifier, request)
    form = form_class()

    if request.method == "POST" and not locked:
        form = form_class(request.POST)
        if form.is_valid():
            if use_recovery:
                ok = device.verify_recovery_code(form.cleaned_data["recovery_code"])
            else:
                ok = device.verify_token(form.cleaned_data["token"])
            if ok:
                mfa.reset_failures(identifier, request)
                redirect_to = mfa.complete_challenge(request, user)
                if use_recovery:
                    messages.warning(
                        request,
                        _("You signed in with a recovery code. %(left)d code(s) remain.")
                        % {"left": device.unused_recovery_code_count},
                    )
                return redirect(_safe_redirect(request, redirect_to, reverse(f"{site.name}:index")))
            mfa.register_failure(identifier, request)
            locked = mfa.is_locked(identifier, request)
            form.add_error(
                None,
                _("That code is not valid. Codes expire every 30 seconds — try the next one.")
                if not use_recovery
                else _("That recovery code is not valid, or has already been used."),
            )

    context = _context(
        site,
        request,
        _("Two-factor authentication"),
        form=form,
        use_recovery=use_recovery,
        locked=locked,
        attempts_left=mfa.attempts_left(identifier, request),
        recovery_url=f"{reverse(f'{site.name}:djadmin_mfa_verify')}?recovery=1",
        verify_url=reverse(f"{site.name}:djadmin_mfa_verify"),
        login_url=login_url,
        masked_user=user.get_username(),
        has_recovery_codes=device.unused_recovery_code_count > 0,
    )
    return render(request, "djadmin/mfa_verify.html", context)


# -- enrolment and management --------------------------------------------


def security(request, site):
    """Account security overview: password, MFA status, recovery codes."""
    device = mfa.get_device(request.user)
    context = _context(
        site,
        request,
        _("Security"),
        device=device,
        mfa_enabled=mfa.is_enabled(),
        mfa_required=mfa.is_required(request.user),
        recovery_count=device.unused_recovery_code_count if device else 0,
        setup_url=reverse(f"{site.name}:djadmin_mfa_setup"),
        disable_url=reverse(f"{site.name}:djadmin_mfa_disable"),
        recovery_url=reverse(f"{site.name}:djadmin_mfa_recovery"),
        password_url=reverse(f"{site.name}:password_change"),
    )
    return render(request, "djadmin/security.html", context)


def mfa_setup(request, site):
    """Enrol an authenticator app: show a QR, confirm with a live code."""
    if not mfa.is_enabled():
        return redirect(reverse(f"{site.name}:index"))
    user = request.user
    if mfa.has_mfa(user) and "reset" not in request.GET:
        return redirect(reverse(f"{site.name}:djadmin_security"))

    secret = request.session.get(mfa.SETUP_SESSION_KEY)
    if not secret:
        secret = totp.random_secret()
        request.session[mfa.SETUP_SESSION_KEY] = secret

    form = TokenForm()
    if request.method == "POST":
        form = TokenForm(request.POST)
        if form.is_valid():
            counter = totp.verify(secret, form.cleaned_data["token"])
            if counter is None:
                form.add_error("token", _("That code did not match. Check your device's clock and try again."))
            else:
                device, _created = MFADevice.objects.update_or_create(
                    user=user,
                    defaults={
                        "secret": secret,
                        "confirmed": True,
                        "confirmed_at": timezone.now(),
                        "last_counter": counter,
                        "last_used_at": timezone.now(),
                    },
                )
                codes = device.issue_recovery_codes(get_config()["MFA"]["RECOVERY_CODES"])
                request.session.pop(mfa.SETUP_SESSION_KEY, None)
                messages.success(request, _("Two-factor authentication is on."))
                return render(
                    request,
                    "djadmin/mfa_codes.html",
                    _context(
                        site,
                        request,
                        _("Save your recovery codes"),
                        codes=codes,
                        security_url=reverse(f"{site.name}:djadmin_security"),
                    ),
                )

    uri = totp.provisioning_uri(secret, account=user.get_username(), issuer=_issuer(site))
    context = _context(
        site,
        request,
        _("Set up two-factor authentication"),
        form=form,
        secret=secret,
        secret_grouped=totp.grouped(secret),
        provisioning_uri=uri,
        qr=qr.svg(uri),
        mfa_required=mfa.is_required(user),
        security_url=reverse(f"{site.name}:djadmin_security"),
    )
    return render(request, "djadmin/mfa_setup.html", context)


def mfa_disable(request, site):
    """Turn MFA off — password required, and refused when policy demands it."""
    device = mfa.get_device(request.user)
    security_url = reverse(f"{site.name}:djadmin_security")
    if device is None:
        return redirect(security_url)
    if mfa.is_required(request.user):
        messages.error(request, _("Two-factor authentication is required for your account."))
        return redirect(security_url)

    form = PasswordConfirmForm(request.user)
    if request.method == "POST":
        form = PasswordConfirmForm(request.user, request.POST)
        if form.is_valid():
            device.delete()
            messages.warning(request, _("Two-factor authentication is off."))
            return redirect(security_url)

    context = _context(
        site,
        request,
        _("Turn off two-factor authentication"),
        form=form,
        security_url=security_url,
        action=_("Turn it off"),
        danger=True,
        explanation=_("Your account will be protected by a password alone."),
    )
    return render(request, "djadmin/confirm_password.html", context)


def mfa_recovery(request, site):
    """Issue a fresh set of recovery codes, invalidating the old ones."""
    device = mfa.get_device(request.user)
    security_url = reverse(f"{site.name}:djadmin_security")
    if device is None:
        return redirect(security_url)

    form = PasswordConfirmForm(request.user)
    if request.method == "POST":
        form = PasswordConfirmForm(request.user, request.POST)
        if form.is_valid():
            codes = device.issue_recovery_codes(get_config()["MFA"]["RECOVERY_CODES"])
            return render(
                request,
                "djadmin/mfa_codes.html",
                _context(
                    site,
                    request,
                    _("Save your recovery codes"),
                    codes=codes,
                    security_url=security_url,
                    regenerated=True,
                ),
            )

    context = _context(
        site,
        request,
        _("New recovery codes"),
        form=form,
        security_url=security_url,
        action=_("Generate new codes"),
        explanation=_("Your existing recovery codes stop working immediately."),
    )
    return render(request, "djadmin/confirm_password.html", context)
