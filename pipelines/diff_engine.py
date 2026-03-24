import json
import fitz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('all-MiniLM-L6-v2')


def extract_all_clauses(json_data):
    clauses = []

    classified = json_data.get("classified_clauses", {})

    for label, clause_list in classified.items():

        clauses.extend(clause_list)

    return clauses


def load_classified_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    return text.lower().strip().replace("\n", " ")


def match_semantic_global(json_a, json_b, threshold=0.75):
    clauses_a = extract_all_clauses(json_a)
    clauses_b = extract_all_clauses(json_b)

    if not clauses_a or not clauses_b:
        return {
            "modified": [],
            "added": clauses_b,
            "removed": clauses_a
        }

    clean_a = [clean_text(c) for c in clauses_a]
    clean_b = [clean_text(c) for c in clauses_b]

    emb_a = model.encode(clean_a)
    emb_b = model.encode(clean_b)

    sim_matrix = cosine_similarity(emb_a, emb_b)

    matched_a = set()
    matched_b = set()
    used_b = set()

    results = {
        "modified": [],
        "added": [],
        "removed": []
    }

    for i, row in enumerate(sim_matrix):

        sorted_idx = row.argsort()[::-1]

        for j in sorted_idx:

            if j not in used_b and row[j] > threshold:

                used_b.add(j)
                matched_a.add(i)
                matched_b.add(j)

                if row[j] < 0.9:
                    results["modified"].append({
                        "old": clauses_a[i],
                        "new": clauses_b[j],
                        "score": float(row[j])
                    })

                break

    for i in range(len(clauses_a)):
        if i not in matched_a:
            results["removed"].append(clauses_a[i])

    for j in range(len(clauses_b)):
        if j not in matched_b:
            results["added"].append(clauses_b[j])

    return results


def highlight_multiple(pdf_path, output_path, diff_data):
    import fitz

    doc = fitz.open(pdf_path)

    for page in doc:

        page_text = page.get_text("text").lower()

        for clause, color in diff_data:

            if not clause or len(clause) < 20:
                continue

            clause_clean = clause.lower().strip()

            # Try partial matching (first 8–12 words)
            words = clause_clean.split()
            search_phrase = " ".join(words[:10])

            try:
                instances = page.search_for(
                    search_phrase,
                    flags=fitz.TEXT_IGNORECASE
                )
            except:
                continue

            for inst in instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=color)
                highlight.update()

    doc.save(output_path)

def debug_results(results):
    print("\n====== DIFF SUMMARY ======")
    print(f"Added: {len(results['added'])}")
    print(f"Removed: {len(results['removed'])}")
    print(f"Modified: {len(results['modified'])}")
    print("==========================\n")