# SEC Litigation Releases — Multi-Target Classification

## What This Project Does

This project takes **10,914 SEC enforcement litigation releases** (scraped into a CSV) and builds machine learning classifiers that can automatically predict three things about any SEC case, given just its text summary:

1. **What type of legal violation is it?** (Legal Topic)
2. **How will the case resolve?** (Case Status / Outcome)
3. **What industry is the defendant in?** (Industry Domain)

---

## The Data

**Source:** `sec_litigation_releases_20260403_234416.csv` — SEC enforcement actions spanning 1995–2025.

Each row is a single litigation release containing a long free-text `summary` (average ~3,400 characters) describing the case facts, plus structured fields like charges filed, judgment type, court, fines, and more.

After filtering to rows that have valid values for all three targets and a non-trivial summary, we work with **8,563 cases**.

---

## The Three Classification Tasks

### Task 1: Legal Topic Classification (16 classes)

**Question:** *"Given a case summary, what type of securities violation is this?"*

The model predicts one of 16 categories:

| Category | Examples in data |
|----------|-----------------|
| Broker-Dealer Violations | Unregistered brokers, sales practice abuses |
| Securities Fraud | General fraud charges under 10b-5 |
| Insider Trading | Trading on material non-public information |
| Books & Records | Failure to maintain proper books/records |
| Inv. Adviser Misconduct | Advisers breaching fiduciary duty |
| Ponzi Scheme | Classic Ponzi/pyramid structures |
| Misappropriation | Stealing client funds |
| Crypto/Digital Assets | ICO fraud, unregistered crypto offerings |
| Accounting Fraud | Cooking the books, revenue manipulation |
| ... and others | Market Manipulation, Pump & Dump, etc. |

**Why it matters:** Automatically tagging the violation type from raw text saves hours of manual legal review and enables trend analysis across thousands of cases.

### Task 2: Case Status / Outcome Prediction (6 classes)

**Question:** *"Given the case details, how did (or will) this case resolve?"*

| Status | What it means |
|--------|---------------|
| **Complaint filed** | Case was initiated but no final resolution recorded yet |
| **Settled/Consented** | Defendant agreed to a settlement or consent decree |
| **Final judgment entered** | Court issued a final judgment (often after trial/motion) |
| **Pending** | Case is still actively being litigated |
| **Dismissed** | Case was thrown out |
| **Other** | Rare statuses (continuing, partial resolution, etc.) |

**Why it matters:** Predicting whether a case will settle vs. go to judgment is directly useful for litigation strategy — it helps lawyers and regulators estimate likely outcomes early.

### Task 3: Industry Domain Classification (18 classes)

**Question:** *"What industry does the defendant company operate in?"*

Top domains include Banking/Financial Services, Brokerage, Media/Entertainment, Hedge Fund, Energy, Technology, Pharmaceuticals, Real Estate, and others.

**Why it matters:** Understanding which industries face which types of enforcement helps regulators allocate resources and helps researchers study enforcement patterns across sectors.

---

## How It Works (Methodology)

### Feature Engineering

The models learn from two types of features:

1. **Text features (TF-IDF):** The `summary` field is converted into a 10,000-dimensional TF-IDF vector using unigrams and bigrams. This captures the "bag of words" — which words and word pairs appear, weighted by how distinctive they are. For example, the word "insider" is very distinctive for insider trading cases, while "the" appears everywhere and gets downweighted.

2. **Structured features:** The `charges_and_sections` field (e.g., "Exchange Act § 10(b); Rule 10b-5") and `judgment_type` field are also TF-IDF encoded and appended. These give the model direct access to the legal statutes cited and the procedural posture.

Combined, each case is represented as a ~10,250-dimensional sparse vector.

### Models Tested

| Model | How it works |
|-------|-------------|
| **Logistic Regression** | Finds a linear boundary between classes. Fast, interpretable, strong baseline for text. |
| **Linear SVC** | Support Vector Machine — finds the maximum-margin boundary between classes. Often the best for high-dimensional text data. |
| **Random Forest** | Ensemble of decision trees. Good for structured data but struggles with very high-dimensional sparse text features. |

### Train/Test Split

- **80% training** (6,850 cases) — the model learns from these
- **20% test** (1,713 cases) — held out, never seen during training, used to measure real performance
- **Stratified split** — ensures each class appears in train and test in the same proportions

---

## Results

### Summary Table

