from features.contract_brief import run_contract_brief

pdf_paths = [
    "data/inputs/ZogenixInc_20190509_10-Q_EX-10.2_11663313_EX-10.2_Distributor Agreement.pdf"
]

for pdf_path in pdf_paths:
    print(f"\nProcessing: {pdf_path}")

    summary = run_contract_brief(pdf_path)

    print("\n========== FINAL SUMMARY ==========\n")
    print(summary)