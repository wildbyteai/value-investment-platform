"""Standard list paging: ``?limit=&offset=`` in, ``{items, total, limit, offset}`` out."""
from dataclasses import dataclass

from fastapi import Query

MAX_LIMIT = 200


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def page_params(limit: int = Query(50, ge=1, le=MAX_LIMIT, description='每页条数'),
                offset: int = Query(0, ge=0, description='跳过条数')) -> PageParams:
    return PageParams(limit=limit, offset=offset)


def page(items: list, total: int, params: PageParams) -> dict:
    return {'items': items, 'total': total, 'limit': params.limit, 'offset': params.offset}
