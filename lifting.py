"""
Phase 1: Symbolic Lifting
=========================
Reads the SEC litigation releases JSON and produces a structured
IRAC object for every case using spaCy NLP and rule-based extraction.
No external API keys required.

Each output record has this shape:
{
  "case_id":      str,   # citation field used as unique ID
  "case_title":   str,
  "court":        str,
  "date":         str,
  "case_status":  str,
  "is_labeled":   bool,  # True if we have a usable outcome label

  "entities": {
    "defendants":     [str],
    "charges":        [str],   # from charges_and_sections
    "legal_topics":   [str],
    "domain":         str,
    "judges":         [str],
  },

  "irac": {
    "issue":       str,   # rule-based extraction
    "rule":        str,   # rule-based extraction
    "application": str,   # rule-based extraction
    "conclusion":  str,   # rule-based extraction
    "uncertainty": str,   # flags missing/incomplete fields
  },

  "outcome_label": {
    "judgment_type":    str,
    "outcome_types":    [str],
    "defendant_result": str,   # "defendant_win", "plaintiff_win", or "unknown"
  },

  "source_fields": {
    "scheme_method":          str,
    "admission_status":       str,
    "total_fine_amount":      str,
    "total_victim_losses":    str,
    "scheme_duration":        str,
    "defendant_sentence":     str,
    "final_judgment_details": str,
  },

  "lift_status": str,   # "success", "skipped_empty"
  "lift_error":  str,   # populated if lift_status != "success"
}

Usage
-----
  python lifting.py \\
    --input  sec_litigation_releases_20260403_234416.json \\
    --output sec_cases_lifted.json \\
    --limit  100          # optional: process only first N cases for testing
    --resume              # optional: skip cases already in output file
"""

import json
import re
import argparse
from pathlib import Path

import spacy

# ── CONFIG ────────────────────────────────────────────────────────────────────

# Judgment types that clearly indicate the SEC (plaintiff) won
PLAINTIFF_WIN_PATTERNS = [
    "consent judgment",
    "default judgment",
    "permanent injunction",
    "final judgment",
    "civil penalty",
    "disgorgement",
    "permanent bar",
    "asset freeze",
    "guilty plea",
    "convicted",
]

# Judgment types that indicate the defendant won or case was dropped
DEFENDANT_WIN_PATTERNS = [
    "dismissed",
    "acquitted",
    "not guilty",
    "judgment for defendant",
    "charges dropped",
]

# We only have a usable outcome label if the case is closed
LABELED_STATUSES = {
    "settled/consented",
    "final judgment entered",
    "dismissed",
    "closed",
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_nlp():
    """Load spaCy model. Falls back to small model if large is not installed."""
    try:
        return spacy.load("en_core_web_lg")
    except OSError:
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "No spaCy model found. Run: python -m spacy download en_core_web_lg"
            )


def extract_entities(record: dict, nlp) -> dict:
    """
    Pull named entities and structured fields from a case record.
    This runs locally with spaCy - no API call needed.
    """
    # Defendants: prefer respondent field, fall back to case title parsing
    defendants = []
    if record.get("respondent"):
        defendants.append(record["respondent"].strip())
    if record.get("co_defendants"):
        co = record["co_defendants"]
        if isinstance(co, list):
            defendants.extend([d.strip() for d in co if d.strip()])
        elif isinstance(co, str) and co.strip():
            defendants.append(co.strip())

    # If we still have nothing, run spaCy on the first sentence of the summary
    # to pick up PERSON entities
    if not defendants and record.get("summary"):
        first_sentence = record["summary"][:500]
        doc = nlp(first_sentence)
        defendants = [
            ent.text.strip()
            for ent in doc.ents
            if ent.label_ == "PERSON"
        ][:3]  # cap at 3 to avoid noise

    # Charges: already structured in the JSON
    charges = record.get("charges_and_sections", [])
    if isinstance(charges, str):
        charges = [c.strip() for c in charges.split(",") if c.strip()]

    # Legal topics
    legal_topics = record.get("legal_topic", [])
    if isinstance(legal_topics, str):
        legal_topics = [t.strip() for t in legal_topics.split(",") if t.strip()]

    return {
        "defendants":   defendants,
        "charges":      charges,
        "legal_topics": legal_topics,
        "domain":       record.get("company_domain", "").strip(),
        "judges":       record.get("judges", []) if isinstance(record.get("judges"), list) else [],
    }


