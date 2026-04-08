import os
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer


class QASystem:
    def __init__(self, json_data, doc_name, base_index_dir="faiss_indexes"):

        self.json_data = json_data
        self.doc_name = doc_name.replace(".json", "")

        self.base_index_dir = base_index_dir
        self.doc_index_dir = os.path.join(self.base_index_dir, self.doc_name)
        os.makedirs(self.doc_index_dir, exist_ok=True)

        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Storage
        self.clauses = []
        self.clause_metadata = []

        self.page_chunks = []
        self.page_metadata = []

        self.clause_index = None
        self.page_index = None

    def build_page_chunks(self, full_text, chunk_size=3, overlap=1):

        chunks = []
        metadata = []

        i = 0
        while i < len(full_text):
            chunk_pages = full_text[i:i + chunk_size]
            chunk_text = "\n".join(chunk_pages)

            chunks.append(chunk_text)
            metadata.append({
                "page_start": i + 1,
                "page_end": i + len(chunk_pages)
            })

            i += chunk_size - overlap

        return chunks, metadata

    def index_exists(self):
        return (
            os.path.exists(os.path.join(self.doc_index_dir, "clause.index")) and
            os.path.exists(os.path.join(self.doc_index_dir, "page.index")) and
            os.path.exists(os.path.join(self.doc_index_dir, "clauses.pkl")) and
            os.path.exists(os.path.join(self.doc_index_dir, "pages.pkl"))
        )

    def save_indexes(self):

        print("[INFO] Saving FAISS indexes...")

        faiss.write_index(self.clause_index,
            os.path.join(self.doc_index_dir, "clause.index"))

        faiss.write_index(self.page_index,
            os.path.join(self.doc_index_dir, "page.index"))

        with open(os.path.join(self.doc_index_dir, "clauses.pkl"), "wb") as f:
            pickle.dump(self.clauses, f)

        with open(os.path.join(self.doc_index_dir, "clause_metadata.pkl"), "wb") as f:
            pickle.dump(self.clause_metadata, f)

        with open(os.path.join(self.doc_index_dir, "pages.pkl"), "wb") as f:
            pickle.dump(self.page_chunks, f)

        with open(os.path.join(self.doc_index_dir, "page_metadata.pkl"), "wb") as f:
            pickle.dump(self.page_metadata, f)

    def load_indexes(self):

        print("[INFO] Loading FAISS indexes...")

        self.clause_index = faiss.read_index(
            os.path.join(self.doc_index_dir, "clause.index"))

        self.page_index = faiss.read_index(
            os.path.join(self.doc_index_dir, "page.index"))

        with open(os.path.join(self.doc_index_dir, "clauses.pkl"), "rb") as f:
            self.clauses = pickle.load(f)

        with open(os.path.join(self.doc_index_dir, "clause_metadata.pkl"), "rb") as f:
            self.clause_metadata = pickle.load(f)

        with open(os.path.join(self.doc_index_dir, "pages.pkl"), "rb") as f:
            self.page_chunks = pickle.load(f)

        with open(os.path.join(self.doc_index_dir, "page_metadata.pkl"), "rb") as f:
            self.page_metadata = pickle.load(f)

    def initialize(self, full_text_pages):

        if self.index_exists():
            self.load_indexes()
            return

        print("[INFO] Building FAISS indexes from scratch...")

        for label, clauses in self.json_data["classified_clauses"].items():
            for clause in clauses:
                self.clauses.append(clause)
                self.clause_metadata.append({"label": label})

        self.page_chunks, self.page_metadata = self.build_page_chunks(full_text_pages)

        clause_embeddings = self.embedder.encode(
            self.clauses, convert_to_numpy=True
        )
        faiss.normalize_L2(clause_embeddings)

        self.clause_index = faiss.IndexFlatIP(clause_embeddings.shape[1])
        self.clause_index.add(clause_embeddings)

        page_embeddings = self.embedder.encode(
            self.page_chunks, convert_to_numpy=True
        )
        faiss.normalize_L2(page_embeddings)

        self.page_index = faiss.IndexFlatIP(page_embeddings.shape[1])
        self.page_index.add(page_embeddings)

        self.save_indexes()

    def retrieve(self, question, top_k_clauses=5, top_k_pages=3):

        query_embedding = self.embedder.encode([question])
        faiss.normalize_L2(query_embedding)

        _, clause_idx = self.clause_index.search(query_embedding, top_k_clauses)
        _, page_idx = self.page_index.search(query_embedding, top_k_pages)

        clause_results = [
            {
                "text": self.clauses[i],
                "label": self.clause_metadata[i]["label"]
            }
            for i in clause_idx[0]
        ]

        page_results = [
            {
                "text": self.page_chunks[i],
                "page_start": self.page_metadata[i]["page_start"],
                "page_end": self.page_metadata[i]["page_end"]
            }
            for i in page_idx[0]
        ]

        return clause_results, page_results

    def build_context(self, clause_results, page_results, max_chars=12000):

        context = ""

        for c in clause_results:
            block = f"[CLAUSE | {c['label']}]\n{c['text']}\n\n"
            if len(context) + len(block) > max_chars:
                break
            context += block

        for p in page_results:
            block = f"[PAGES {p['page_start']}-{p['page_end']}]\n{p['text']}\n\n"
            if len(context) + len(block) > max_chars:
                break
            context += block

        return context

    def get_context(self, question):

        clause_results, page_results = self.retrieve(question)

        context = self.build_context(clause_results, page_results)

        return context, clause_results, page_results