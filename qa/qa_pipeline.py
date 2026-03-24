import os
import ollama

from pipelines.contract_pipeline import run_pipeline
from qa.vector_manager import create_vectorstore, load_vectorstore, vectorstore_exists
from config import VECTORSTORE_DIR
from utils.file_handler import get_filename


def initialize_document(pdf_path):

    doc_id = get_filename(pdf_path)
    vector_path = os.path.join(VECTORSTORE_DIR, doc_id)

    if vectorstore_exists(doc_id):
        print("[INFO] Vector store exists. Loading...")
        return load_vectorstore(doc_id)

    print("[INFO] Running contract pipeline...")
    data = run_pipeline(pdf_path)

    classified = data["classified_clauses"]

    docs = []

    for label, clauses in classified.items():

        for clause in clauses:
            docs.append({
                "text": clause,
                "metadata": {
                    "type": "clause",
                    "clause_type": label
                }
            })

    print(f"[INFO] Total docs for embedding: {len(docs)}")

    db = create_vectorstore(docs, doc_id)

    return db


def ask_question(db, question):

    docs = db.similarity_search(question, k=5)

    if not docs:
        return "The document does not contain relevant information."

    context = "\n\n".join([d.page_content for d in docs])

    context = context[:8000]

    prompt = f"""
    You are a legal assistant.

    Answer the question using ONLY the provided context.

    Rules:
    - Do NOT hallucinate
    - If answer is not explicitly stated, say: "The document does not contain this information."
    - Answer clearly and concisely
    - Use complete sentences

    Context:
    {context}

    Question:
    {question}
    """

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]