def classify_outcome(record: dict) -> dict:
    """
    Determine defendant_result from judgment_type, outcome, and case_status.
    Returns "defendant_win", "plaintiff_win", or "unknown".
    """
    judgment = str(record.get("judgment_type", "")).lower()
    outcome_list = record.get("outcome", [])
    if isinstance(outcome_list, str):
        outcome_list = [outcome_list]
    outcomes_text = " ".join(outcome_list).lower()
    status = str(record.get("case_status", "")).lower()

    # Check for defendant win signals
    for pat in DEFENDANT_WIN_PATTERNS:
        if pat in judgment or pat in outcomes_text or pat in status:
            return {
                "judgment_type":    record.get("judgment_type", ""),
                "outcome_types":    outcome_list,
                "defendant_result": "defendant_win",
            }

    # Check for plaintiff win signals
    for pat in PLAINTIFF_WIN_PATTERNS:
        if pat in judgment or pat in outcomes_text:
            return {
                "judgment_type":    record.get("judgment_type", ""),
                "outcome_types":    outcome_list,
                "defendant_result": "plaintiff_win",
            }

    return {
        "judgment_type":    record.get("judgment_type", ""),
        "outcome_types":    outcome_list,
        "defendant_result": "unknown",
    }


def is_labeled(record: dict) -> bool:
    """
    A case is 'labeled' (usable for training) if:
    1. The case is closed / settled, AND
    2. We can determine a defendant_result that is not 'unknown'
    """
    status = str(record.get("case_status", "")).lower()
    closed = any(s in status for s in LABELED_STATUSES)
    if not closed:
        return False
    outcome = classify_outcome(record)
    return outcome["defendant_result"] != "unknown"


def extract_irac(record: dict, entities: dict, nlp) -> dict:
    """
    Build IRAC fields from the structured case data using rule-based
    extraction and spaCy NLP. No API key needed.
    """
    NOT_AVAILABLE = "Not available in case record."

    defendants_text = ", ".join(entities["defendants"]) if entities["defendants"] else "the defendant(s)"
    charges_text = ", ".join(entities["charges"]) if entities["charges"] else ""

    # ── ISSUE ──
    if charges_text:
        issue = f"Whether {defendants_text} violated {charges_text}."
    elif entities["legal_topics"]:
        issue = f"Whether {defendants_text} engaged in conduct constituting {', '.join(entities['legal_topics'])}."
    else:
        issue = NOT_AVAILABLE

    # ── RULE ──
    if charges_text:
        rule = f"Governing statutes and provisions: {charges_text}."
    else:
        rule = NOT_AVAILABLE

    # ── APPLICATION ──
    scheme = str(record.get("scheme_method", "")).strip()
    summary = str(record.get("summary", "")).strip()
    app_parts = []

    if scheme:
        # Use spaCy to extract the first 2 sentences for conciseness
        doc = nlp(scheme[:1500])
        sents = [s.text.strip() for s in doc.sents]
        app_parts.append(" ".join(sents[:2]))

    if summary and not app_parts:
        doc = nlp(summary[:1500])
        sents = [s.text.strip() for s in doc.sents]
        app_parts.append(" ".join(sents[:2]))

    fine = str(record.get("total_fine_amount", "")).strip()
    losses = str(record.get("total_victim_losses", "")).strip()
    if fine:
        app_parts.append(f"Total fines: {fine}.")
    if losses:
        app_parts.append(f"Victim losses: {losses}.")

    application = " ".join(app_parts) if app_parts else NOT_AVAILABLE

    # ── CONCLUSION ──
    judgment = str(record.get("judgment_type", "")).strip()
    outcome_list = record.get("outcome", [])
    if isinstance(outcome_list, str):
        outcome_list = [outcome_list]
    final_j = str(record.get("final_judgment_details", "")).strip()
    sentence = str(record.get("defendant_sentence", "")).strip()
    admission = str(record.get("admission_status", "")).strip()

    conc_parts = []
    if judgment:
        conc_parts.append(f"Judgment type: {judgment}.")
    if outcome_list:
        conc_parts.append(f"Outcome: {', '.join(str(o) for o in outcome_list)}.")
    if admission:
        conc_parts.append(f"Admission status: {admission}.")
    if sentence:
        conc_parts.append(f"Sentence: {sentence}.")
    if final_j:
        conc_parts.append(f"Final judgment: {final_j}.")

    conclusion = " ".join(conc_parts) if conc_parts else NOT_AVAILABLE

    # ── UNCERTAINTY ──
    gaps = []
    if not charges_text:
        gaps.append("charges/statutes not specified")
    if not scheme and not summary:
        gaps.append("no scheme description or summary available")
    if not judgment and not outcome_list:
        gaps.append("judgment type and outcome not recorded")
    if not fine and not losses:
        gaps.append("financial impact figures missing")

    uncertainty = "; ".join(gaps).capitalize() + "." if gaps else "None identified."

    return {
        "issue":       issue,
        "rule":        rule,
        "application": application,
        "conclusion":  conclusion,
        "uncertainty": uncertainty,
    }


