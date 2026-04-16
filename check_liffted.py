import json
from collections import Counter

with open("sec_cases_lifted.json") as f:
    data = json.load(f)

# How many lifted successfully
statuses = Counter(r["lift_status"] for r in data)
print("Lift status breakdown:", statuses)

# How many are labeled and what the outcome split looks like
labeled = [r for r in data if r["is_labeled"]]
results = Counter(r["outcome_label"]["defendant_result"] for r in labeled)
print("Labeled cases:", len(labeled))
print("Outcome split:", results)

# How populated are the charges fields
has_charges = sum(1 for r in data if r["entities"]["charges"])
print("Cases with charges:", has_charges, "/", len(data))

# How many have related_releases we can use for citation edges
# (need to check raw data for this)
print("Sample case IDs:", [r["case_id"] for r in data[:3]])
