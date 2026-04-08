import ollama
import re
from concurrent.futures import ThreadPoolExecutor
import os
from pipelines.contract_pipeline import run_pipeline
from config import REPORTS_DIR
from utils.file_handler import get_filename
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter


LLM_MODEL = "llama3"

LABEL_DISPLAY_MAP = {
    "dates_term": "Dates & Term",
    "intellectual_property": "Intellectual Property",
    "legal_jurisdiction": "Legal & Jurisdiction",
    "liability_legal": "Liability & Legal",
    "license": "License",
    "parties_definitions": "Parties & Definitions",
    "payment_commercial": "Payment & Commercial Terms",
    "restrictions": "Restrictions",
    "rights_control": "Rights & Control",
    "termination": "Termination"
}

def create_chunks(text, chunk_size=6000, overlap=300):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def clean_summary(summary):

    summary = summary.strip()

    if ":" in summary:
        summary = summary.split(":", 1)[1]

    summary = re.sub(
        r"^(here\s*(is|'s)?\s*(a|the)?\s*summary\s*(of)?[:\-]?\s*)",
        "",
        summary,
        flags=re.IGNORECASE
    )

    summary = re.sub(
        r"^(this\s*(is|'s)?\s*(a|the)?\s*summary\s*(of)?[:\-]?\s*)",
        "",
        summary,
        flags=re.IGNORECASE
    )

    summary = re.sub(r"^of\s+", "", summary, flags=re.IGNORECASE)

    summary = summary.replace("*", "")
    summary = re.sub(r"\s+", " ", summary)

    return summary.strip()

def process_summary_chunk(chunk, i, parties_text):
    print(f"[LLM] Generating partial summary {i+1}")

    prompt = f"""
    You are a professional legal analyst.

    Task:
    Write a clear executive summary of the contract in a SINGLE natural paragraph.

    STRICT RULES:
    - Write in plain English paragraph form
    - Do NOT use colons (:)
    - Do NOT use semicolons (;)
    - Do NOT use bullet points or lists
    - Use complete sentences only
    - Ensure the paragraph flows naturally

    Content requirements:
    - Include obligations of each party
    - Include rights of each party
    - Include key conditions
    - Include termination terms

    IMPORTANT:
    - Every sentence must be COMPLETE
    - Do NOT end mid-sentence
    - Do NOT truncate
    - Ensure the final sentence is fully finished

    Contract Parties:
    {parties_text}

    Clauses:
    {chunk}
    """

    try:
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt,
            options={"num_predict": 400}
        )

        return response["response"].strip()

    except Exception as e:
        print(f"[ERROR] Summary chunk {i+1} failed: {e}")
        return ""

def hierarchical_summarize(summaries, parties_text, batch_size=5):

    summaries = [s for s in summaries if s and s.strip()]
    prev_len = len(summaries)

    while len(summaries) > 1:

        print(f"[INFO] Hierarchical summarization round: {len(summaries)} summaries")

        new_summaries = []

        for i in range(0, len(summaries), batch_size):

            batch = summaries[i:i+batch_size]
            combined = "\n".join(batch)

            prompt = f"""
            You are a professional legal analyst.

            Task:
            Combine multiple partial contract summaries into ONE final executive summary.

            STRICT RULES:
            - Write in a SINGLE natural paragraph
            - Use plain English
            - Do NOT use colons (:)
            - Do NOT use semicolons (;)
            - Do NOT use bullet points or lists
            - Do NOT repeat information
            - Do NOT add new information
            - Preserve full legal meaning

            SENTENCE QUALITY:
            - Every sentence must be COMPLETE
            - The paragraph must end with a COMPLETE sentence
            - Do NOT truncate
            - Ensure smooth logical flow between ideas

            CONTENT TO COVER:
            - obligations of each party
            - rights of each party
            - key conditions
            - termination or legal implications

            CONTEXT:
            The contract involves the following parties:
            {parties_text}

            PARTIAL SUMMARIES:
            {combined}
            """

            try:
                response = ollama.generate(
                    model=LLM_MODEL,
                    prompt=prompt,
                    options={"num_predict": 400}
                )

                new_summaries.append(response["response"].strip())

            except Exception as e:
                print(f"[ERROR] Hierarchical summary failed: {e}")
                new_summaries.append(combined[:500])

        if len(new_summaries) >= prev_len:
            print("[WARNING] No reduction in summaries, stopping hierarchical merge")
            break

        summaries = new_summaries
        prev_len = len(summaries)

    return summaries[0] if summaries else ""

def generate_summary(classified, parties):
    print("\n[STEP 5] Generating optimized contract summary")

    summary_input = ""
    for label, clauses in classified.items():
        if label == "Uncertain": continue

        display_label = LABEL_DISPLAY_MAP.get(label, label.title())
        representative_sample = "\n".join(clauses[:20])
        summary_input += f"--- {display_label} ---\n{representative_sample}\n\n"

    chunks = create_chunks(summary_input, chunk_size=6000)
    print(f"[INFO] Summary chunks reduced to: {len(chunks)}")

    parties_text = ", ".join(parties)
    partial_summaries = []

    with ThreadPoolExecutor(max_workers=1) as executor:
        partial_summaries = list(executor.map(
            lambda x: process_summary_chunk(x[1], x[0], parties_text),
            enumerate(chunks)
        ))

    summary = hierarchical_summarize(partial_summaries, parties_text)

    summary = re.sub(r"^(here\s*(is|'s)?\s*(a|the)?\s*summary[:\-]?\s*)", "", summary, flags=re.IGNORECASE)
    return clean_summary(summary)

def create_pdf(summary, parties, classified, pdf_output_path):

    print("\n[STEP 7] Generating PDF report")

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("Contract Analysis Report", styles['Title']))
    story.append(Spacer(1,20))

    story.append(Paragraph("Executive Summary", styles['Heading2']))
    story.append(Paragraph(summary, styles['BodyText']))
    story.append(Spacer(1,20))

    story.append(Paragraph("Parties", styles['Heading2']))

    party_list = ListFlowable(
        [Paragraph(p, styles['BodyText']) for p in parties]
    )

    story.append(party_list)
    story.append(Spacer(1,20))

    story.append(Paragraph("Contract Clauses", styles['Heading2']))
    story.append(Spacer(1,10))

    for label, clauses in classified.items():

        if label == "Uncertain":
            continue

        filtered_clauses = []

        for clause in clauses:

            clean_clause = clause

            if len(clean_clause.split()) >= 15:
                filtered_clauses.append(clean_clause)

        if not filtered_clauses:
            continue

        display_label = LABEL_DISPLAY_MAP.get(label, label.replace("_", " ").title())
        story.append(Paragraph(f"<b>{display_label}</b>", styles['Heading3']))
        story.append(Spacer(1, 5))

        for clause in filtered_clauses:
            story.append(Paragraph(clause, styles['BodyText']))
            story.append(Spacer(1, 8))

    doc = SimpleDocTemplate(pdf_output_path, pagesize=letter)
    doc.build(story)

    print(f"[SUCCESS] PDF generated: {pdf_output_path}")

def run_contract_brief(pdf_path):

    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = get_filename(pdf_path)

    pdf_path_out = os.path.join(REPORTS_DIR, f"{filename}_report.pdf")

    data = run_pipeline(pdf_path)

    classified = data["classified_clauses"]
    parties = data["parties"]

    summary = generate_summary(classified, parties)

    create_pdf(summary, parties, classified, pdf_path_out)

    print(f"[SUCCESS] Outputs saved")

    return pdf_path_out

