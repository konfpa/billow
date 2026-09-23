"""One page of a directory, so a register that grows never arrives whole.

A directory used to render every record it had. At a few hundred that is a
large page; at ten thousand it is a megabyte of markup and a browser that
stutters on every scroll, and no Operator reads past the first screen of it
anyway.
"""

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.core.paginator import Paginator

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

# Enough that paging is rare for a Business with an ordinary register, and few
# enough that the page stays light for one with a long one.
PER_PAGE = 50


def paged(request: HttpRequest, records: QuerySet, per_page: int = PER_PAGE) -> dict:
    """The page asked for, the window of page numbers, and the filters to keep.

    `get_page` rather than `page`: a bookmarked `?page=98` of a directory that
    has since shrunk lands on the last page instead of raising, and so does a
    page number that is not a number at all.
    """
    paginator = Paginator(records, per_page)
    page = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page,
        # Django draws the same seven slots the pager does — first, a gap or a
        # page, three around the current one, a gap or a page, last — so the
        # row does not change width as somebody walks it. It takes arguments,
        # which a template call cannot pass, so it is built here.
        "page_range": paginator.get_elided_page_range(
            page.number, on_each_side=1, on_ends=1
        ),
        # What the search and the filters were, carried onto every page link.
        # Without it page 2 of a search is page 2 of everything.
        "kept_query": urlencode(
            {
                name: value
                for name, value in request.GET.items()
                if name != "page" and value
            }
        ),
    }
