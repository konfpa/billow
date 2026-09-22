from typing import TYPE_CHECKING

from django import template

if TYPE_CHECKING:
    from decimal import Decimal

register = template.Library()

ICON = {
    "success": "check-circle-2",
    "warning": "alert-triangle",
    "error": "alert-circle",
}
TONE = {
    "success": "text-emerald-600",
    "warning": "text-amber-700",
    "error": "text-red-600",
}


# `tags` is space-separated and may carry more than the level, so each word is
# looked up rather than the whole string.
@register.filter
def message_icon(tags: str) -> str:
    return next((ICON[t] for t in tags.split() if t in ICON), "info")


@register.filter
def message_tone(tags: str) -> str:
    return next((TONE[t] for t in tags.split() if t in TONE), "text-zinc-500")


@register.filter
def initials(name: str) -> str:
    words = name.split()
    if not words:
        return ""
    return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()


# A rate is stored to six places, but 1 PCS = 20 ft reads better than
# 20.000000 ft.
@register.filter
def plain(number: Decimal) -> str:
    return f"{number.normalize():f}"
