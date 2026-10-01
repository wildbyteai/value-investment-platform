#!/usr/bin/env python3
"""Render the physical-design dictionary from its local catalog. No database access."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'design/database-catalog.json').read_text())
tables={t['name']:t for t in catalog['tables']}
for t in tables.values():
    names=[c['name'] for c in t['columns']]
    assert len(names)==len(set(names)),t['name']
    for c in t['columns']:
        if 'references' in c:
            target,field=c['references'].split('.')
            assert target in tables and field in [x['name'] for x in tables[target]['columns']],c
    for key in t['unique_keys']:
        assert all(c in names for c in key),(t['name'],key)
header=(ROOT/'design/database-dictionary-intro.md').read_text()
parts=[header,'\n## 字段字典（由目录生成）\n\n']
for t in tables.values():
    parts.append(f"### {t['name']}\n\n责任：{t['owner']}；生命周期：`{t['lifecycle']}`；范围：`{t['scope']}`。\n\n")
    parts.append('| 字段 | PostgreSQL类型 | 可空 | 含义/引用 |\n|---|---|---|---|\n')
    for c in t['columns']:
        desc=c['meaning'].replace('|','/')
        if c.get('references'):desc+=f"；→ `{c['references']}`"
        parts.append(f"| `{c['name']}` | `{c['type']}` | {'是' if c['nullable'] else '否'} | {desc} |\n")
    parts.append('\n唯一键：'+ '；'.join('`('+','.join(k)+')`' for k in t['unique_keys'])+'。\n')
    if t['indexes']:parts.append('\n查询索引：'+'；'.join('`'+k+'`' for k in t['indexes'])+'。\n')
    if t['rules']:parts.append('\n'+ '\n'.join('- '+r for r in t['rules'])+'\n')
    parts.append('\n')
parts.append('## 逻辑对象与物理表示映射\n\n| 逻辑对象/视图 | 存储根 | 展开条件 | 说明 |\n|---|---|---|---|\n')
for v in catalog['logical_views']:parts.append(f"| `{v['name']}` | `{v['root']}` | `{v['filter']}` | {v['meaning']} |\n")
parts.append('\n这些视图尚未创建。统一修订存储只减少重复值和多态外键，公开Schema仍按现有类型分支；没有把risk/rubric能力收窄。\n')
(ROOT/'docs/15-database-dictionary.md').write_text(''.join(parts))
print(f"Rendered {len(tables)} tables, {sum(len(t['columns']) for t in tables.values())} columns; references and unique-key fields checked. No SQL executed.")
