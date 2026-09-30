#!/usr/bin/env python3
"""Offline design artifact checks, NOT runtime/software acceptance or a full JSON Schema validator."""
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
checks = []

def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Material syntax, provenance and local references.
json_paths = sorted(ROOT.glob("config/*.json")) + sorted(ROOT.glob("contracts/*.json")) + sorted(ROOT.glob("examples/*.json"))
for p in json_paths:
    json.loads(p.read_text())
    check(True, f"JSON syntax: {p.relative_to(ROOT)}")

for p in sorted(ROOT.rglob("*.md")):
    if p.name == "REVIEW-PACK.md" or ".git" in p.parts:
        continue
    for dest in re.findall(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", p.read_text()):
        if "://" in dest or dest.startswith("#"):
            continue
        target = unquote(dest.split("#")[0])
        check((p.parent / target).exists(), f"Local link: {p.relative_to(ROOT)} -> {target}")

for p in sorted(ROOT.glob("contracts/*.schema.json")):
    schema = json.loads(p.read_text())
    check(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"Schema dialect: {p.name}")
    def inspect(value):
        if isinstance(value, dict):
            if "$ref" in value:
                ref = value["$ref"]
                check(ref.startswith("#/"), f"Local-only schema ref: {p.name}")
                target = schema
                for segment in ref[2:].split("/"):
                    target = target[segment.replace("~1", "/").replace("~0", "~")]
                check(isinstance(target, dict), f"Resolvable schema ref: {p.name}:{ref}")
            for v in value.values():
                inspect(v)
        elif isinstance(value, list):
            for v in value:
                inspect(v)
    inspect(schema)

strategy = read_json("config/strategy-standard-v1.json")
scoring = read_json("config/scoring-standard-v1.json")
check(strategy["universe"]["markets"] == ["CN_A", "HK"], "Confirmed A-share and HK scope")
check(strategy["scoring_model_ref"] == scoring["model_key"], "Strategy scoring version reference")
check(sum(Decimal(v) for v in scoring["dimension_weights"].values()) == Decimal(1), "Dimension weights sum to 1")
check(set(strategy["quality_gates"]["required_dimensions"]) <= set(scoring["dimension_weights"]), "Required dimensions exist")
check(strategy["quality_gates"]["minimum_coverage"] == scoring["minimum_company_coverage"] == "0.80", "Coverage configuration consistency")
for dim, baseline in scoring["baselines"].items():
    if "metrics" in baseline:
        check(sum(Decimal(x["weight"]) for x in baseline["metrics"]) == 1, f"Baseline weights: {dim}")
        check(all(Decimal(x["zero_at"]) != Decimal(x["full_at"]) for x in baseline["metrics"]), f"Nonzero interpolation ranges: {dim}")

schema_fields = set(read_json("contracts/strategy.schema.json")["$defs"]["expression"]["oneOf"][1]["properties"]["field"]["enum"])
for mode in ["enter", "retain"]:
    clauses = strategy[mode]["all"]
    check(0 < len(clauses) <= 30, f"Bounded clause count: {mode}")
    check(len({x["field"] for x in clauses}) == len(clauses), f"No duplicate default rule fields: {mode}")
    for clause in clauses:
        check(clause["field"] in schema_fields and clause["op"] in {"gte", "lte"}, f"Whitelisted default rule: {mode}:{clause['field']}")
        Decimal(clause["value"])
enter = {x["field"]: x for x in strategy["enter"]["all"]}
retain = {x["field"]: x for x in strategy["retain"]["all"]}
check(set(enter) == set(retain), "Enter/retain field parity")
for field, e in enter.items():
    r = retain[field]
    check(e["op"] == r["op"], f"Enter/retain comparator parity: {field}")
    ev, rv = Decimal(e["value"]), Decimal(r["value"])
    check(ev >= rv if e["op"] == "gte" else ev <= rv, f"Retain no stricter than enter: {field}")
policy = strategy["state_policy"]
check(policy["enter_distinct_sessions"] == policy["exit_distinct_sessions"] == 2, "Default two distinct-session confirmation")
check(not policy["initial_baseline_notify"] and not policy["historical_notify"], "Baseline/history notification silence")
check(strategy["hard_risk_policy"]["confirmed_only"], "Hard risk requires confirmation")

proposal = read_json("examples/analysis-proposal.json")
check(not proposal["no_link"] and bool(proposal["links"]), "Synthetic linked proposal shape")
for link in proposal["links"]:
    check(0 <= Decimal(link["relevance"]) <= 1 and 0 <= Decimal(link["confidence"]) <= 1, "Proposal link numeric range")
    check(bool(link["evidence_ids"]) and "approved" not in link, "Evidence required; analysis cannot self-approve")
for impact in proposal["impact_proposals"]:
    check(impact["company_id"] in {x["company_id"] for x in proposal["links"]}, "Impact refers to proposed company link")
    check(impact["dimension"] in scoring["dimension_weights"] and -1 <= Decimal(impact["signed_impact"]) <= 1, "Impact dimension and range")
job = read_json("examples/job-event.json")
check(job["mode"] == "shadow" and set(job["payload"]) == {"input_manifest_id", "job_id"}, "Synthetic job is shadow/reference-only")
cases = read_json("examples/state-machine-cases.json")
check(cases["synthetic"], "State cases are synthetic")
check([x["notification"] for x in cases["cases"] if x["notification"]] == ["ENTER", "EXIT", "ENTER", "RISK"], "State scenario expected notification sequence (not engine execution)")
check(cases["cases"][1]["session"] == cases["cases"][2]["session"] and cases["cases"][2]["display"] == "ENTER_PENDING", "Same-session expected count held")
check(cases["cases"][4]["display"] == "UNKNOWN" and cases["cases"][4]["confirmed"] == "IN", "Unknown scenario preserves confirmed state")

prd = (ROOT / "docs/01-product-requirements.md").read_text()
acceptance = (ROOT / "docs/10-acceptance.md").read_text()
plan = (ROOT / "docs/09-delivery-plan.md").read_text()
for n in range(1, 15):
    rid = f"R-{n:02}"
    check(rid in prd and rid in acceptance, f"Requirement trace: {rid}")
for n in range(1, 25):
    check(f"T-{n:02}" in acceptance, f"Acceptance scenario present: T-{n:02}")
for n in range(1, 8):
    check(f"W-{n:02}" in plan and f"W-{n:02}" in acceptance, f"Work trace: W-{n:02}")

sources = sorted(p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts and p.name not in {"REVIEW-PACK.md", "validation-result.json"})
for p in sources:
    content = p.read_text(encoding="utf-8")
    check(not re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}", content), f"Targeted credential-pattern scan: {p.relative_to(ROOT)}")
report = {"design_version": "0.1", "design_date": "2026-09-30", "status": "passed", "scope": "Offline material syntax, references, bounded semantic/config and synthetic expected-result checks", "check_count": len(checks), "checks": checks, "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources}, "not_run": ["Full draft-2020-12 JSON Schema validation", "Runtime strategy/scoring/state-machine implementation tests", "Database/API/source integration", "Model/retrieval gold-set evaluation", "Real UI, accessibility, device and user acceptance", "Load/security/recovery exercises", "External notification"]}
(ROOT / "review/validation-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(checks)} material checks; {len(sources)} source artifact hashes. Runtime acceptance and full JSON Schema validation NOT RUN.")
