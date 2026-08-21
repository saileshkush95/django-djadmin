"""Lightweight, dependency-free charts for the dashboard.

Everything here returns plain geometry (points, rects) that the templates draw
as inline SVG. No chart library, no JavaScript, no external requests — the
charts are part of the server-rendered page and work with JS disabled.
"""

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone


def daily_counts(queryset, field, days=30, now=None):
    """Zero-filled ``[(date, count)]`` for the last ``days`` days.

    Days with no rows still appear, so charts keep an even time axis.
    """
    now = now or timezone.now()
    today = timezone.localdate(now)
    start = today - timedelta(days=days - 1)
    counts = {}
    try:
        rows = (
            queryset.filter(**{f"{field}__date__gte": start})
            .annotate(_day=TruncDate(field))
            .values("_day")
            .annotate(_n=Count("pk"))
            .order_by()
        )
        for row in rows:
            if row["_day"]:
                counts[row["_day"]] = row["_n"]
    except Exception:
        # A model without a usable date field should never break the dashboard.
        return []
    return [(start + timedelta(days=offset), counts.get(start + timedelta(days=offset), 0)) for offset in range(days)]


def sparkline(values, width=120, height=30, pad=3):
    """Polyline geometry for a small trend line.

    Returns ``None`` when there is nothing to draw, so templates can simply
    test the value.
    """
    values = list(values)
    if len(values) < 2 or not any(values):
        return None
    top = max(values) or 1
    span = width - pad * 2
    step = span / (len(values) - 1)
    usable = height - pad * 2
    points = [
        (round(pad + index * step, 2), round(height - pad - (value / top) * usable, 2))
        for index, value in enumerate(values)
    ]
    line = " ".join(f"{x},{y}" for x, y in points)
    area = f"M{points[0][0]},{height} L" + " L".join(f"{x},{y}" for x, y in points) + f" L{points[-1][0]},{height} Z"
    return {
        "width": width,
        "height": height,
        "points": line,
        "area": area,
        "last_x": points[-1][0],
        "last_y": points[-1][1],
        "max": top,
    }


def bar_chart(series, height=100, bar=10, gap=3):
    """Rect geometry for a day-by-day bar chart.

    ``series`` is the ``[(date, count)]`` shape returned by :func:`daily_counts`.
    The SVG uses a viewBox and stretches to its container's width.
    """
    series = list(series)
    if not series:
        return None
    top = max(count for _date, count in series) or 1
    bars = []
    for index, (day, count) in enumerate(series):
        bar_height = round(count / top * (height - 4), 2) if count else 1.5
        bars.append(
            {
                "x": round(index * (bar + gap), 2),
                "y": round(height - bar_height, 2),
                "width": bar,
                "height": bar_height,
                "count": count,
                "date": day,
                "empty": not count,
            }
        )
    return {
        "bars": bars,
        "view_width": round(len(series) * (bar + gap) - gap, 2),
        "view_height": height,
        "max": top,
        "total": sum(count for _date, count in series),
        "first_date": series[0][0],
        "last_date": series[-1][0],
    }


def admin_activity(days=30, user=None, now=None):
    """Admin edits per day, split by action, from django.contrib.admin's log."""
    from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry

    queryset = LogEntry.objects.all()
    if user is not None:
        queryset = queryset.filter(user=user)
    chart = bar_chart(daily_counts(queryset, "action_time", days=days, now=now))
    if chart is None:
        return None
    since = (now or timezone.now()) - timedelta(days=days)
    recent = queryset.filter(action_time__gte=since)
    counts = {row["action_flag"]: row["_n"] for row in recent.values("action_flag").annotate(_n=Count("pk"))}
    chart.update(
        {
            "days": days,
            "additions": counts.get(ADDITION, 0),
            "changes": counts.get(CHANGE, 0),
            "deletions": counts.get(DELETION, 0),
        }
    )
    return chart

