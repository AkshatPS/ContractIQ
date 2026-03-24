from features.contract_diff import run_contract_diff

pdf1 = "data/inputs/sample1.pdf"
pdf2 = "data/inputs/sample2.pdf"

results, path = run_contract_diff(pdf1, pdf2)

print("\nSUMMARY")
print(f"Added: {len(results['added'])}")
print(f"Removed: {len(results['removed'])}")
print(f"Modified: {len(results['modified'])}")