| Task | Best Model | Accuracy | F1 (weighted) | F1 (macro) |
|------|-----------|----------|---------------|------------|
| Legal Topic (16 classes) | Linear SVC | **68.7%** | 0.676 | 0.546 |
| Case Status (6 classes) | Linear SVC | **83.9%** | 0.832 | 0.557 |
| Industry Domain (18 classes) | Linear SVC | **68.8%** | 0.684 | 0.640 |

### What Do These Metrics Mean?

- **Accuracy:** The percentage of cases the model labels correctly. Simple and intuitive but can be misleading when classes are imbalanced (e.g., if 60% of cases are "Securities Fraud", a model that always guesses "Securities Fraud" gets 60% accuracy for free).

- **F1 (weighted):** The harmonic mean of precision and recall, averaged across all classes but weighted by how many examples each class has. This is the most reliable single number — it rewards models that do well on common classes and doesn't get inflated by always-guessing the majority.

- **F1 (macro):** Same F1 but averaged equally across all classes regardless of size. A class with 7 examples counts the same as a class with 600. This penalizes models that ignore rare classes. A big gap between weighted and macro F1 means the model struggles on minority classes.

### Interpreting Each Task

#### Legal Topic — 68.7% accuracy

This is a **16-class** problem, so random guessing would give ~6%. The model is 11x better than chance. Highlights:

- **Insider Trading** is the easiest to detect (F1 = 0.91) — these cases use very distinctive language ("traded," "material non-public information," "tipped")
- **Broker-Dealer Violations** (F1 = 0.70) and **Inv. Adviser Misconduct** (F1 = 0.76) are also well-detected
- **Offering Fraud** (F1 = 0.16) and **Internal Controls Failure** (F1 = 0.14) are hard — they're rare and their language overlaps heavily with general Securities Fraud

The weighted F1 of 0.676 means: for the cases the model encounters most often, it's right about 2/3 of the time with good precision-recall balance.

#### Case Status — 83.9% accuracy

This is the **strongest performer**. The model correctly predicts how a case resolved 84% of the time. Why is this easier?

- The summary text itself often contains resolution language ("defendant consented to," "final judgment was entered," "complaint alleges" for ongoing cases)
- The `judgment_type` feature directly correlates — "Consent Judgment" strongly predicts "Settled/Consented"
- The three main classes (Complaint filed, Settled, Final judgment) are large and well-separated

Weakness: rare statuses like Dismissed (only 7 in test set) and Other (3 in test set) are essentially invisible to the model.

#### Industry Domain — 68.8% accuracy

An **18-class** problem (random baseline ~5.5%), so 68.8% is strong in relative terms. The macro F1 of 0.640 is actually the best across all three tasks — meaning this model handles minority classes better than the others.

The summary text mentions industry-specific terms (drug names for pharma, "crude oil" for energy, "cryptocurrency" for crypto) that make domain classification feasible even without explicit sector labels as input.

### Why Linear SVC Wins

Linear SVC consistently outperforms the other two models because:
1. Text data is very high-dimensional (10,000+ features) and sparse — linear models thrive here
2. SVMs maximize the margin between classes, which generalizes well to unseen text
3. Random Forests struggle because they can't efficiently handle 10,000 sparse features (they split one feature at a time)

---

## Output Files

| File | Description |
|------|-------------|
| `sec_classification.ipynb` | Full notebook with code, outputs, and charts |
| `label_distributions.png` | Bar charts showing class distributions for all 3 targets |
| `model_comparison.png` | Side-by-side accuracy/F1 comparison across models and tasks |
| `confusion_matrices.png` | Normalized confusion matrices showing per-class performance |
| `feature_importance.png` | Top TF-IDF features driving each class prediction |

---

## Prediction Demo

The notebook includes a `predict_case()` function. Pass any SEC case summary text and get all three predictions instantly:

```
=== Multi-Target Prediction ===
  Legal Topic          → Broker-Dealer Violations
  Case Status          → Settled/Consented
  Industry Domain      → Banking/Financial Services
```

---

## Possible Next Steps

- **Better text models:** Fine-tune a transformer (LegalBERT, SEC-BERT) for higher accuracy, especially on rare classes
- **Multi-label classification:** Currently we take only the primary label; many cases have multiple topics (e.g., "Insider Trading; Securities Fraud")
- **Add more features:** Fine amounts, scheme duration, court district, number of defendants
- **Cross-reference with Stanford SCAC:** Merge SEC enforcement data with private class action outcomes for a richer dataset (as outlined in `data_source_guide.md`)
