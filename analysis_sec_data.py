#!/usr/bin/env python3
"""
SEC Litigation Data Analyzer
==============================
Analyzes CSV/SQLite output from the SEC Litigation Scraper.
Produces a comprehensive data quality report and statistical profile.

Usage:
    python analyze_sec_data.py cases.csv
    python analyze_sec_data.py sec_litigation.db
"""

import csv
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass

# ─── Load Data ───────────────────────────────────────────────────────────────

def load_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_sqlite(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM cases ORDER BY scraped_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def load_data(path):
    if path.endswith(".db"):
        return load_sqlite(path)
    return load_csv(path)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def pct(n, total):
    return f"{n}/{total} ({100*n/total:.1f}%)" if total > 0 else "0/0"

def bar(n, total, width=30):
    filled = int(width * n / total) if total > 0 else 0
    return "█" * filled + "░" * (width - filled)

def parse_dollar(s):
    """Extract numeric dollar amount from strings like '$2,860,000' or '$2.86 million'."""
    if not s:
        return 0
    m = re.search(r"\$([\d,]+(?:\.\d+)?)\s*(million|billion)?", s, re.I)
    if not m:
        return 0
    val = float(m.group(1).replace(",", ""))
    if m.group(2):
        mult = m.group(2).lower()
        if mult == "million":
            val *= 1_000_000
        elif mult == "billion":
            val *= 1_000_000_000
    return val

def split_field(val):
    """Split semicolon-delimited field into list of values."""
    if not val:
        return []
    return [v.strip() for v in val.split(";") if v.strip()]

def top_n(counter, n=10):
    return counter.most_common(n)


# ─── Analysis ────────────────────────────────────────────────────────────────

def analyze(rows):
    total = len(rows)
    if total == 0:
        print("No data to analyze.")
        return

    print()
    print("=" * 70)
    print(f"  SEC LITIGATION DATA ANALYSIS REPORT")
    print(f"  Total cases: {total}")
    print("=" * 70)

    # ── 1. Field Completeness ────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  1. FIELD COMPLETENESS")
    print(f"{'─' * 70}\n")

    fields = [
        "case_title", "citation", "court", "date", "respondent",
        "defendant_roles", "defendant_employer", "employer_crd_cik",
        "co_defendants", "relief_defendants",
        "sec_attorneys", "sec_regional_office", "judges", "judgment_type",
        "summary", "outcome", "legal_topic", "charges_and_sections",
        "company_domain", "total_fine_amount", "total_victim_losses",
        "scheme_duration", "scheme_method", "victim_count", "admission_status",
        "parallel_actions", "related_releases", "case_status",
        "scheme_start_date", "scheme_end_date",
        "complaint_filed_date", "judgment_date",
        "regulatory_registrations", "defendant_sentence",
        "final_judgment_details", "source_url", "pdf_insights",
        "associated_documents",
    ]

    filled_counts = {}
    for field in fields:
        count = sum(1 for r in rows if r.get(field, "").strip())
        filled_counts[field] = count

    # Sort by fill rate descending
    sorted_fields = sorted(filled_counts.items(), key=lambda x: -x[1])

    print(f"  {'Field':<30s} {'Filled':>8s}  {'Rate':>6s}  Coverage")
    print(f"  {'─'*30} {'─'*8}  {'─'*6}  {'─'*30}")
    for field, count in sorted_fields:
        rate = count / total * 100
        print(f"  {field:<30s} {count:>6d}  {rate:>5.1f}%  {bar(count, total)}")

    filled_all = sum(1 for f, c in filled_counts.items() if c == total)
    filled_majority = sum(1 for f, c in filled_counts.items() if c > total * 0.5)
    filled_some = sum(1 for f, c in filled_counts.items() if c > 0)
    print(f"\n  Fields at 100%: {filled_all}  |  >50%: {filled_majority}  |  >0%: {filled_some}  |  Total: {len(fields)}")

    # ── 2. Legal Topics Distribution ─────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  2. LEGAL TOPICS DISTRIBUTION")
    print(f"{'─' * 70}\n")

    topic_counter = Counter()
    for r in rows:
        for t in split_field(r.get("legal_topic", "")):
            topic_counter[t] += 1

    if topic_counter:
        max_count = topic_counter.most_common(1)[0][1]
        for topic, count in top_n(topic_counter, 15):
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {topic}")
    else:
        print("  No legal topics extracted.")

    # ── 3. Court Distribution ────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  3. COURT DISTRIBUTION")
    print(f"{'─' * 70}\n")

    court_counter = Counter()
    for r in rows:
        court = r.get("court", "").strip()
        if court:
            court_counter[court] += 1

    if court_counter:
        max_count = court_counter.most_common(1)[0][1]
        for court, count in top_n(court_counter, 15):
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {court}")
        print(f"\n  Unique courts: {len(court_counter)}")
    else:
        print("  No court data extracted.")

    # ── 4. Outcome Distribution ──────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  4. OUTCOME DISTRIBUTION")
    print(f"{'─' * 70}\n")

    outcome_counter = Counter()
    for r in rows:
        for o in split_field(r.get("outcome", "")):
            outcome_counter[o] += 1

    if outcome_counter:
        max_count = outcome_counter.most_common(1)[0][1]
        for outcome, count in top_n(outcome_counter, 15):
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {outcome}")
    else:
        print("  No outcome data extracted.")

    # ── 5. Financial Analysis ────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  5. FINANCIAL ANALYSIS")
    print(f"{'─' * 70}\n")

    # Parse fine amounts
    cases_with_fines = 0
    disgorgement_total = 0
    penalty_total = 0
    all_victim_losses = []

    for r in rows:
        fines = r.get("total_fine_amount", "")
        if fines:
            cases_with_fines += 1
            for part in fines.split(";"):
                part = part.strip()
                val = parse_dollar(part)
                if "disgorgement" in part.lower():
                    disgorgement_total += val
                elif "penalty" in part.lower():
                    penalty_total += val

        losses = r.get("total_victim_losses", "")
        if losses:
            val = parse_dollar(losses)
            if val > 0:
                all_victim_losses.append(val)

    print(f"  Cases with fine data:        {pct(cases_with_fines, total)}")
    print(f"  Total disgorgement:          ${disgorgement_total:,.0f}")
    print(f"  Total civil penalties:       ${penalty_total:,.0f}")
    print(f"  Combined:                    ${disgorgement_total + penalty_total:,.0f}")

    if all_victim_losses:
        print(f"\n  Cases with victim loss data: {len(all_victim_losses)}")
        print(f"  Total victim losses:         ${sum(all_victim_losses):,.0f}")
        print(f"  Average loss per case:       ${sum(all_victim_losses)/len(all_victim_losses):,.0f}")
        sorted_losses = sorted(all_victim_losses, reverse=True)
        print(f"  Largest single loss:         ${sorted_losses[0]:,.0f}")
        if len(sorted_losses) >= 5:
            print(f"  Median loss:                 ${sorted_losses[len(sorted_losses)//2]:,.0f}")
    else:
        print("\n  No victim loss data extracted.")

    # ── 6. Charges & Statutory Sections ──────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  6. CHARGES AND STATUTORY SECTIONS")
    print(f"{'─' * 70}\n")

    charge_counter = Counter()
    for r in rows:
        for c in split_field(r.get("charges_and_sections", "")):
            charge_counter[c] += 1

    if charge_counter:
        max_count = charge_counter.most_common(1)[0][1]
        for charge, count in top_n(charge_counter, 15):
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {charge}")
        print(f"\n  Unique charges/sections: {len(charge_counter)}")
    else:
        print("  No charge data extracted.")

    # ── 7. SEC Enforcement Staff ─────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  7. SEC ENFORCEMENT STAFF")
    print(f"{'─' * 70}\n")

    attorney_counter = Counter()
    office_counter = Counter()
    for r in rows:
        for a in split_field(r.get("sec_attorneys", "")):
            attorney_counter[a] += 1
        office = r.get("sec_regional_office", "").strip()
        if office:
            office_counter[office] += 1

    if office_counter:
        print("  Regional Offices:")
        max_count = office_counter.most_common(1)[0][1]
        for office, count in top_n(office_counter, 12):
            print(f"    {count:>4d}  {bar(count, max_count, 20)}  {office}")

    if attorney_counter:
        print(f"\n  Most Active Attorneys (top 10):")
        for atty, count in top_n(attorney_counter, 10):
            print(f"    {count:>4d} cases  {atty}")
        print(f"\n  Unique attorneys: {len(attorney_counter)}")
    else:
        print("  No SEC attorney data extracted.")

    # ── 8. Judgment Types ────────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  8. JUDGMENT TYPES")
    print(f"{'─' * 70}\n")

    jtype_counter = Counter()
    for r in rows:
        for j in split_field(r.get("judgment_type", "")):
            jtype_counter[j] += 1

    if jtype_counter:
        max_count = jtype_counter.most_common(1)[0][1]
        for jt, count in jtype_counter.most_common():
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {jt}")
    else:
        print("  No judgment type data extracted.")

    # ── 9. Admission Status ──────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  9. ADMISSION STATUS")
    print(f"{'─' * 70}\n")

    admission_counter = Counter()
    for r in rows:
        ad = r.get("admission_status", "").strip()
        if ad:
            admission_counter[ad] += 1
        else:
            admission_counter["(not extracted)"] += 1

    max_count = admission_counter.most_common(1)[0][1]
    for ad, count in admission_counter.most_common():
        print(f"  {count:>5d}  {bar(count, max_count, 25)}  {ad}")

    # ── 10. Company Domains / Industries ─────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  10. COMPANY DOMAINS / INDUSTRIES")
    print(f"{'─' * 70}\n")

    domain_counter = Counter()
    for r in rows:
        for d in split_field(r.get("company_domain", "")):
            domain_counter[d] += 1

    if domain_counter:
        max_count = domain_counter.most_common(1)[0][1]
        for dom, count in top_n(domain_counter, 15):
            print(f"  {count:>5d}  {bar(count, max_count, 25)}  {dom}")
    else:
        print("  No company domain data extracted.")

    # ── 11. Temporal Analysis ────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  11. TEMPORAL ANALYSIS")
    print(f"{'─' * 70}\n")

    year_counter = Counter()
    for r in rows:
        date = r.get("date", "")
        m = re.search(r"(\d{4})", date)
        if m:
            year_counter[m.group(1)] += 1

    if year_counter:
        print("  Cases by year:")
        for year in sorted(year_counter.keys(), reverse=True)[:15]:
            count = year_counter[year]
            max_y = max(year_counter.values())
            print(f"    {year}  {count:>4d}  {bar(count, max_y, 25)}")

    # Scheme durations
    durations_months = []
    for r in rows:
        sd = r.get("scheme_duration", "")
        start = r.get("scheme_start_date", "")
        end = r.get("scheme_end_date", "")
        if start and end:
            sy = re.search(r"(\d{4})", start)
            ey = re.search(r"(\d{4})", end)
            if sy and ey:
                dur = int(ey.group(1)) - int(sy.group(1))
                if 0 < dur < 50:
                    durations_months.append(dur)

    if durations_months:
        avg_dur = sum(durations_months) / len(durations_months)
        print(f"\n  Scheme duration statistics ({len(durations_months)} cases with data):")
        print(f"    Average: {avg_dur:.1f} years")
        print(f"    Longest: {max(durations_months)} years")
        print(f"    Shortest: {min(durations_months)} year(s)")

    # Temporal chain completeness
    temporal_fields = ["scheme_start_date", "scheme_end_date", "complaint_filed_date", "judgment_date"]
    print(f"\n  Temporal chain completeness:")
    for tf in temporal_fields:
        count = sum(1 for r in rows if r.get(tf, "").strip())
        print(f"    {tf:<25s}  {pct(count, total)}")

    # ── 12. Parallel Actions ─────────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  12. PARALLEL ACTIONS AND CROSS-REFERENCES")
    print(f"{'─' * 70}\n")

    has_parallel = sum(1 for r in rows if r.get("parallel_actions", "").strip())
    has_related = sum(1 for r in rows if r.get("related_releases", "").strip())
    has_criminal = sum(1 for r in rows if "criminal" in r.get("parallel_actions", "").lower())
    has_admin = sum(1 for r in rows if "admin" in r.get("parallel_actions", "").lower())
    has_finra = sum(1 for r in rows if "finra" in r.get("parallel_actions", "").lower())
    has_sentence = sum(1 for r in rows if r.get("defendant_sentence", "").strip())

    print(f"  Cases with parallel actions:   {pct(has_parallel, total)}")
    print(f"    Criminal prosecutions:       {pct(has_criminal, total)}")
    print(f"    Administrative proceedings:  {pct(has_admin, total)}")
    print(f"    FINRA actions:               {pct(has_finra, total)}")
    print(f"  Cases with related releases:   {pct(has_related, total)}")
    print(f"  Cases with criminal sentence:  {pct(has_sentence, total)}")

    # ── 13. Defendant Profiles ───────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  13. DEFENDANT PROFILES")
    print(f"{'─' * 70}\n")

    role_counter = Counter()
    for r in rows:
        for role in split_field(r.get("defendant_roles", "")):
            role_counter[role] += 1

    if role_counter:
        print("  Defendant Roles:")
        max_count = role_counter.most_common(1)[0][1]
        for role, count in top_n(role_counter, 12):
            print(f"    {count:>4d}  {bar(count, max_count, 20)}  {role}")

    employer_counter = Counter()
    for r in rows:
        emp = r.get("defendant_employer", "").strip()
        if emp:
            employer_counter[emp] += 1

    if employer_counter:
        print(f"\n  Employer Entities (top 10):")
        for emp, count in top_n(employer_counter, 10):
            print(f"    {count:>4d} cases  {emp}")
        print(f"\n  Unique employers: {len(employer_counter)}")

    # ── 14. PDF Analysis Coverage ────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  14. PDF ANALYSIS COVERAGE")
    print(f"{'─' * 70}\n")

    has_pdfs = sum(1 for r in rows if r.get("associated_documents", "").strip())
    has_insights = sum(1 for r in rows if r.get("pdf_insights", "").strip())
    has_jd = sum(1 for r in rows if r.get("final_judgment_details", "").strip())
    has_narrative = sum(1 for r in rows if "PDF DETAILS:" in r.get("summary", ""))

    print(f"  Cases with PDF documents:      {pct(has_pdfs, total)}")
    print(f"  Cases with PDF insights:       {pct(has_insights, total)}")
    print(f"  Cases with judgment details:   {pct(has_jd, total)}")
    print(f"  Cases with PDF narratives:     {pct(has_narrative, total)}")

    doc_counter = Counter()
    for r in rows:
        for d in split_field(r.get("associated_documents", "")):
            doc_counter[d] += 1

    if doc_counter:
        print(f"\n  Document types analyzed:")
        for doc, count in top_n(doc_counter, 10):
            print(f"    {count:>4d}  {doc}")

    # ── 15. Knowledge Graph Readiness ────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  15. KNOWLEDGE GRAPH READINESS SCORE")
    print(f"{'─' * 70}\n")

    kg_fields = {
        "Entity: Person-Role":      ("defendant_roles", 0.15),
        "Entity: Employer":         ("defendant_employer", 0.10),
        "Entity: Court":            ("court", 0.10),
        "Entity: Judge":            ("judges", 0.10),
        "Entity: SEC Attorney":     ("sec_attorneys", 0.10),
        "Relation: Charges":        ("charges_and_sections", 0.10),
        "Relation: Penalties":      ("total_fine_amount", 0.10),
        "Relation: Parallel":       ("parallel_actions", 0.05),
        "Temporal: Scheme dates":   ("scheme_duration", 0.05),
        "Temporal: Filing dates":   ("complaint_filed_date", 0.05),
        "Attribute: Admission":     ("admission_status", 0.05),
        "Attribute: Domain":        ("company_domain", 0.05),
    }

    total_score = 0
    print(f"  {'Component':<30s}  {'Fill Rate':>10s}  {'Weight':>7s}  {'Score':>7s}")
    print(f"  {'─'*30}  {'─'*10}  {'─'*7}  {'─'*7}")
    for component, (field, weight) in kg_fields.items():
        count = sum(1 for r in rows if r.get(field, "").strip())
        rate = count / total if total > 0 else 0
        score = rate * weight * 100
        total_score += score
        print(f"  {component:<30s}  {rate*100:>8.1f}%  {weight*100:>5.0f}%  {score:>6.2f}")

    print(f"  {'─'*30}  {'─'*10}  {'─'*7}  {'─'*7}")
    print(f"  {'TOTAL KG READINESS SCORE':<30s}  {'':>10s}  {'100%':>7s}  {total_score:>5.1f}/100")

    if total_score >= 80:
        grade = "EXCELLENT -- ready for graph construction"
    elif total_score >= 60:
        grade = "GOOD -- most entity relationships extractable"
    elif total_score >= 40:
        grade = "FAIR -- core entities present, relationships sparse"
    else:
        grade = "NEEDS WORK -- insufficient for meaningful graph"

    print(f"\n  Assessment: {grade}")

    # ── 16. Summary Statistics ───────────────────────────────────────────

    print(f"\n{'─' * 70}")
    print("  16. SUMMARY")
    print(f"{'─' * 70}\n")

    avg_summary_len = sum(len(r.get("summary", "")) for r in rows) / total if total > 0 else 0
    avg_fields_filled = sum(
        sum(1 for f in fields if r.get(f, "").strip())
        for r in rows
    ) / total if total > 0 else 0

    print(f"  Total cases:                   {total}")
    print(f"  Average fields filled per case: {avg_fields_filled:.1f} / {len(fields)}")
    print(f"  Average summary length:         {avg_summary_len:.0f} characters")
    print(f"  Unique courts:                  {len(court_counter)}")
    print(f"  Unique legal topics:            {len(topic_counter)}")
    print(f"  Unique charges/sections:        {len(charge_counter)}")
    print(f"  Unique SEC attorneys:            {len(attorney_counter)}")
    print(f"  KG readiness score:             {total_score:.1f}/100")

    print(f"\n{'=' * 70}")
    print(f"  END OF REPORT")
    print(f"{'=' * 70}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_sec_data.py <file.csv|file.db>")
        print("\nAccepts CSV or SQLite database from the SEC Litigation Scraper.")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit(f"File not found: {path}")

    print(f"\nLoading data from: {path}")
    rows = load_data(path)
    print(f"Loaded {len(rows)} cases.")

    analyze(rows)