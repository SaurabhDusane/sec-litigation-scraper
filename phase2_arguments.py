"""
Phase 2: Argument Feature Extraction
=====================================
Reads the lifted JSON from Phase 1 and extracts structured argument
features for every case. These become the nodes and edges in Phase 3.

For each case we extract:
  - Which charges were filed (from entities.charges)
  - What scheme type was used (parsed from irac.application + source_fields.scheme_method)
  - What the admission status was
  - What outcome types appeared (from outcome_label.outcome_types)

Output: sec_cases_arguments.json
Each record looks like:
{
  "case_id":          str,
  "is_labeled":       bool,
  "defendant_result": str,   # "plaintiff_win", "defendant_win", "unknown"
  "judgment_type":    str,
  "arguments": [
    {
      "argument_id":   str,   # stable ID like "charge::Rule 10b-5"
      "argument_type": str,   # "charge", "scheme_type", "admission", "outcome_type"
      "argument_text": str,   # human readable label
    },
    ...
  ]
}

Usage
-----
  python phase2_arguments.py \
    --input  sec_cases_lifted.json \
    --output sec_cases_arguments.json
"""

import json
import re
import argparse
from collections import defaultdict


# ── SCHEME TYPE KEYWORDS ──────────────────────────────────────────────────────
# We map free text scheme descriptions to a fixed set of scheme type labels.
# Order matters: more specific patterns go first.

SCHEME_TYPE_PATTERNS = [
    ("ponzi_scheme",             ["ponzi", "pyramid scheme", "ponzi-like"]),
    ("insider_trading",          ["insider trading", "material nonpublic", "misappropriated information"]),
    ("pump_and_dump",            ["pump and dump", "pump-and-dump", "artificially inflat", "manipulate the price"]),
    ("accounting_fraud",         ["false financial statement", "fictitious sale", "inflate.*income", "earnings manipulation", "cook the books"]),
    ("misrepresentation",        ["material misrepresentation", "false statement", "false representation", "misleading statement"]),
    ("unregistered_offering",    ["unregistered", "not registered", "failed to register"]),
    ("misappropriation",         ["misappropriat", "embezzl", "convert.*client fund", "stole"]),
    ("front_running",            ["front.?running", "front run"]),
    ("affinity_fraud",           ["affinity fraud", "targeted.*religious", "targeted.*community", "targeted.*church"]),
    ("prime_bank_fraud",         ["prime bank", "prime bank instrument"]),
    ("investment_adviser_fraud", ["investment adviser", "advisory client", "fiduciary"]),
    ("market_manipulation",      ["market manipulation", "manipulate.*market", "wash trade", "matched order"]),
    ("false_filings",            ["false.*filing", "false.*report", "false.*disclosure", "material omission"]),
    ("boiler_room",              ["boiler room", "high pressure sales"]),
    ("other_fraud",              ["fraud", "deceptive", "scheme to defraud"]),  # catch-all
]


def classify_scheme(text: str) -> list[str]:
    """
    Return a list of scheme type labels that match the text.
    Can return multiple if the scheme involves several methods.
    """
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for label, patterns in SCHEME_TYPE_PATTERNS:
        for pat in patterns:
            if re.search(pat, text_lower):
                matched.append(label)
                break  # one match per label is enough
    return matched if matched else ["unclassified"]


def normalize_charge(charge: str) -> str:
    """
    Normalize charge strings to consistent IDs.
    e.g. "Exchange Act § 10(b)" -> "exchange_act_10b"
    """
    c = charge.lower()
    c = re.sub(r"§", "s", c)
    c = re.sub(r"[^a-z0-9]+", "_", c)
    c = c.strip("_")
    return c


def extract_arguments(case: dict) -> list[dict]:
    """
    Extract all argument features from a single lifted case.
    Returns a list of argument dicts.
    """
    arguments = []

    # 1. CHARGES - one argument per charge
    for charge in case.get("entities", {}).get("charges", []):
        charge = charge.strip()
        if not charge:
            continue
        arguments.append({
            "argument_id":   f"charge::{normalize_charge(charge)}",
            "argument_type": "charge",
            "argument_text": charge,
        })

    # 2. SCHEME TYPES - parsed from application text and scheme_method
    scheme_text = " ".join([
        case.get("irac", {}).get("application", ""),
        case.get("source_fields", {}).get("scheme_method", ""),
    ])
    for scheme_label in classify_scheme(scheme_text):
        arguments.append({
            "argument_id":   f"scheme::{scheme_label}",
            "argument_type": "scheme_type",
            "argument_text": scheme_label.replace("_", " "),
        })

    # 3. ADMISSION STATUS - structured signal
    admission = case.get("source_fields", {}).get("admission_status", "").strip().lower()
    if admission:
        admission_id = re.sub(r"[^a-z0-9]+", "_", admission).strip("_")
        arguments.append({
            "argument_id":   f"admission::{admission_id}",
            "argument_type": "admission",
            "argument_text": case.get("source_fields", {}).get("admission_status", "").strip(),
        })

    # 4. LEGAL TOPICS - from entities
    for topic in case.get("entities", {}).get("legal_topics", []):
        topic = topic.strip()
        if not topic:
            continue
        topic_id = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
        arguments.append({
            "argument_id":   f"topic::{topic_id}",
            "argument_type": "legal_topic",
            "argument_text": topic,
        })

    # 5. OUTCOME TYPES (only for labeled cases - used to build ANCO-HITS edges)
    for otype in case.get("outcome_label", {}).get("outcome_types", []):
        otype = otype.strip()
        if not otype:
            continue
        otype_id = re.sub(r"[^a-z0-9]+", "_", otype.lower()).strip("_")
        arguments.append({
            "argument_id":   f"outcome_type::{otype_id}",
            "argument_type": "outcome_type",
            "argument_text": otype,
        })

    # Deduplicate by argument_id while preserving order
    seen = set()
    deduped = []
    for arg in arguments:
        if arg["argument_id"] not in seen:
            seen.add(arg["argument_id"])
            deduped.append(arg)

    return deduped


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Extract argument features")
    parser.add_argument("--input",  required=True, help="Path to sec_cases_lifted.json")
    parser.add_argument("--output", required=True, help="Path to write sec_cases_arguments.json")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    with open(args.input) as f:
        cases = json.load(f)
    print(f"  {len(cases)} cases loaded")

    results = []
    argument_counts = defaultdict(int)
    scheme_type_counts = defaultdict(int)

    for case in cases:
        arguments = extract_arguments(case)

        for arg in arguments:
            argument_counts[arg["argument_type"]] += 1
            if arg["argument_type"] == "scheme_type":
                scheme_type_counts[arg["argument_text"]] += 1

        results.append({
            "case_id":          case["case_id"],
            "case_title":       case.get("case_title", ""),
            "is_labeled":       case.get("is_labeled", False),
            "defendant_result": case.get("outcome_label", {}).get("defendant_result", "unknown"),
            "judgment_type":    case.get("outcome_label", {}).get("judgment_type", ""),
            "arguments":        arguments,
        })

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. {len(results)} cases written to {args.output}")
    print("\nArgument type counts:")
    for atype, count in sorted(argument_counts.items()):
        print(f"  {atype}: {count}")
    print("\nTop scheme types:")
    for scheme, count in sorted(scheme_type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {scheme}: {count}")


if __name__ == "__main__":
    main()
