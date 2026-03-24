from qa.qa_pipeline import initialize_document, ask_question


def run_qa_system(pdf_path, question):

    db = initialize_document(pdf_path)

    answer = ask_question(db, question)

    return answer