#!/usr/bin/env python3
"""Package committed review sources locally; no network, DB or business-data reads."""
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {"AGENTS.md", "PROJECT.md", "README.md", "CONTEXT.md", "Makefile", ".gitignore"}
PREFIXES = ("docs/", "design/", "contracts/", "config/", "examples/", "research/",
            "prototype/", "backend/", "frontend/", "tools/", "versions/v0.0.1/")
REVIEWS = {"CURRENT-HANDOFF.md", "CURRENT-REVIEW-PROMPT.md", "GPT-PRO-UX18-PROMPT.md", "CODING-READINESS.md",
           "V02-CHANGELOG.md", "V03-CHANGELOG.md", "V03-COUNTEREXAMPLES.md",
           "DESIGN-DETAIL-REVIEW.md", "USABILITY-REVIEW.md", "USABILITY-FIXES.md",
           "GPT-PRO-FINAL-DISPOSITION.md", "ROUND-2-REVIEW.md"}
SUFFIXES = {".md", ".json", ".py", ".tsx", ".ts", ".css", ".js", ".mjs", ".cjs",
            ".html", ".toml", ".lock", ".ini", ".mako"}
FORBIDDEN_PARTS = {".git", "raw-data", "local-data", "local-evidence", ".runtime",
                   "secrets", "node_modules", ".venv", "__pycache__"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def allowed(name):
    p = Path(name)
    if FORBIDDEN_PARTS.intersection(p.parts) or any(part.startswith(".env") for part in p.parts):
        return False
    if name == "backend/static/app.js":  # Generated minified copy; review TS source instead.
        return False
    if name in ROOT_FILES or name == "tools/vip":
        return True
    if name.startswith("review/"):
        return p.name in REVIEWS and len(p.parts) == 2
    return name.startswith(PREFIXES) and p.suffix in SUFFIXES


def main():
    if git("status", "--porcelain").strip():
        raise SystemExit("Refusing ambiguous review snapshot: commit or preserve pending changes first.")
    revision = git("rev-parse", "HEAD").decode().strip()
    names = sorted(n for n in git("ls-tree", "-r", "--name-only", "HEAD").decode().splitlines() if allowed(n))
    required = {"review/CURRENT-HANDOFF.md", "review/CURRENT-REVIEW-PROMPT.md",
                "frontend/src/app.tsx", "backend/app/services/research_pipeline.py"}
    if not required.issubset(names):
        raise SystemExit("Missing current review inputs in HEAD.")
    contents = {n: git("show", f"HEAD:{n}") for n in names}
    manifest = {"git_revision": revision, "branch_at_packaging": git("branch", "--show-current").decode().strip(),
                "status": "committed_clean_snapshot", "scope": "design, implementation and review evidence metadata",
                "tests_rerun_by_packaging": False, "real_raw_data_included": False,
                "screenshots_included": False,
                "files": [{"path": n, "bytes": len(contents[n]), "sha256": hashlib.sha256(contents[n]).hexdigest()} for n in names]}
    out = ROOT / "local-evidence/review-handoff"
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"value-investment-review-{revision[:12]}.zip"
    if archive.exists():
        raise SystemExit(f"Already packaged; preserving existing archive: {archive}")
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as z:
        z.writestr("value-investment-platform/REVIEW-MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for name, content in contents.items():
            z.writestr("value-investment-platform/" + name, content)
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise SystemExit("Archive CRC check failed.")
        actual = json.loads(z.read("value-investment-platform/REVIEW-MANIFEST.json"))
        assert len(z.namelist()) == len(names) + 1
        for entry in actual["files"]:
            assert allowed(entry["path"])
            assert hashlib.sha256(z.read("value-investment-platform/" + entry["path"])).hexdigest() == entry["sha256"]
    print(json.dumps({"archive": str(archive), "git_revision": revision, "files": len(names),
                      "bytes": archive.stat().st_size, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                      "crc_and_all_file_hashes_verified": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
