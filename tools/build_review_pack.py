#!/usr/bin/env python3
"""Build one local, self-contained GPT Pro review attachment; no network calls."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / "README.md", ROOT / "CONTEXT.md", ROOT / "AGENTS.md"]
for pattern in ["docs/*.md", "docs/adr/*.md", "config/*.json", "contracts/*.md", "contracts/*.json", "examples/*.json"]:
    paths.extend(sorted(ROOT.glob(pattern)))
paths.append(ROOT / "review/GPT-PRO-PROMPT.md")
if (ROOT / "review/validation-result.json").exists():
    paths.append(ROOT / "review/validation-result.json")
parts = ["# 价值投资策略管理系统 v0.1 · GPT Pro 整包评审材料\n\n日期：2026-09-30。设计为提案、系统尚未实现。只含本次新生成设计、合成例子及材料检查。\n\n请对照随附提示词完整审查；不能从材料检查通过推导运行时已通过。\n\n## 文件目录与 SHA-256\n\n| 文件 | SHA-256 |\n|---|---|\n"]
for p in paths:
    parts.append(f"| `{p.relative_to(ROOT)}` | `{hashlib.sha256(p.read_bytes()).hexdigest()}` |\n")
for p in paths:
    rel = p.relative_to(ROOT)
    parts.append(f"\n\n---\n\n# 文件：{rel}\n\n")
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        parts.append("```json\n" + text + "```\n")
    else:
        parts.append(text)
output = ROOT / "review/REVIEW-PACK.md"
output.write_text("".join(parts), encoding="utf-8")
print(f"Built {len(paths)} source sections; {output.stat().st_size} bytes; SHA256={hashlib.sha256(output.read_bytes()).hexdigest()}")
