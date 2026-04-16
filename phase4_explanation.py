"""
Phase 4: Explanation Generation
=================================
For every case (labeled and unlabeled), generates a plain English
legal explanation that ties together:
  - The IRAC structure from Phase 1
  - The predicted or actual outcome from Phase 3
  - The top arguments that drove the prediction, with their scores

The explanation answers two questions:
  1. What is the predicted/actual outcome?
  2. Why? Which arguments drove that prediction and what do they mean?

Output: sec_cases_explained.json
Each record adds:
{
  "explanation": {
    "outcome_summary":   str,   # one sentence: what happened and result
    "legal_reasoning":   str,   # IRAC-grounded explanation of why
    "key_arguments":     str,   # plain English explanation of top drivers
    "confidence_note":   str,   # honest note about prediction confidence
    "full_explanation":  str,   # combined narrative for display
  }
}

Usage
-----
  python phase4_explanation.py \
    --input   sec_cases_scored.json \
    --output  sec_cases_explained.json \
    --limit   100          # optional: test on first N cases
    --resume               # optional: skip already explained cases
    --labeled_only         # optional: only explain labeled cases
"""

import json
import argparse
import time
from pathlib import Path


def _describe_outcome(case: dict) -> tuple[str, str, str, str]:
    """
    Decide what outcome we are explaining and build short textual descriptors.
    Returns (outcome_source, outcome_result, judgment, outcome_types_text).
    """
    outcome_label = case.get("outcome_label", {})
    is_labeled = case.get("is_labeled", False)

    if is_labeled and outcome_label.get("defendant_result") != "unknown":
        outcome_source = "actual"
        outcome_result = outcome_label.get("defendant_result", "")
        judgment = outcome_label.get("judgment_type", "")
        outcome_types_text = ", ".join(outcome_label.get("outcome_types", []))
    else:
        outcome_source = "predicted"
        outcome_result = case.get("predicted_result", "uncertain")
        judgment = case.get("judgment_type", "")
        outcome_types = case.get("outcome_label", {}).get("outcome_types", [])
        outcome_types_text = ", ".join(outcome_types) if outcome_types else ""

    return outcome_source, outcome_result, judgment, outcome_types_text


def _format_confidence(confidence: float) -> str:
    if confidence > 0.7:
        return "high confidence"
    if confidence > 0.3:
        return "moderate confidence"
    return "low confidence - the case arguments are mixed"


def _summarize_arguments(top_arguments: list) -> tuple[str, str]:
    """
    Build short templates describing which arguments drove the outcome.
    Returns (short_phrase, detailed_sentences).
    """
    if not top_arguments:
        return "no specific argument features stood out", "No specific argument features stood out as especially strong in either direction."

    names = [a["argument_text"] for a in top_arguments]
    strong = [a for a in top_arguments if abs(a["argument_score"]) > 0.7]
    moderate = [a for a in top_arguments if 0.3 < abs(a["argument_score"]) <= 0.7]

    short = ", ".join(names[:3])

    parts = []
    if strong:
        strong_names = ", ".join(a["argument_text"] for a in strong[:3])
        parts.append(f"The strongest drivers were {strong_names}.")
    if moderate:
        moderate_names = ", ".join(a["argument_text"] for a in moderate[:3])
        parts.append(f"Additional supporting factors included {moderate_names}.")
    if not parts:
        parts.append("The arguments provided only weak directional signals.")

    return short, " ".join(parts)


