"""Models backing djadmin's multi-factor authentication."""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import gettext_lazy as _

from . import totp

RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alikes


def hash_recovery_code(code):
    """Hash a recovery code with SECRET_KEY as the pepper.

    Recovery codes carry ~60 bits of entropy, so a keyed hash is the right
    tool — unlike a password, there is nothing here to brute-force offline.
    """
    normalized = (code or "").strip().lower().replace("-", "").replace(" ", "")
    return salted_hmac("djadmin.recovery-code", normalized).hexdigest()


class MFADevice(models.Model):
    """One TOTP authenticator per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="djadmin_mfa",
        verbose_name=_("user"),
    )
    secret = models.CharField(_("secret"), max_length=64)
    confirmed = models.BooleanField(_("confirmed"), default=False)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    last_used_at = models.DateTimeField(_("last used"), null=True, blank=True)
    #: Highest TOTP counter already accepted — blocks replay of a live code.
    last_counter = models.BigIntegerField(_("last counter"), default=0)

    class Meta:
        verbose_name = _("authenticator")
        verbose_name_plural = _("authenticators")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} · {'active' if self.confirmed else 'pending'}"

    # -- verification ----------------------------------------------------

    def verify_token(self, token, at=None):
        """Verify a TOTP code, consuming its counter on success."""
        counter = totp.verify(self.secret, token, at=at, after=self.last_counter)
        if counter is None:
            return False
        self.last_counter = counter
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_counter", "last_used_at"])
        return True

    def verify_recovery_code(self, code):
        """Spend a recovery code. Each one works exactly once."""
        digest = hash_recovery_code(code)
        for candidate in self.recovery_codes.filter(used_at__isnull=True):
            if constant_time_compare(candidate.code_hash, digest):
                candidate.used_at = timezone.now()
                candidate.save(update_fields=["used_at"])
                self.last_used_at = candidate.used_at
                self.save(update_fields=["last_used_at"])
                return True
        return False

    # -- recovery codes --------------------------------------------------

    def issue_recovery_codes(self, count=RECOVERY_CODE_COUNT):
        """Replace every recovery code and return the new ones in plain text.

        This is the only moment the codes exist unhashed — show them once.
        """
        self.recovery_codes.all().delete()
        codes = []
        for _index in range(count):
            raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
            codes.append(f"{raw[:5]}-{raw[5:]}")
        RecoveryCode.objects.bulk_create(
            [RecoveryCode(device=self, code_hash=hash_recovery_code(code)) for code in codes]
        )
        return codes

    @property
    def unused_recovery_code_count(self):
        return self.recovery_codes.filter(used_at__isnull=True).count()


class RecoveryCode(models.Model):
    """A single-use backup code for when the authenticator is unavailable."""

    device = models.ForeignKey(MFADevice, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("recovery code")
        verbose_name_plural = _("recovery codes")
        ordering = ("id",)

    def __str__(self):
        return f"{'used' if self.used_at else 'unused'} recovery code"
