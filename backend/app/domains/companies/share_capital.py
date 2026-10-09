"""Reviewed point-in-time ordinary capital, separate from report-period facts."""
import re
from datetime import date, datetime
from decimal import Decimal
from app.domains.companies.original_financials import FinancialGap, number
from app.domains.platform.transactions import digest


def references(refs):
    if not isinstance(refs, list) or not refs or any(
        r.get('synthetic') is not False or not r.get('source_revision_id') or
        not re.fullmatch('[0-9a-f]{64}', r.get('hash', '')) or not r.get('locator')
        for r in refs):
        raise FinancialGap('股本原文修订/hash/定位不完整')
    return refs


def normalize(bundle):
    as_of=date.fromisoformat(bundle['shares_as_of'])
    through=date.fromisoformat(bundle['ordinary_shares_verified_through'])
    if through < as_of:raise FinancialGap('股本覆盖截止早于结存日')
    if bundle.get('scope')!='parent_ordinary' or bundle.get('complete_classes_confirmed') is not True:
        raise FinancialGap('发行人完整普通股范围未核对')
    if bundle.get('equivalent_share_rights_confirmed') is not True or not bundle.get('rights_basis'):
        raise FinancialGap('各股类同权依据未核对')
    refs=list(references(bundle.get('share_basis_evidence')))
    classes=bundle.get('classes', [])
    if not 1<=len(classes)<=8:raise FinancialGap('普通股分类缺失或超出范围')
    seen=set();total=Decimal(0)
    for row in classes:
        if not row.get('class_key') or row['class_key'] in seen or row.get('reviewed') is not True or row.get('unit')!='shares':
            raise FinancialGap('股类重复、未核对或单位错误')
        seen.add(row['class_key'])
        values=[number(row.get(k)) for k in ('outstanding_shares','treasury_shares','issued_shares')]
        if any(v<0 or v!=v.to_integral_value() for v in values) or values[2]!=values[0]+values[1]:
            raise FinancialGap('已发行股数必须等于在外股数加库存股数')
        # Preserve the source's explicit three-column closing balance. A value
        # elsewhere on the page is insufficient; do not subtract treasury twice.
        line=row.get('original_line','')
        tokens=re.findall(r'(?<![\d,])\d{1,3}(?:,\d{3})+(?![\d,])|(?<![\d,])\d+(?![\d,])',line)
        if len(tokens)<3 or list(map(number,tokens[-3:]))!=values or not row.get('column_basis'):
            raise FinancialGap('股数原行/列定位不匹配')
        refs.extend(references(row.get('evidence')))
        total+=values[0]
    if total<=0:raise FinancialGap('在外普通股合计必须为正')
    if through>as_of:refs.extend(references(bundle.get('coverage_evidence')))
    until=bundle.get('ordinary_shares_valid_until')
    if until:
        deadline=datetime.fromisoformat(until)
        if deadline.tzinfo is None or deadline.date()<=as_of:raise FinancialGap('股数已知变动时点不合法')
        refs.extend(references(bundle.get('share_change_evidence')))
    return {'scope':'parent_ordinary','shares_as_of':as_of.isoformat(),
        'ordinary_shares_verified_through':through.isoformat(),
        **({'ordinary_shares_valid_until':until} if until else {}),
        'ordinary_shares':format(total,'f'),'equivalent_share_rights':True,
        'classes':classes,'rights_basis':bundle['rights_basis'],
        'evidence':list({digest(r):r for r in refs}.values()),
        'lineage':{'method':'sum_explicit_outstanding_classes_v1','bundle_hash':digest(bundle)}}


def verify_originals(db, payload):
    """Every selected balance row must occur in its immutable source text."""
    for row in payload['classes']:
        if not any(row['original_line'] in json_text(db,ref) for ref in row['evidence']):
            raise FinancialGap('股数原行不在指定原文修订中')


def json_text(db, ref):
    import json
    from app.models.runtime import ItemRevision
    revision=db.get(ItemRevision,ref['source_revision_id'])
    return json.loads(revision.payload_json).get('readable_text','') if revision else ''