def build_offline_explanation(case: dict) -> dict:
    """
    Construct an explanation purely from existing structured fields.
    No external API calls are used.
    """
    irac = case.get("irac", {})
    outcome_source, outcome_result, judgment, outcome_types_text = _describe_outcome(case)
    confidence = case.get("prediction_confidence", 0.0)
    anco_score = case.get("anco_hits_score", 0.0)
    confidence_desc = _format_confidence(confidence)

    short_args, detailed_args = _summarize_arguments(case.get("top_arguments", []))

    # Outcome summary: one or two short sentences
    if outcome_source == "actual":
        outcome_summary = (
            f"This case concerns {case.get('case_title', 'an SEC enforcement action')}. "
            f"The actual result was classified as {outcome_result.replace('_', ' ')}."
        )
    else:
        outcome_summary = (
            f"This case concerns {case.get('case_title', 'an SEC enforcement action')}. "
            f"Based on the argument pattern, the model predicts {outcome_result.replace('_', ' ')}."
        )

    # Legal reasoning: use IRAC fields if present
    issue = irac.get("issue", "") or "The precise legal issue could not be reliably extracted."
    rule = irac.get("rule", "") or "The governing legal rules were not clearly identified in the record."
    application = irac.get("application", "") or "The factual application to those rules is incomplete in the structured data."
    conclusion = irac.get("conclusion", "") or "The conclusion section did not clearly state why the court ruled as it did."

    legal_reasoning = (
        f"Issue: {issue} "
        f"Rule: {rule} "
        f"Application: {application} "
        f"Conclusion: {conclusion}"
    )

    if judgment or outcome_types_text:
        legal_reasoning += (
            f" The outcome was recorded as judgment type '{judgment or 'not specified'}'"
            f"{' with outcome types ' + outcome_types_text if outcome_types_text else ''}."
        )

    # Key arguments: use ANCO-HITS scores and direction
    directions = []
    for arg in case.get("top_arguments", []):
        score = arg["argument_score"]
        direction = "favored the SEC" if score > 0 else "favored the defendant"
        directions.append(
            f"'{arg['argument_text']}' (score {score:+.2f}) {direction}"
        )
    if directions:
        key_arguments = (
            "The model treated the following argument features as most informative: "
            + "; ".join(directions)
            + "."
        )
    else:
        key_arguments = "The model did not identify any single argument feature as strongly driving the outcome."

    if detailed_args:
        key_arguments += f" {detailed_args}"

    # Confidence note based on ANCO score and confidence
    confidence_note = (
        f"The ANCO-HITS score for this case was {anco_score:+.3f}, which corresponds to {confidence_desc} in the direction of the predicted result."
    )

    # Full explanation: single paragraph for non-lawyers
    full_explanation = (
        f"{outcome_summary} {legal_reasoning} "
        f"{key_arguments} {confidence_note}"
    )

    return {
        "outcome_summary": outcome_summary,
        "legal_reasoning": legal_reasoning,
        "key_arguments": key_arguments,
        "confidence_note": confidence_note,
        "full_explanation": full_explanation,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 4 (offline): Generate explanations without external APIs")
    parser.add_argument("--input",        required=True, help="Path to sec_cases_scored.json")
    parser.add_argument("--output",       required=True, help="Path to write sec_cases_explained.json")
    parser.add_argument("--limit",        type=int, default=None)
    parser.add_argument("--resume",       action="store_true")
    parser.add_argument("--labeled_only", action="store_true", help="Only explain labeled cases")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    with open(args.input) as f:
        cases = json.load(f)

    # Filter if labeled_only
    if args.labeled_only:
        cases = [c for c in cases if c.get("is_labeled")]
        print(f"  Filtered to {len(cases)} labeled cases")

    if args.limit:
        cases = cases[:args.limit]
        print(f"  Limited to {len(cases)} cases")

    # Load existing results if resuming
    already_done = set()
    results = []
    if args.resume and Path(args.output).exists():
        with open(args.output) as f:
            results = json.load(f)
        already_done = {r["case_id"] for r in results}
        print(f"  Resuming: {len(already_done)} already explained")

    to_process = [c for c in cases if c["case_id"] not in already_done]
    print(f"  {len(to_process)} cases to explain\n")

    success = 0
    failed = 0

    for i, case in enumerate(to_process):
        case_id = case["case_id"]
        print(f"[{i+1}/{len(to_process)}] {case_id[:60]}...", end=" ", flush=True)

        try:
            explanation = build_offline_explanation(case)
            status = "success"
            error = ""
            success += 1
            print("OK")
        except Exception as e:
            explanation = {}
            status = "failed"
            error = str(e)
            failed += 1
            print(f"FAILED: {error[:80]}")

        results.append({
            **case,
            "explanation":        explanation,
            "explanation_status": status,
            "explanation_error":  error,
        })

        # Checkpoint every 50 records
        if (i + 1) % 50 == 0:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"  -- checkpoint saved ({len(results)} records) --")

        time.sleep(0.3)

    # Final save
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDone.")
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")
    print(f"  Output:  {args.output}")

    # Print a sample explanation
    sample = next((r for r in results if r.get("explanation_status") == "success"), None)
    if sample:
        print(f"\nSample explanation for: {sample['case_id']}")
        print("-" * 60)
        exp = sample.get("explanation", {})
        print("OUTCOME SUMMARY:")
        print(exp.get("outcome_summary", ""))
        print("\nLEGAL REASONING:")
        print(exp.get("legal_reasoning", ""))
        print("\nKEY ARGUMENTS:")
        print(exp.get("key_arguments", ""))
        print("\nCONFIDENCE:")
        print(exp.get("confidence_note", ""))
        print("\nFULL EXPLANATION:")
        print(exp.get("full_explanation", ""))


if __name__ == "__main__":
    main()
