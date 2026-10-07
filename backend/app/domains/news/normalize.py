"""Turn the daily Excel sheets (and RSS entries) into one normalized record shape.

The six human-run feeds each used their own columns. Headers are matched through
``column_synonyms`` in config/news-radar-v1.json, the header row is found
automatically (titles/date banners above it are skipped), and placeholder rows such
as "今日无重要动态" are dropped.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domains.news.policy import policy


@dataclass
class Record:
    title: str
    summary: str = ''
    source_text: str | None = None
    url: str | None = None
    category: str | None = None
    company_hint: str | None = None
    note: str | None = None
    published_at: datetime | None = None
    raw: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        basis = '|'.join([normalize_title(self.title), (self.url or '').strip(),
                          self.published_at.date().isoformat() if self.published_at else ''])
        return hashlib.sha256(basis.encode()).hexdigest()


_PUNCT = re.compile(r'[\s\W_]+', re.UNICODE)


def normalize_title(title: str) -> str:
    return _PUNCT.sub('', (title or '').lower())


def feed_key_from_filename(filename: str) -> tuple[str, str]:
    """'创新药每日动态_2026-09-30.xlsx' -> ('创新药每日动态', '创新药每日动态')."""
    stem = re.sub(r'\.(xlsx|xlsm|xls)$', '', filename.rsplit('/', 1)[-1], flags=re.I)
    name = re.sub(r'[_\-\s]*\d{4}-?\d{2}-?\d{2}$', '', stem).strip(' _-') or stem
    return name, name


_DATE = re.compile(r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?(?:\s*(\d{1,2}):(\d{2}))?')


def parse_published(value, tz: str | None = None) -> datetime | None:
    zone = ZoneInfo(tz or policy()['timezone'])
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=zone)
    if hasattr(value, 'year') and hasattr(value, 'month'):
        return datetime.combine(value, time(0, 0), zone)
    m = _DATE.search(str(value))
    if not m:
        return None
    y, mo, d, hh, mm = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), tzinfo=zone)
    except ValueError:
        return None


def _header_index(header: list) -> dict[str, int]:
    synonyms = policy()['column_synonyms']
    cells = [str(c).strip() if c is not None else '' for c in header]
    index = {}
    for field_name, names in synonyms.items():
        for name in names:
            if name in cells:
                index[field_name] = cells.index(name)
                break
    return index


def _is_header(row: list) -> bool:
    idx = _header_index(row)
    return ('title' in idx or 'person' in idx) and ('summary' in idx or 'published' in idx)


def _skip(title: str) -> bool:
    return not title or any(p in title for p in policy()['skip_title_patterns'])


def records_from_rows(rows: list[list]) -> list[Record]:
    header_at = next((i for i, r in enumerate(rows) if _is_header(list(r))), None)
    if header_at is None:
        return []
    header = [str(c).strip() if c is not None else '' for c in rows[header_at]]
    idx = _header_index(header)
    out = []
    section = None  # '◆ 诺诚健华（688428.SH / 09969.HK）' banners group rows by company
    for row in rows[header_at + 1:]:
        row = list(row) + [None] * (len(header) - len(row))
        first = str(row[0]).strip() if row[0] is not None else ''
        if first.startswith('◆'):
            section = first.lstrip('◆ ').strip()
            continue

        def get(name):
            if name not in idx:
                return None
            v = row[idx[name]]
            return None if v is None else (v if isinstance(v, datetime) else str(v).strip()) or None

        title = get('title')
        if not title and get('person'):
            title = f"{get('person')}｜{get('source_text') or get('company_hint') or '访谈'}"
        title = (title or '').strip()
        summary = get('summary') or ''
        if _skip(title) or (not summary and not get('url') and _skip(summary or title)):
            continue
        raw = {h: (row[i].isoformat() if isinstance(row[i], datetime) else row[i]) for i, h in enumerate(header) if h}
        out.append(Record(title=title[:500], summary=summary, source_text=(get('source_text') or None),
                          url=get('url'), category=get('category'), company_hint=section or get('company_hint'),
                          note=get('note'), published_at=parse_published(get('published')), raw=raw))
    return out


def records_from_excel(data: bytes) -> list[Record]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out = []
    for sheet in wb.worksheets:
        out.extend(records_from_rows([list(r) for r in sheet.iter_rows(values_only=True)]))
    return out


def records_from_rss(xml_text: str) -> list[Record]:
    """RSS 2.0 or Atom."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    root = ET.fromstring(xml_text)
    atom = '{http://www.w3.org/2005/Atom}'
    out = []
    for node in root.iter():
        tag = node.tag
        if tag not in ('item', atom + 'entry'):
            continue
        def text(*names):
            for n in names:
                el = node.find(n)
                if el is not None:
                    return (el.text or el.get('href') or '').strip()
            return ''
        title = text('title', atom + 'title')
        if _skip(title):
            continue
        link = text('link', atom + 'link')
        when = text('pubDate', atom + 'updated', atom + 'published')
        try:
            published = parsedate_to_datetime(when) if when and not when[:4].isdigit() else parse_published(when)
        except (TypeError, ValueError):
            published = parse_published(when)
        summary = re.sub(r'<[^>]+>', '', text('description', atom + 'summary', atom + 'content'))
        out.append(Record(title=title[:500], summary=summary, url=link or None, published_at=published,
                          raw={'title': title, 'link': link, 'published': when}))
    return out
