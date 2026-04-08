from qa.qa_pipeline import QAPipeline
import fitz  # PyMuPDF


def extract_pdf_pages(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []

    for page in doc:
        text = page.get_text("text")
        pages.append(text)

    return pages


json_path = "data/outputs/classified/ZogenixInc_20190509_10-Q_EX-10.2_11663313_EX-10.2_Distributor Agreement.json"
pdf_path = "data/inputs/ZogenixInc_20190509_10-Q_EX-10.2_11663313_EX-10.2_Distributor Agreement.pdf"

full_text_pages = extract_pdf_pages(pdf_path)

qa = QAPipeline(json_path, full_text_pages)

question = "What happens if payment is delayed?"
answer = qa.answer_question(question)

print("\n===== FINAL ANSWER =====\n")
print(answer)