"""Small HTML helpers for ``list_display`` columns.

    from djadmin import badge, money

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), TONES[obj.status])
"""

from decimal import Decimal

from django.utils.html import format_html
from django.utils.safestring import mark_safe

#: Colour tones available to :func:`badge` and :func:`progress`.
TONES = ("neutral", "success", "warning", "danger", "info", "accent")


def _tone(tone):
    return tone if tone in TONES else "neutral"


def badge(text, tone="neutral", dot=False):
    """A pill-shaped status label."""
    marker = mark_safe('<span class="dj-badge-dot"></span>') if dot else ""
    return format_html(
        '<span class="dj-badge dj-badge--{}">{}{}</span>', _tone(tone), marker, text
    )


def money(amount, currency="$", tone=None):
    """A right-aligned, tabular-figures currency value."""
    if amount is None:
        return mark_safe('<span class="dj-muted">—</span>')
    value = Decimal(amount).quantize(Decimal("0.01"))
    classes = "dj-money" + (f" dj-money--{_tone(tone)}" if tone else "")
    return format_html('<span class="{}">{}{}</span>', classes, currency, f"{value:,}")


def progress(value, total=100, tone="accent", label=None):
    """A compact progress bar, useful for quotas and completion columns."""
    try:
        percent = max(0, min(100, round(float(value) / float(total) * 100)))
    except (TypeError, ValueError, ZeroDivisionError):
        percent = 0
    return format_html(
        '<span class="dj-progress" role="img" aria-label="{}">'
        '<span class="dj-progress-track"><span class="dj-progress-fill dj-progress-fill--{}"'
        ' style="width:{}%"></span></span><span class="dj-progress-label">{}</span></span>',
        label or f"{percent}%",
        _tone(tone),
        percent,
        label or f"{percent}%",
    )


def avatar(name, subtitle=None, image_url=None):
    """An identity cell: initials (or a photo) plus a name and subtitle."""
    initials = "".join(part[0] for part in str(name).split()[:2]).upper() or "?"
    if image_url:
        mark = format_html('<img class="dj-avatar-img" src="{}" alt="">', image_url)
    else:
        mark = format_html('<span class="dj-avatar-initials">{}</span>', initials)
    sub = format_html('<span class="dj-identity-sub">{}</span>', subtitle) if subtitle else ""
    return format_html(
        '<span class="dj-identity"><span class="dj-avatar">{}</span>'
        '<span class="dj-identity-text"><span class="dj-identity-name">{}</span>{}</span></span>',
        mark,
        name,
        sub,
    )
