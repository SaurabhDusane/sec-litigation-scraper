"""
Phase 3: ANCO-HITS Scoring and Outcome Prediction
===================================================
Builds a signed bipartite graph between cases and arguments,
runs ANCO-HITS to score every argument on a -1 to +1 scale,
then predicts outcomes for unlabeled cases.

How the scale works:
  +1.0  = argument strongly predicts plaintiff wins (SEC wins)
  -1.0  = argument strongly predicts defendant wins
   0.0  = argument is neutral / goes either way

Why ANCO-HITS and not a standard classifier:
  Every prediction traces back to specific argument scores.
  You can say "this case scores +0.72 because it involves
  Rule 10b-5 (+0.85), misrepresentation (+0.79), and the
  defendant consented (+0.91)." That is your explainability.

Signed edge assignment:
  labeled case + plaintiff_win  ->  all arguments get edge +1
  labeled case + defendant_win  ->  all arguments get edge -1
  unlabeled case                ->  no edges during training,
                                    score predicted after

Output: sec_cases_scored.json
Each record adds:
{
  "anco_hits_score":     float,   # case score on [-1, +1]
  "predicted_result":    str,     # "plaintiff_win" or "defendant_win"
  "prediction_confidence": float, # how far from 0 the score is (0-1)
  "top_arguments": [              # top 5 arguments driving the score
    {
      "argument_id":    str,
      "argument_text":  str,
      "argument_score": float,
    }
  ]
}

Usage
-----
  python phase3_anco_hits.py \
    --input   sec_cases_arguments.json \
    --output  sec_cases_scored.json \
    --iterations 50
"""

import json
import argparse
import random
from collections import defaultdict


# ── ANCO-HITS IMPLEMENTATION ──────────────────────────────────────────────────

def run_anco_hits(
    case_ids: list,
    argument_ids: list,
    incidence_edges: list,      # list of (case_id, argument_id), unsigned case-argument links
    seed_case_scores: dict,     # dict of labeled train case_id -> +1/-1
    iterations: int = 50,
    convergence_threshold: float = 1e-6,
) -> tuple[dict, dict]:
    """
    Run ANCO-HITS-style propagation on a case-argument bipartite graph.

    Returns:
        case_scores:     dict of case_id -> float score on [-1, +1]
        argument_scores: dict of argument_id -> float score on [-1, +1]

    Algorithm:
        1. Initialize all scores to 0
        2. Seed train labeled case scores to known outcomes (+1/-1)
        3. Update argument scores as mean of connected case scores
        4. Update case scores as mean of connected argument scores
        5. Re-apply seed scores each iteration to keep supervision anchored
        6. Normalize to [-1, +1] and repeat until convergence
    """

    # Build adjacency structures for fast lookup
    # case_to_args[case_id] = list of argument_id
    # arg_to_cases[argument_id] = list of case_id
    case_to_args = defaultdict(list)
    arg_to_cases = defaultdict(list)

    for case_id, argument_id in incidence_edges:
        case_to_args[case_id].append(argument_id)
        arg_to_cases[argument_id].append(case_id)

    # Initialize scores
    case_scores = {cid: 0.0 for cid in case_ids}
    argument_scores = {aid: 0.0 for aid in argument_ids}

    # Seed train labeled cases with known outcomes (+1 plaintiff, -1 defendant)
    for cid, seed_score in seed_case_scores.items():
        if cid in case_scores:
            case_scores[cid] = float(seed_score)

    def normalize(scores: dict) -> dict:
        """Normalize scores to [-1, +1] range."""
        values = list(scores.values())
        if not values:
            return scores
        max_abs = max(abs(v) for v in values)
        if max_abs == 0:
            return scores
        return {k: v / max_abs for k, v in scores.items()}

    prev_arg_scores = {}

    for iteration in range(iterations):
        # Step 1: Update argument scores from case scores
        new_argument_scores = {}
        for aid in argument_ids:
            connected = arg_to_cases[aid]
            if not connected:
                new_argument_scores[aid] = 0.0
                continue
            total = sum(case_scores[cid] for cid in connected)
            new_argument_scores[aid] = total / len(connected)

        # Step 2: Normalize argument scores
        new_argument_scores = normalize(new_argument_scores)

        # Step 3: Update case scores from argument scores
        new_case_scores = {}
        for cid in case_ids:
            connected = case_to_args[cid]
            if not connected:
                new_case_scores[cid] = 0.0
                continue
            total = sum(new_argument_scores[aid] for aid in connected)
            new_case_scores[cid] = total / len(connected)

        # Step 3.5: Keep train labels anchored (semi-supervised propagation)
        for cid, seed_score in seed_case_scores.items():
            if cid in new_case_scores:
                new_case_scores[cid] = float(seed_score)

        # Step 4: Normalize case scores
        new_case_scores = normalize(new_case_scores)

        # Check convergence
        if prev_arg_scores:
            max_delta = max(
                abs(new_argument_scores.get(aid, 0) - prev_arg_scores.get(aid, 0))
                for aid in argument_ids
            )
            if max_delta < convergence_threshold:
                print(f"  Converged at iteration {iteration + 1} (delta={max_delta:.2e})")
                break

        prev_arg_scores = dict(new_argument_scores)
        case_scores = new_case_scores
        argument_scores = new_argument_scores

        if (iteration + 1) % 10 == 0:
            print(f"  Iteration {iteration + 1}/{iterations}")

    return case_scores, argument_scores


