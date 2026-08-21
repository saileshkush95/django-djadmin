"""Tests for djadmin's authentication: login, MFA, recovery codes, policy.

Run with:  uv run demo/manage.py test shop
"""

import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from djadmin import mfa, totp
from djadmin.models import MFADevice

PASSWORD = "correct-horse-battery"


def mfa_settings(**overrides):
    """DJADMIN settings with an MFA block, for override_settings."""
    return {"BRAND": "Northwind", "MFA": {"ENABLED": True, **overrides}}


class TOTPTests(TestCase):
    def test_code_verifies_within_the_drift_window(self):
        secret = totp.random_secret()
        now = time.time()
        self.assertIsNotNone(totp.verify(secret, totp.totp(secret, at=now), at=now))
        # One step early or late still passes (clock drift).
        self.assertIsNotNone(totp.verify(secret, totp.totp(secret, at=now - 30), at=now))
        self.assertIsNotNone(totp.verify(secret, totp.totp(secret, at=now + 30), at=now))
        # Two steps out does not.
        self.assertIsNone(totp.verify(secret, totp.totp(secret, at=now - 90), at=now))

    def test_garbage_is_rejected(self):
        secret = totp.random_secret()
        for token in ("", "abcdef", "12345", "1234567", None):
            self.assertIsNone(totp.verify(secret, token))

    def test_counter_cannot_be_replayed(self):
        secret = totp.random_secret()
        now = time.time()
        counter = totp.verify(secret, totp.totp(secret, at=now), at=now)
        self.assertIsNone(totp.verify(secret, totp.totp(secret, at=now), at=now, after=counter))

    def test_provisioning_uri_is_scannable(self):
        uri = totp.provisioning_uri("ABCDEFGH", account="ada", issuer="Northwind")
        self.assertTrue(uri.startswith("otpauth://totp/Northwind%3Aada?"))
        self.assertIn("secret=ABCDEFGH", uri)
        self.assertIn("issuer=Northwind", uri)


class MFALoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_superuser("ada", "ada@example.com", PASSWORD)
        cls.plain = User.objects.create_superuser("bob", "bob@example.com", PASSWORD)
        cls.secret = totp.random_secret()
        cls.device = MFADevice.objects.create(user=cls.user, secret=cls.secret, confirmed=True)
        cls.codes = cls.device.issue_recovery_codes(10)

    def setUp(self):
        cache.clear()
        self.login_url = reverse("admin:login")
        self.verify_url = reverse("admin:djadmin_mfa_verify")

    def _password_step(self, username="ada"):
        return self.client.post(
            self.login_url, {"username": username, "password": PASSWORD, "next": "/admin/"}
        )

    def test_password_alone_does_not_sign_in_an_mfa_user(self):
        response = self._password_step()
        self.assertRedirects(response, self.verify_url, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIsNotNone(self.client.session.get(mfa.CHALLENGE_SESSION_KEY))

    def test_user_without_mfa_signs_in_normally(self):
        response = self._password_step(username="bob")
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.plain.pk))

    def test_valid_code_completes_the_login(self):
        self._password_step()
        response = self.client.post(self.verify_url, {"token": totp.totp(self.secret)})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_verify_page_renders_the_djadmin_shell(self):
        self._password_step()
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-auth-card")
        self.assertContains(response, "Two-factor authentication")

    def test_wrong_code_keeps_the_user_out(self):
        self._password_step()
        response = self.client.post(self.verify_url, {"token": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "not valid")

    def test_code_cannot_be_replayed(self):
        self._password_step()
        token = totp.totp(self.secret)
        self.client.post(self.verify_url, {"token": token})
        self.client.logout()
        self._password_step()
        self.client.post(self.verify_url, {"token": token})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_repeated_failures_lock_the_challenge(self):
        self._password_step()
        for _attempt in range(5):
            self.client.post(self.verify_url, {"token": "000000"})
        response = self.client.post(self.verify_url, {"token": totp.totp(self.secret)})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Too many incorrect codes")

    def test_recovery_code_works_once(self):
        code = self.codes[0]
        self._password_step()
        response = self.client.post(f"{self.verify_url}?recovery=1", {"recovery_code": code})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

        self.client.logout()
        self._password_step()
        self.client.post(f"{self.verify_url}?recovery=1", {"recovery_code": code})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_recovery_codes_are_not_stored_in_plain_text(self):
        stored = list(self.device.recovery_codes.values_list("code_hash", flat=True))
        for code in self.codes:
            self.assertNotIn(code, stored)

    def test_challenge_expires(self):
        self._password_step()
        session = self.client.session
        data = session[mfa.CHALLENGE_SESSION_KEY]
        data["started"] = time.time() - 10_000
        session[mfa.CHALLENGE_SESSION_KEY] = data
        session.save()
        response = self.client.post(self.verify_url, {"token": totp.totp(self.secret)})
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_verify_url_without_a_challenge_bounces_to_login(self):
        response = self.client.get(self.verify_url)
        self.assertRedirects(response, self.login_url, fetch_redirect_response=False)


class MFAEnrolmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("ada", "ada@example.com", PASSWORD)

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)
        self.setup_url = reverse("admin:djadmin_mfa_setup")
        self.security_url = reverse("admin:djadmin_security")

    def test_security_page_lists_the_controls(self):
        response = self.client.get(self.security_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-factor authentication")
        self.assertContains(response, "Change password")

    def test_setup_offers_a_secret_and_a_qr(self):
        response = self.client.get(self.setup_url)
        self.assertEqual(response.status_code, 200)
        secret = self.client.session[mfa.SETUP_SESSION_KEY]
        self.assertEqual(len(secret), 32)
        self.assertContains(response, "otpauth" if response.context["qr"] is None else "<svg")

    def test_confirming_a_live_code_enables_mfa_and_shows_codes(self):
        self.client.get(self.setup_url)
        secret = self.client.session[mfa.SETUP_SESSION_KEY]
        response = self.client.post(self.setup_url, {"token": totp.totp(secret)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-codes")
        device = MFADevice.objects.get(user=self.user)
        self.assertTrue(device.confirmed)
        self.assertEqual(device.unused_recovery_code_count, 10)
        self.assertEqual(len(response.context["codes"]), 10)
        self.assertNotIn(mfa.SETUP_SESSION_KEY, self.client.session)

    def test_a_wrong_code_does_not_enable_mfa(self):
        self.client.get(self.setup_url)
        response = self.client.post(self.setup_url, {"token": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MFADevice.objects.filter(user=self.user).exists())

    def test_disable_requires_the_password(self):
        device = MFADevice.objects.create(user=self.user, secret=totp.random_secret(), confirmed=True)
        disable_url = reverse("admin:djadmin_mfa_disable")
        self.client.post(disable_url, {"password": "wrong"})
        self.assertTrue(MFADevice.objects.filter(pk=device.pk).exists())
        self.client.post(disable_url, {"password": PASSWORD})
        self.assertFalse(MFADevice.objects.filter(pk=device.pk).exists())

    def test_regenerating_codes_invalidates_the_old_ones(self):
        device = MFADevice.objects.create(user=self.user, secret=totp.random_secret(), confirmed=True)
        old = device.issue_recovery_codes(10)
        response = self.client.post(reverse("admin:djadmin_mfa_recovery"), {"password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        new = response.context["codes"]
        self.assertEqual(len(new), 10)
        self.assertFalse(set(old) & set(new))
        self.assertFalse(device.verify_recovery_code(old[0]))
        self.assertTrue(device.verify_recovery_code(new[0]))


@override_settings(DJADMIN=mfa_settings(REQUIRED=True))
class MFAPolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("ada", "ada@example.com", PASSWORD)

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)

    def test_admin_pages_redirect_to_setup_until_mfa_is_on(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(
            response, reverse("admin:djadmin_mfa_setup"), fetch_redirect_response=False
        )

    def test_setup_page_itself_stays_reachable(self):
        response = self.client.get(reverse("admin:djadmin_mfa_setup"))
        self.assertEqual(response.status_code, 200)

    def test_enrolled_users_are_not_redirected(self):
        MFADevice.objects.create(user=self.user, secret=totp.random_secret(), confirmed=True)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_required_mfa_cannot_be_switched_off(self):
        device = MFADevice.objects.create(user=self.user, secret=totp.random_secret(), confirmed=True)
        self.client.post(reverse("admin:djadmin_mfa_disable"), {"password": PASSWORD})
        self.assertTrue(MFADevice.objects.filter(pk=device.pk).exists())


@override_settings(DJADMIN={"MFA": {"ENABLED": False}})
class MFADisabledTests(TestCase):
    def test_login_skips_the_second_factor_when_mfa_is_off(self):
        user = get_user_model().objects.create_superuser("ada", "ada@example.com", PASSWORD)
        MFADevice.objects.create(user=user, secret=totp.random_secret(), confirmed=True)
        response = self.client.post(
            reverse("admin:login"), {"username": "ada", "password": PASSWORD, "next": "/admin/"}
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)


class PasswordResetTests(TestCase):
    def test_reset_page_uses_the_djadmin_layout(self):
        response = self.client.get(reverse("admin_password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dj-auth-card")
        self.assertContains(response, "Reset your password")

    def test_login_page_links_to_the_reset_flow(self):
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, reverse("admin_password_reset"))
