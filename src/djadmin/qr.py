"""QR rendering for authenticator enrolment.

Uses `segno <https://pypi.org/project/segno/>`_ when it is installed (pure
Python, no build step). Without it the setup page falls back to the secret in
manual-entry form, which every authenticator app accepts.
"""

import io

from django.utils.safestring import mark_safe


def available():
    try:
        import segno  # noqa: F401
    except ImportError:
        return False
    return True


def svg(data, scale=4, border=2):
    """Inline SVG for ``data``, or ``None`` when segno is not installed."""
    try:
        import segno
    except ImportError:
        return None
    try:
        # segno writes bytes, even for SVG.
        buffer = io.BytesIO()
        segno.make(data, error="m").save(
            buffer,
            kind="svg",
            scale=scale,
            border=border,
            dark="#111111",
            light="#ffffff",
            xmldecl=False,
            svgns=True,
            svgclass="dj-qr-svg",
            lineclass=None,
            omitsize=True,
        )
    except Exception:
        return None
    return mark_safe(buffer.getvalue().decode("utf-8"))
