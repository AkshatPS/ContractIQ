import os
from features.contract_diff import run_contract_diff


def test_document_diff():
    print("\n========== TESTING DOCUMENT DIFFERENCE FEATURE ==========\n")

    # Change these paths as needed
    pdf_a = "data/inputs/samplea.pdf"
    pdf_b = "data/inputs/samplea_changed.pdf"

    # Check if files exist
    if not os.path.exists(pdf_a):
        print(f"[ERROR] File not found: {pdf_a}")
        return

    if not os.path.exists(pdf_b):
        print(f"[ERROR] File not found: {pdf_b}")
        return

    # Run diff
    result = run_contract_diff(pdf_a, pdf_b)

    print("\n========== DIFF OUTPUT ==========\n")
    print(result)


if __name__ == "__main__":
    test_document_diff()