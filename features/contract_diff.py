import os
from pipelines.contract_pipeline import run_pipeline
from pipelines.diff_engine import match_semantic_global
from config import REPORTS_DIR
from utils.file_handler import get_filename


def run_contract_diff(pdf1, pdf2):

    print("\n[DIFF] Running semantic contract comparison...")

    # Get structured data
    data1 = run_pipeline(pdf1)
    data2 = run_pipeline(pdf2)

    # Semantic comparison
    results = match_semantic_global(data1, data2)

    # Save report
    os.makedirs(REPORTS_DIR, exist_ok=True)

    name1 = get_filename(pdf1)
    name2 = get_filename(pdf2)

    report_path = os.path.join(REPORTS_DIR, f"{name1}_vs_{name2}_diff.txt")

    with open(report_path, "w", encoding="utf-8") as f:

        f.write("SEMANTIC CONTRACT DIFFERENCE REPORT\n\n")

        f.write(f"Added Clauses: {len(results['added'])}\n")
        f.write(f"Removed Clauses: {len(results['removed'])}\n")
        f.write(f"Modified Clauses: {len(results['modified'])}\n\n")

        if results["removed"]:
            f.write("=== REMOVED CLAUSES ===\n")
            for c in results["removed"]:
                f.write(f"- {c}\n")
            f.write("\n")

        if results["added"]:
            f.write("=== ADDED CLAUSES ===\n")
            for c in results["added"]:
                f.write(f"- {c}\n")
            f.write("\n")

        if results["modified"]:
            f.write("=== MODIFIED CLAUSES ===\n")
            for m in results["modified"]:
                f.write(f"OLD: {m['old']}\n")
                f.write(f"NEW: {m['new']}\n")
                f.write(f"SCORE: {m['score']}\n\n")

    print(f"[SUCCESS] Diff report saved: {report_path}")

    return results, report_path