"""RFC 6238 (TOTP) and RFC 4226 (HOTP) — implemented on the standard library.

No third-party dependency: a TOTP verifier is ~40 lines of hmac. Codes produced
here work with Google Authenticator, 1Password, Aegis, Authy and friends.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

#: Seconds per code.
STEP = 30
#: Digits per code.
DIGITS = 6
#: How many steps either side of "now" are accepted (clock drift).
WINDOW = 1

_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def random_secret(length=32):
    """A fresh base32 secret (default 32 chars ≈ 160 bits)."""
    return "".join(secrets.choice(_B32_ALPHABET) for _ in range(length))


def _decode(secret):
    padded = secret.strip().replace(" ", "").upper()
    padded += "=" * (-len(padded) % 8)
    return base64.b32decode(padded, casefold=True)


def hotp(secret, counter, digits=DIGITS, digest=hashlib.sha1):
    """The HOTP value for ``counter``, zero-padded to ``digits``."""
    mac = hmac.new(_decode(secret), struct.pack(">Q", counter), digest).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def totp(secret, at=None, step=STEP, digits=DIGITS):
    """The current TOTP value."""
    return hotp(secret, counter_at(at, step), digits=digits)


def counter_at(at=None, step=STEP):
    return int((at if at is not None else time.time()) // step)


def verify(secret, token, at=None, window=WINDOW, step=STEP, digits=DIGITS, after=None):
    """Check ``token`` and return the counter it matched, else ``None``.

    ``after`` enforces single use: a counter at or below it is rejected, so a
    code that has already been accepted cannot be replayed within its window.
    Comparison is constant-time.
    """
    token = (token or "").strip().replace(" ", "")
    if not token.isdigit() or len(token) != digits:
        return None
    current = counter_at(at, step)
    for drift in range(-window, window + 1):
        counter = current + drift
        if counter < 0:
            continue
        if after is not None and counter <= after:
            continue
        if hmac.compare_digest(hotp(secret, counter, digits=digits), token):
            return counter
    return None


def provisioning_uri(secret, account, issuer, digits=DIGITS, step=STEP):
    """The ``otpauth://`` URI an authenticator app scans."""
    label = quote(f"{issuer}:{account}" if issuer else account, safe="")
    params = {
        "secret": secret,
        "algorithm": "SHA1",
        "digits": digits,
        "period": step,
    }
    if issuer:
        params["issuer"] = issuer
    return f"otpauth://totp/{label}?{urlencode(params)}"


def grouped(secret, size=4):
    """Format a secret for manual entry: ``ABCD EFGH IJKL``."""
    return " ".join(secret[index : index + size] for index in range(0, len(secret), size))
