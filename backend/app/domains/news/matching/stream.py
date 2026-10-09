"""公司档案的资讯流（confirmed + proposed links, newest first, cursor paged) and the 近期要点 digest.

R10a fixes the contract; the stream is implemented in R10b, the digest (scene ``company_digest``) in R12.
"""
from __future__ import annotations


def company_news(db, workspace_id: str, company_id: str, cursor: str | None = None, limit: int = 30) -> dict:
    """``{"items": [CompanyNewsItemOut], "next_cursor": str | None}``; the cursor is opaque
    (base64 of ``<published_at ISO>|<link id>``) and stable while new links arrive."""
    raise NotImplementedError('R10b: matching.stream.company_news')


def company_digest(db, workspace_id: str, company_id: str, days: int = 30, transport=None) -> dict:
    """LLM summary of the last ``days`` days of linked news (scene ``company_digest``)."""
    raise NotImplementedError('R12: matching.stream.company_digest')