def predict_outcome(case_score: float, threshold: float = 0.0) -> tuple[str, float]:
    """
    Convert a case score to a predicted outcome and confidence.

    confidence is how far the score is from 0 (the decision boundary),
    scaled to 0-1. A score of +1.0 has confidence 1.0, a score of 0.05
    has confidence 0.05.
    """
    confidence = abs(case_score)
    if case_score > threshold:
        return "plaintiff_win", confidence
    elif case_score < threshold:
        return "defendant_win", confidence
    else:
        return "uncertain", 0.0


def get_top_arguments(
    case: dict,
    argument_scores: dict,
    top_n: int = 5,
) -> list[dict]:
    """
    For a given case, return the top N arguments by absolute score
    that appear in this case, along with their scores.
    """
    case_args = case.get("arguments", [])
    scored = []
    for arg in case_args:
        aid = arg["argument_id"]
        score = argument_scores.get(aid, 0.0)
        scored.append({
            "argument_id":    aid,
            "argument_text":  arg["argument_text"],
            "argument_type":  arg["argument_type"],
            "argument_score": round(score, 4),
        })
    # Sort by absolute score descending, then by score value descending
    scored.sort(key=lambda x: (-abs(x["argument_score"]), -x["argument_score"]))
    return scored[:top_n]


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 3: ANCO-HITS scoring")
    parser.add_argument("--input",      required=True, help="Path to sec_cases_arguments.json")
    parser.add_argument("--output",     required=True, help="Path to write sec_cases_scored.json")
    parser.add_argument("--iterations", type=int, default=50, help="Max ANCO-HITS iterations")
    parser.add_argument("--val_frac",   type=float, default=0.2, help="Fraction of labeled cases to hold out for validation")
    parser.add_argument(
        "--min_argument_cases",
        type=int,
        default=5,
        help="Minimum number of labeled cases an argument must appear in to be used for training (regularization)",
    )
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    with open(args.input) as f:
        cases = json.load(f)
    print(f"  {len(cases)} cases loaded")

    # Split into labeled and unlabeled
    labeled   = [c for c in cases if c["is_labeled"] and c["defendant_result"] != "unknown"]
    unlabeled = [c for c in cases if not c["is_labeled"] or c["defendant_result"] == "unknown"]
    print(f"  Labeled:   {len(labeled)}")
    print(f"  Unlabeled: {len(unlabeled)}")

    plaintiff_wins = sum(1 for c in labeled if c["defendant_result"] == "plaintiff_win")
    defendant_wins = sum(1 for c in labeled if c["defendant_result"] == "defendant_win")
    print(f"  Plaintiff wins: {plaintiff_wins}, Defendant wins: {defendant_wins}")

    # Train/validation split on labeled cases to avoid overfitting.
    # We shuffle deterministically for reproducibility.
    rng = random.Random(42)
    labeled_shuffled = list(labeled)
    rng.shuffle(labeled_shuffled)
    split_idx = int(len(labeled_shuffled) * (1.0 - args.val_frac))
    train_cases = labeled_shuffled[:split_idx]
    val_cases = labeled_shuffled[split_idx:]

    print(f"\nTrain/validation split on labeled cases:")
    print(f"  Train: {len(train_cases)}")
    print(f"  Validation: {len(val_cases)}")

    # Count how many labeled train cases each argument appears in
    arg_case_counts = defaultdict(int)
    for case in train_cases:
        seen_in_case = set()
        for arg in case.get("arguments", []):
            if arg["argument_type"] == "outcome_type":
                continue
            aid = arg["argument_id"]
            if aid not in seen_in_case:
                arg_case_counts[aid] += 1
                seen_in_case.add(aid)

    # Choose arguments that appear in at least min_argument_cases labeled train cases
    all_argument_ids = sorted(arg_case_counts.keys())
    kept_arguments = {aid for aid, cnt in arg_case_counts.items() if cnt >= args.min_argument_cases}
    print(f"\n  Unique train-time arguments (after frequency filter >= {args.min_argument_cases}): {len(kept_arguments)}")

    # Collect all unique case IDs (train + val + unlabeled) so we score every case
    all_case_ids = [c["case_id"] for c in cases]

    # Build unsigned incidence edges for ALL cases so val/unlabeled cases can be inferred.
    # We still avoid leakage by (a) excluding outcome_type features and (b) using only
    # train-frequency-filtered arguments.
    print("\nBuilding case-argument incidence edges...")
    incidence_edges = []
    for case in cases:
        for arg in case.get("arguments", []):
            if arg["argument_type"] == "outcome_type":
                continue
            aid = arg["argument_id"]
            if aid not in kept_arguments:
                continue
            incidence_edges.append((case["case_id"], aid))

    print(f"  {len(incidence_edges)} incidence edges built across all cases")

    # Seed map from TRAIN labeled outcomes only
    seed_case_scores = {
        c["case_id"]: (+1 if c["defendant_result"] == "plaintiff_win" else -1)
        for c in train_cases
    }

    # Run ANCO-HITS
    print(f"\nRunning ANCO-HITS ({args.iterations} max iterations)...")
    case_scores, argument_scores = run_anco_hits(
        case_ids=all_case_ids,
        argument_ids=list(kept_arguments),
        incidence_edges=incidence_edges,
        seed_case_scores=seed_case_scores,
        iterations=args.iterations,
    )

    # Print top and bottom arguments by score
    sorted_args = sorted(argument_scores.items(), key=lambda x: -x[1])
    print("\nTop 10 plaintiff-favoring arguments (score near +1):")
    for aid, score in sorted_args[:10]:
        print(f"  {score:+.4f}  {aid}")
    print("\nTop 10 defendant-favoring arguments (score near -1):")
    for aid, score in sorted_args[-10:]:
        print(f"  {score:+.4f}  {aid}")

    # Attach scores and predictions to every case
    print("\nAttaching scores and predictions...")
    results = []
    for case in cases:
        cid = case["case_id"]
        score = case_scores.get(cid, 0.0)
        predicted_result, confidence = predict_outcome(score)
        top_args = get_top_arguments(case, argument_scores, top_n=5)

        results.append({
            **case,
            "anco_hits_score":       round(score, 4),
            "predicted_result":      predicted_result,
            "prediction_confidence": round(confidence, 4),
            "top_arguments":         top_args,
        })

    # Validation: check accuracy on held-out labeled validation cases only
    print("\nValidation on held-out labeled cases:")
    val_case_ids = {c["case_id"] for c in val_cases}
    correct = 0
    total_validatable = 0
    for r in results:
        if r["case_id"] in val_case_ids and r["defendant_result"] != "unknown":
            total_validatable += 1
            if r["predicted_result"] == r["defendant_result"]:
                correct += 1
    if total_validatable > 0:
        print(f"  Accuracy: {correct}/{total_validatable} = {correct/total_validatable:.1%}")

    # Summary of predictions on unlabeled cases
    unlabeled_results = [r for r in results if not r["is_labeled"] or r["defendant_result"] == "unknown"]
    pred_counts = defaultdict(int)
    for r in unlabeled_results:
        pred_counts[r["predicted_result"]] += 1
    print(f"\nPredictions on {len(unlabeled_results)} unlabeled cases:")
    for result, count in pred_counts.items():
        print(f"  {result}: {count}")

    # Write output
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDone. Written to {args.output}")

    # Also write just the argument scores for inspection and Phase 4
    arg_scores_path = args.output.replace(".json", "_argument_scores.json")
    with open(arg_scores_path, "w") as f:
        json.dump(
            [{"argument_id": aid, "score": round(score, 4)}
             for aid, score in sorted(argument_scores.items(), key=lambda x: -x[1])],
            f, indent=2
        )
    print(f"Argument scores written to {arg_scores_path}")


if __name__ == "__main__":
    main()
