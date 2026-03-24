from features.contract_brief import run_contract_brief

pdf_path = "data/inputs/Dummy_thread.pdf"

summary = run_contract_brief(pdf_path)

print("\n========== FINAL SUMMARY ==========\n")
print(summary)