def lift_record(record: dict, nlp) -> dict:
    """
    Run the full lifting pipeline for one case record.
    Uses spaCy + rule-based extraction (no API calls).
    """
    case_id = record.get("citation", record.get("case_title", "unknown"))

    # Skip cases with no usable text
    summary = str(record.get("summary", "")).strip()
    scheme = str(record.get("scheme_method", "")).strip()
    if not summary and not scheme:
        return {
            "case_id":      case_id,
            "case_title":   record.get("case_title", ""),
            "court":        record.get("court", ""),
            "date":         record.get("date", ""),
            "case_status":  record.get("case_status", ""),
            "is_labeled":   is_labeled(record),
            "entities":     extract_entities(record, nlp),
            "irac":         {},
            "outcome_label": classify_outcome(record),
            "source_fields": _source_fields(record),
            "lift_status":  "skipped_empty",
            "lift_error":   "Both summary and scheme_method are empty",
        }

    entities = extract_entities(record, nlp)
    irac = extract_irac(record, entities, nlp)

    return {
        "case_id":      case_id,
        "case_title":   record.get("case_title", ""),
        "court":        record.get("court", ""),
        "date":         record.get("date", ""),
        "case_status":  record.get("case_status", ""),
        "is_labeled":   is_labeled(record),
        "entities":     entities,
        "irac":         irac,
        "outcome_label": classify_outcome(record),
        "source_fields": _source_fields(record),
        "lift_status":  "success",
        "lift_error":   "",
    }


def _source_fields(record: dict) -> dict:
    """Pull the raw source fields we want to keep alongside the IRAC output."""
    return {
        "scheme_method":          str(record.get("scheme_method", "")),
        "admission_status":       str(record.get("admission_status", "")),
        "total_fine_amount":      str(record.get("total_fine_amount", "")),
        "total_victim_losses":    str(record.get("total_victim_losses", "")),
        "scheme_duration":        str(record.get("scheme_duration", "")),
        "defendant_sentence":     str(record.get("defendant_sentence", "")),
        "final_judgment_details": str(record.get("final_judgment_details", "")),
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 1: Lift SEC cases to IRAC structure")
    parser.add_argument("--input",  required=True, help="Path to raw JSON file")
    parser.add_argument("--output", required=True, help="Path to write lifted JSON file")
    parser.add_argument("--limit",  type=int, default=None, help="Only process first N cases (for testing)")
    parser.add_argument("--resume", action="store_true", help="Skip case IDs already present in output file")
    args = parser.parse_args()

    # Load input
    print(f"Loading {args.input}...")
    with open(args.input) as f:
        records = json.load(f)
    if args.limit:
        records = records[:args.limit]
    print(f"  {len(records)} cases to process")

    # Load existing output if resuming
    already_done = set()
    results = []
    if args.resume and Path(args.output).exists():
        with open(args.output) as f:
            results = json.load(f)
        already_done = {r["case_id"] for r in results}
        print(f"  Resuming: {len(already_done)} cases already lifted, skipping them")

    # Load spaCy
    print("Loading spaCy model...")
    nlp = load_nlp()

    # Process
    to_process = [
        r for r in records
        if r.get("citation", r.get("case_title", "")) not in already_done
    ]
    print(f"  {len(to_process)} cases to lift now\n")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, record in enumerate(to_process):
        case_id = record.get("citation", record.get("case_title", f"record_{i}"))

        print(f"[{i+1}/{len(to_process)}] {case_id[:60]}...", end=" ", flush=True)

        lifted = lift_record(record, nlp)
        results.append(lifted)

        if lifted["lift_status"] == "success":
            success_count += 1
            print("OK")
        elif lifted["lift_status"] == "skipped_empty":
            skip_count += 1
            print("SKIPPED (no text)")
        else:
            fail_count += 1
            print(f"FAILED: {lifted['lift_error'][:80]}")

        # Save after every 50 records so we don't lose progress
        if (i + 1) % 50 == 0:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"  -- checkpoint saved ({len(results)} total records) --")

    # Final save
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDone.")
    print(f"  Success:  {success_count}")
    print(f"  Skipped:  {skip_count}")
    print(f"  Failed:   {fail_count}")
    print(f"  Total:    {len(results)}")
    print(f"  Output:   {args.output}")

    # Quick stats on label coverage
    labeled = [r for r in results if r.get("is_labeled")]
    plaintiff_wins = [r for r in labeled if r["outcome_label"]["defendant_result"] == "plaintiff_win"]
    defendant_wins = [r for r in labeled if r["outcome_label"]["defendant_result"] == "defendant_win"]
    print(f"\nLabel coverage:")
    print(f"  Labeled cases:   {len(labeled)}")
    print(f"  Plaintiff wins:  {len(plaintiff_wins)}")
    print(f"  Defendant wins:  {len(defendant_wins)}")


if __name__ == "__main__":
    main()