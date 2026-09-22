import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

# A filter link somebody kept filters nothing rather than failing: neither of
# these is a mistake to report.


def chosen[M: Model](choices: QuerySet[M], raw: str) -> M | None:
    """The choice `raw` names, or None for one not on file or not a number."""
    return choices.filter(pk=raw).first() if raw.isdigit() else None


def date_given(raw: str) -> datetime.date | None:
    """The date `raw` gives as YYYY-MM-DD, or None for one that is not a date."""
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return None
