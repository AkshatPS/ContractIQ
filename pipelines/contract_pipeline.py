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
tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()
LLM_MODEL = "llama3"

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
        print(f"[PDF] Reading page {i + 1}/{len(doc)}")
        text.append(page.get_text())

    final_text = "\n".join(text)

    print(f"[INFO] Total characters extracted: {len(final_text)}")

    return final_text


def normalize_text(text):
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n\s*\(([a-z])\)", r"\n(\1)", text)
    text = re.sub(r"(?<![.;:])\n(?!\n)", " ", text)
    text = re.sub(r"\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def create_chunks(text, chunk_size=6000):
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def clean_clause_text(text):
    if not isinstance(text, str):
        text = str(text)

    text = re.sub(r"^\s*\d+(\.\d+)?\s*", "", text)

    text = re.sub(r'^[A-Z][A-Za-z\s,/]{2,40}[\.:]\s*', '', text)

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

        if isinstance(p, dict):
            p = p.get("name", "")

        if not isinstance(p, str):
            p = str(p)

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
    if not isinstance(text, str):
        text = str(text)

    try:
        return json.loads(text)
    except:
        pass

    stack = []
    start = None

    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except:
                        pass

    try:
        fixed = text

        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)

        fixed = re.sub(r"(\w+):", r'"\1":', fixed)

        return json.loads(fixed)
    except:
        pass

    print("[WARNING] Could not parse JSON")
    return {"parties": [], "clauses": []}


def process_chunk(chunk, i):
    print(f"[EXTRACT] Processing chunk {i + 1}")

    prompt = f"""### System:
    You are a precise legal data extraction engine. Your task is to identify and extract the signing parties and every individual legal clause from the provided contract text.
    
    ### Extraction Rules:
    1. **NO HEADINGS:** Start the clause text immediately with the legal obligation. Delete "WHEREAS", "Section X", or "Heading Title."
    2. **VERBATIM:** Do not change a single word or character of the body text.
    3. **JSON ONLY:** Return only valid JSON.
    4. Clause Definition (STRICT):
        A clause is a COMPLETE paragraph or section.
        
        - If a paragraph contains multiple bullet points (a), (b), (c),
          KEEP THEM TOGETHER as ONE clause.
        
        - NEVER split a paragraph into multiple clauses.
        
        - Only split when there is a CLEAR paragraph break or section number change.
        
        Each clause must correspond to a visually separable block in the contract.
    6. **No Merging:** Do not combine continuous short sentences if they represent different obligations.
    7. **No Headings:** Start the clause text immediately with the legal content. Remove "Section 1.1" or "TERMINATION:". [cite: 97, 98]
    
    ### Constraints:
    1. **Verbatim Extraction:** You must extract the clause text exactly as it appears. Do not summarize, do not paraphrase, and do not truncate the text.
    2. **No Metadata:** Do not include clause headings (e.g., "Indemnification"), serial numbers (e.g., "Section 4.2"), or bullet point symbols. Extract only the body text of the clause.
    3. **Format:** Your output must be a single, valid JSON object. No conversational filler, no markdown code blocks, and no introductory text.
    
    ### Schema:
    {{
      "parties": ["Full legal name of Party 1", "Full legal name of Party 2"],
      "clauses": ["Full text of clause 1", "Full text of clause 2"]
    }}
    
    Use formatting cues:
    - Newlines
    - Numbering (1., 1.1, (a), (i))
    - Bullet points
    - Paragraph spacing
    
    These define clause boundaries.
    
    IMPORTANT:
    - If text begins with a lead sentence followed by (a), (b), (c),
      treat the ENTIRE block as ONE clause.
      
    - Do NOT extract individual bullet points separately.
    
    - Preserve logical grouping exactly as in original paragraph.
    
    ### User:
    Extract the parties and clauses from the following contract text:
    
    {chunk}"""

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

            if isinstance(data, dict) and "clauses" in data and "parties" in data:
                if isinstance(data["clauses"], list) and isinstance(data["parties"], list):
                    break

            print(f"[RETRY] Chunk {i + 1} retry {attempt + 1}")

        if not data:
            data = {"parties": [], "clauses": []}

        clauses = data.get("clauses") or []
        parties = data.get("parties") or []

        normalized_parties = []
        for p in parties:
            if isinstance(p, dict):
                p = p.get("name", "")
            if isinstance(p, str):
                normalized_parties.append(p)

        parties = normalized_parties

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
        print(f"[ERROR] Chunk {i + 1} failed: {e}")
        return [], []


def extract_clauses_llm(text):
    print("\n[STEP 2] Extracting clauses using LLM (Parallelized)")

    chunks = create_chunks(text, chunk_size=6000)
    print(f"[INFO] Total chunks created: {len(chunks)}")

    clauses = []
    parties = []

    with ThreadPoolExecutor(max_workers=1) as executor:
        results = list(executor.map(lambda p: process_chunk(p[1], p[0]), enumerate(chunks)))

    for chunk_clauses, chunk_parties in results:
        clauses.extend(chunk_clauses)
        parties.extend(chunk_parties)

    parties = clean_parties(parties)
    parties = merge_similar_parties(parties)
    clauses = deduplicate_clauses(clauses)
    clauses = [c for c in clauses if isinstance(c, str) and len(c.split()) >= 8]

    print(f"\n[INFO] Total clauses collected: {len(clauses)}")
    return parties, clauses


def classify_clauses(clauses):
    print("\n[STEP 4] Classifying clauses")

    results = {}

    processed = 0

    for idx, clause in enumerate(clauses):

        print(f"[CLASSIFY] Clause {idx + 1}/{len(clauses)}")

        if not isinstance(clause, str):
            clause = str(clause)

        clause = clause.strip()

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