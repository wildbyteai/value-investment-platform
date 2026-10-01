#!/usr/bin/env python3
"""Build local review pack and copy/paste messages; no network calls."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / "README.md", ROOT / "PROJECT.md", ROOT / "CONTEXT.md", ROOT / "AGENTS.md"]
for pattern in ["docs/*.md", "docs/adr/*.md", "research/*.md", "config/*.json", "contracts/*.md", "contracts/*.json", "examples/*.json", "tools/*.py", "tools/*.cjs", "design/*.json", "design/*.md", "prototype/*.html", "prototype/*.css", "prototype/*.js", "prototype/*.md"]:
    paths.extend(sorted(ROOT.glob(pattern)))
paths.extend([ROOT / "review/GPT-PRO-PROMPT.md", ROOT / "review/V02-CHANGELOG.md", ROOT / "review/V03-CHANGELOG.md", ROOT / "review/V03-COUNTEREXAMPLES.md", ROOT / "review/DESIGN-DETAIL-REVIEW.md", ROOT / "review/USABILITY-REVIEW.md", ROOT / "review/USABILITY-FIXES.md", ROOT / "review/GPT-PRO-FINAL-DISPOSITION.md"])
paths.extend(sorted(ROOT.glob("review/ROUND-2-*")))
if (ROOT / "review/validation-result.json").exists():
    paths.append(ROOT / "review/validation-result.json")
parts = ["# 价值投资策略管理系统 v0.3 · GPT Pro 整包评审材料\n\n日期：2026-10-01。产品范围已确认，工程设计尚未实现。只含本次新生成设计、合成例子及材料检查。\n\n请对照随附提示词完整审查；不能从材料检查通过推导运行时已通过。\n\n## 文件目录与 SHA-256\n\n| 文件 | SHA-256 |\n|---|---|\n"]
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

# Plain-text alternatives: no attachment and no repository access are required.
source_paths = [p for p in paths if str(p.relative_to(ROOT)) not in {"review/GPT-PRO-PROMPT.md", "review/validation-result.json"}]
sections = []
for p in source_paths:
    sections.append(f"\n\n===== SOURCE: {p.relative_to(ROOT)} =====\n\n" + p.read_text(encoding="utf-8"))
instruction = (ROOT / "review/GPT-PRO-PROMPT.md").read_text(encoding="utf-8").split("## 完整提示词\n", 1)[1].strip()
all_text = instruction + "\n\n[REVIEW_MATERIALS_BEGIN]\n" + "".join(sections) + "\n[REVIEW_MATERIALS_END]\n请按提示词开始业务闭环与UI终审，输出评审及最小修改提案。\n"
(ROOT / "review/PASTE-ALL.txt").write_text(all_text, encoding="utf-8")
# Focused final review keeps the business/UI path readable. Full engineering pack remains optional.
final_names = [
    "PROJECT.md", "README.md", "AGENTS.md", "CONTEXT.md",
    "review/USABILITY-REVIEW.md", "review/USABILITY-FIXES.md", "review/GPT-PRO-FINAL-DISPOSITION.md",
    "docs/01-product-requirements.md", "docs/06-ux-and-design-system.md",
    "docs/11-templates-automation-and-roles.md", "docs/12-time-numerics-and-corrections.md",
    "docs/13-first-slice.md", "docs/14-domain-and-business-flows.md", "docs/16-prototype-and-design-trace.md",
    "prototype/README.md", "prototype/index.html", "prototype/app.js", "prototype/style.css",
    "config/scoring-standard-v1.json", "config/strategy-standard-v1.json", "config/rubrics-standard-v1.json",
    "review/design-detail/prototype-checks.json",
]
final_sections = []
for name in final_names:
    p = ROOT / name
    final_sections.append(f"\n\n===== SOURCE: {name} | SHA256: {hashlib.sha256(p.read_bytes()).hexdigest()} =====\n\n" + p.read_text(encoding="utf-8"))
final_text = instruction + "\n\n[FINAL_REVIEW_MATERIALS_BEGIN]\n本正文包含终审核心材料与原型源码，不包含截图像素，不能据此声称已看过视觉效果。需要具体工程合同可从私有仓库或REVIEW-PACK另查。材料按文件SHA绑定当前工作树，运行报告中的Git HEAD是运行时基线。\n" + "".join(final_sections) + "\n[FINAL_REVIEW_MATERIALS_END]\n请开始业务闭环与UI终审，按提示词输出，不重写全套设计。\n"
(ROOT / "review/FINAL-REVIEW-PASTE.txt").write_text(final_text, encoding="utf-8")
print(f"Built focused final review: {len(final_names)} files; {len(final_text):,} characters.")
groups, group = [], ""
for section in sections:
    if group and len(group) + len(section) > 14000:
        groups.append(group)
        group = ""
    group += section
if group:
    groups.append(group)
links = []
for index, group in enumerate(groups, 1):
    start = instruction + "\n\n[REVIEW_MATERIALS_BEGIN]\n" if index == 1 else ""
    end = "\n[REVIEW_MATERIALS_END]\n全部材料已发完，请按提示词开始业务闭环与UI终审。\n" if index == len(groups) else "\n本段结束，材料尚未发完，请只确认已收到，不开始评审。\n"
    name = f"PASTE-PART-{index:02}.txt"
    body = start + f"\n[PART {index}/{len(groups)}]\n" + group + f"\n[END PART {index}/{len(groups)}]\n" + end
    (ROOT / "review" / name).write_text(body, encoding="utf-8")
    links.append(f"{index}. [{name}](./{name})：{len(body):,} 字符；直接复制全文作为一条消息。")
help_text = """# 不附文件的 GPT Pro 评审方式

## 优先：读取 GitHub

复制 [完整提示词](./GPT-PRO-PROMPT.md)中“完整提示词”下的全部内容，直接发给 GPT Pro。提示词已经指定仓库与材料路径，不要求上传附件。该方式要求当前 GPT Pro 会话有权限读取这个私有仓库；链接本身不赋予权限。

## 备用：正文粘贴

没有 GitHub 读取能力时，优先打开 [FINAL-REVIEW-PASTE.txt](./FINAL-REVIEW-PASTE.txt)，复制全部正文发给 GPT Pro，已含提示词与本轮业务/UI核心材料、旧独立评审和逐项处置。无截图像素时应明确视觉检查未执行；纯文本可评审业务、文案和导航。GPT Pro终审已取得，三项处置见 [终审记录](./GPT-PRO-FINAL-DISPOSITION.md)，本入口保留为按需复核材料，不要求再次评审。

完整工程上下文按需查 [REVIEW-PACK.md](./REVIEW-PACK.md) 或 [PASTE-ALL.txt](./PASTE-ALL.txt)，无需把全部工程材料列为本轮终审前置。全文已有提示词，无需另发提示词或附件。

若单条消息长度受界面限制，按下列顺序复制各段到同一个对话。第1段已包含完整提示词；中间段仅接收，最后一段自动开始评审。每个原文件完整保留，不在文件中间截断。没有假定所有界面都支持一次粘贴整包。

""" + "\n".join(links) + "\n\n这些是当前v0.3的传递方式。纯文本按文件完整覆盖README、领域词汇、实现规则、全部设计/ADR/两轮研究/配置/Schema/合成例子与变更账本；不包含机器检查报告的冗长日志，该日志仍在仓库可查。\n"
(ROOT / "review/PASTE-INSTRUCTIONS.md").write_text(help_text, encoding="utf-8")
print(f"Built full copy/paste text: {len(all_text):,} characters; {len(groups)} file-boundary parts.")
