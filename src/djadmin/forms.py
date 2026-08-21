"""Forms for the second authentication factor."""

from django import forms
from django.utils.translation import gettext_lazy as _


class TokenForm(forms.Form):
    """A six-digit code from an authenticator app."""

    token = forms.CharField(
        label=_("Authentication code"),
        max_length=8,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
                "autofocus": True,
                "placeholder": "123456",
                "class": "dj-otp-input",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data["token"].replace(" ", "")
        if not token.isdigit():
            raise forms.ValidationError(_("Enter the six digits shown in your authenticator app."))
        return token


class RecoveryCodeForm(forms.Form):
    """One of the single-use backup codes."""

    recovery_code = forms.CharField(
        label=_("Recovery code"),
        max_length=32,
        strip=True,
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "autofocus": True, "placeholder": "abcde-fghij"}
        ),
    )


class PasswordConfirmForm(forms.Form):
    """Re-authentication before a security setting changes."""

    password = forms.CharField(
        label=_("Your password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "autofocus": True}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("That password is not correct."))
        return password
