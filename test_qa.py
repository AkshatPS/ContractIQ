from features.qa_system import run_qa_system

pdf_path = "data/inputs/Dummy_thread.pdf"

question = "What are the termination conditions?"

answer = run_qa_system(pdf_path, question)

print("\nANSWER\n")
print(answer)