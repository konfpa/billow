from django import template

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
