import fitz
import ollama
import json
import os
import torch
import re
from rapidfuzz import fuzz
from concurrent.futures import ThreadPoolExecutor
from transformers import RobertaTokenizer, RobertaForSequenceClassification

from config import CLASSIFIED_DIR, MODEL_PATH

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = RobertaTokenizer.from_pretrained("roberta-base")
tokenizer.save_pretrained(MODEL_PATH)
# tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()
LLM_MODEL = "phi3:mini"

with open(f"{MODEL_PATH}/label_mapping.json", "r") as f:
    maps = json.load(f)

label2id = maps["label2id"]
id2label = {int(k): v for k, v in maps["id2label"].items()}

print("[INFO] Classifier loaded successfully")

def extract_text(pdf):

    print("\n[STEP 1] Extracting text from PDF...")

    doc = fitz.open(pdf)
    text = []

    for i, page in enumerate(doc):
        print(f"[PDF] Reading page {i+1}/{len(doc)}")
        text.append(page.get_text())

    final_text = "\n".join(text)

    print(f"[INFO] Total characters extracted: {len(final_text)}")

    return final_text

def normalize_text(text):
    text = re.sub(r"-\n", "", text)  # fix broken words
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"(?<!\.)\n(?!\n)", " ", text)
    return text





def create_chunks(text, chunk_size=8000, overlap=400):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def clean_clause_text(text):
    # Remove leading numbering ONLY if clearly present
    if not isinstance(text, str):
        text = str(text)

    text = re.sub(r"^\s*\d+(\.\d+)?\s*", "", text)

    # Remove leading headings like "Governing Law"
    text = re.sub(r"^[A-Z][A-Za-z\s]{2,40}:\s*", "", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def deduplicate_clauses(clauses, threshold=95):
    unique = []

    for c in clauses:
        matched = False

        for u in unique:
            if fuzz.token_sort_ratio(c.lower(), u.lower()) > threshold:
                matched = True
                break

        if not matched:
            unique.append(c)

    return unique

def clean_parties(parties):
    cleaned = []

    for p in parties:
        p = p.strip()
        p = re.sub(r'["“”]', '', p)

        if len(p) > 3:
            cleaned.append(p)

    return list(set(cleaned))

def merge_similar_parties(parties, threshold=90):

    merged = []

    for p in parties:

        if isinstance(p, dict):
            name = p.get("name", "")
        else:
            name = str(p)

        name = name.strip()

        if not name:
            continue

        matched = False

        for i, existing in enumerate(merged):

            score = fuzz.token_sort_ratio(name.lower(), existing.lower())

            if score >= threshold:
                matched = True
                break

        if not matched:
            merged.append(name)

    return merged

def extract_json(text):
    """
    Robust JSON extractor from messy LLM output
    """
    if not isinstance(text, str):
        text = str(text)

    # 1. Direct parse
    try:
        return json.loads(text)
    except:
        pass

    # 2. Extract largest JSON block
    matches = re.findall(r"\{[\s\S]*?\}", text)

    for match in matches:
        try:
            return json.loads(match)
        except:
            continue

    # 3. Try fixing common issues
    try:
        fixed = text.replace("\n", " ")
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        return json.loads(fixed)
    except:
        pass

    print("[WARNING] Could not parse JSON from model output.")
    return {"parties": [], "clauses": []}






def process_chunk(chunk, i):
    print(f"[EXTRACT] Processing chunk {i+1}")

    prompt = f"""
        <|system|>
        You are a professional legal data extractor. Extract information in strict JSON format.
        <|end|>
        <|user|>
        EXTRACT ALL legal clauses and parties from the text below.

        RULES:
        1. PARTIES: Extract full legal names of entities.
        2. CLAUSES: Each clause must be a single, complete legal provision. 
        3. Do NOT include headings or clause numbers.
        4. Format: {{"parties": ["name1"], "clauses": ["text1", "text2"]}}

        TEXT:
        {chunk}
        <|end|>
        <|assistant|>
        """

    try:
        max_retries = 2
        data = None

        for attempt in range(max_retries + 1):

            response = ollama.generate(
                model=LLM_MODEL,
                prompt=prompt,
                format="json",
                options={"temperature": 0, "num_ctx": 8192}
            )

            raw = response["response"]
            data = extract_json(raw)

            # Check if valid
            if data.get("clauses") or data.get("parties"):
                break

            print(f"[RETRY] Chunk {i + 1} retry {attempt + 1}")

        # fallback
        if not data:
            data = {"parties": [], "clauses": []}

        clauses = data.get("clauses") or []
        parties = data.get("parties") or []

        cleaned_clauses = []

        for c in clauses:
            if not isinstance(c, str):
                c = str(c)

            c = c.strip()

            if c:
                cleaned_clauses.append(clean_clause_text(c))

        clauses = cleaned_clauses

        return clauses, parties

    except Exception as e:
        print(f"[ERROR] Chunk {i+1} failed: {e}")
        return [], []

def extract_clauses_llm(text):
    print("\n[STEP 2] Extracting clauses using LLM (Parallelized)")

    chunks = create_chunks(text, chunk_size=8000)
    print(f"[INFO] Total chunks created: {len(chunks)}")

    clauses = []
    parties = []


    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda p: process_chunk(p[1], p[0]), enumerate(chunks)))

    for chunk_clauses, chunk_parties in results:
        clauses.extend(chunk_clauses)
        parties.extend(chunk_parties)

    parties = clean_parties(parties)
    parties = merge_similar_parties(parties)
    clauses = deduplicate_clauses(clauses)
    clauses = [c for c in clauses if isinstance(c, str) and len(c.strip()) > 15]

    print(f"\n[INFO] Total clauses collected: {len(clauses)}")
    return parties, clauses

def classify_clauses(clauses):

    print("\n[STEP 4] Classifying clauses")

    results = {}

    processed = 0

    for idx, clause in enumerate(clauses):

        print(f"[CLASSIFY] Clause {idx+1}/{len(clauses)}")

        # Convert to string safely
        if not isinstance(clause, str):
            clause = str(clause)

        clause = clause.strip()

        # Skip empty clauses
        if not clause:
            print(f"[SKIP] Empty clause at index {idx}")
            continue

        try:

            inputs = tokenizer(
                clause,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            )

            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = model(**inputs).logits

            probs = torch.softmax(logits, dim=1)

            conf, pred = torch.max(probs, dim=1)

            conf = conf.item()
            pred = pred.item()

            if conf < 0.7:
                label = "Uncertain"
            else:
                label = id2label[pred]

        except Exception as e:

            print(f"[ERROR] Failed to classify clause {idx}: {e}")
            continue

        if label not in results:
            results[label] = []

        results[label].append(clause)

        processed += 1

    print(f"[INFO] Successfully classified clauses: {processed}")
    print(f"[INFO] Total categories created: {len(results)}")

    return results

def run_pipeline(pdf_path):

    os.makedirs(CLASSIFIED_DIR, exist_ok=True)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    json_output_path = os.path.join(CLASSIFIED_DIR, f"{filename}.json")

    # CACHE
    if os.path.exists(json_output_path):
        print("[INFO] Using cached JSON")
        with open(json_output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[INFO] Running full pipeline...")

    text = extract_text(pdf_path)
    text = normalize_text(text)
    parties, clauses = extract_clauses_llm(text)
    classified = classify_clauses(clauses)

    output = {
        "parties": parties,
        "classified_clauses": classified
    }

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    return output