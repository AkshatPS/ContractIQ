import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from config import VECTORSTORE_DIR

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def get_vectorstore_path(doc_id):
    return os.path.join(VECTORSTORE_DIR, doc_id)

def create_vectorstore(docs, doc_id):

    texts = [d["text"] for d in docs]
    metadatas = [d["metadata"] for d in docs]

    print(f"[INFO] Creating vector store with {len(texts)} chunks")

    db = FAISS.from_texts(
        texts,
        embedding_model,
        metadatas=metadatas
    )

    path = get_vectorstore_path(doc_id)

    os.makedirs(path, exist_ok=True)

    db.save_local(path)

    print("[INFO] Vectorstore saved")

    return db


def load_vectorstore(doc_id):

    path = get_vectorstore_path(doc_id)

    db = FAISS.load_local(
        path,
        embedding_model,
        allow_dangerous_deserialization=True
    )

    return db


def vectorstore_exists(doc_id):

    path = get_vectorstore_path(doc_id)

    return os.path.exists(path)