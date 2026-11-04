from dataclasses import dataclass
from fastapi import Query

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageRequest:
    page: int
    pageSize: int

    # Returns the row offset a repository query starts at for this page.
    @property
    def offset(self):
        return pageOffset(self.page, self.pageSize)

# Converts a page number into the row offset a repository query starts at.
def pageOffset(page, pageSize):
    return (page - 1) * pageSize

# Parses the page and pageSize query parameters, refusing a page below 1 or a size above the cap.
def pageQuery(
    page: int = Query(default=DEFAULT_PAGE, ge=1),
    pageSize: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    return PageRequest(page=page, pageSize=pageSize)

# Builds the list envelope every paginated endpoint returns.
def paginatedResponse(items, total, paging):
    return {"items": items, "total": total, "page": paging.page, "pageSize": paging.pageSize}


__all__ = [
    "DEFAULT_PAGE",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "PageRequest",
    "pageOffset",
    "pageQuery",
    "paginatedResponse",
]
