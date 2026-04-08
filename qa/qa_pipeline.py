import os
import json
import ollama
from features.qa_system import QASystem


class QAPipeline:
    def __init__(self, json_path, full_text_pages):

        self.json_path = json_path
        self.doc_name = os.path.basename(json_path)

        with open(json_path, "r", encoding="utf-8") as f:
            self.json_data = json.load(f)

        self.qa_system = QASystem(
            json_data=self.json_data,
            doc_name=self.doc_name
        )

        self.qa_system.initialize(full_text_pages)

    def llm(self, prompt):
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={
                "num_predict": 400,
                "temperature": 0.1
            }
        )
        return response['message']['content']

    def format_page_info(self, page_results):
        ranges = []
        for p in page_results:
            ranges.append(f"{p['page_start']}-{p['page_end']}")

        return ", ".join(ranges)

    def answer_question(self, question):

        context, clause_results, page_results = self.qa_system.get_context(question)

        page_info = self.format_page_info(page_results)

        prompt = f"""
        You are an expert legal contract analyst.
        
        STRICT INSTRUCTIONS:
        - Answer ONLY using the provided context
        - Perform reasoning across multiple clauses if needed
        - Combine information where necessary
        - Do NOT hallucinate
        - If information is missing, clearly say so
        
        STYLE RULES:
        - Write in a clear, professional paragraph
        - Do NOT use bullet points
        - Do NOT use colons or semicolons
        - Use complete sentences
        - Ensure the answer ends properly (no truncation)
        
        
        CONTEXT:
        {context}
        
        QUESTION:
        {question}
        
        ANSWER:
        """

        answer = self.llm(prompt)

        return answer

    def debug_question(self, question):

        context, clause_results, page_results = self.qa_system.get_context(question)

        print("\n===== DEBUG INFO =====")
        print("Question:", question)

        print("\nTop Clauses:")
        for c in clause_results:
            print(f"[{c['label']}] {c['text'][:150]}...")

        print("\nTop Pages:")
        for p in page_results:
            print(f"Pages {p['page_start']}-{p['page_end']}")

        print("\nContext Used:\n", context[:2000])
        print("======================\n")

        answer = self.answer_question(question)
        print("Answer:\n", answer)