import fitz  # PyMuPDF
import difflib
import re
import os


class ContractDiffEngine:
    def __init__(self, output_dir="data/outputs/differences"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.similarity_threshold = 0.7

    def semantic_cleanup(self, text):
        legal_num_regex = re.compile(
            r'^\s*(\d+(\.\d+)*[.\)]|[a-zA-Z]+(\.\d+)*[.\)]|\(?[a-zA-Z]+\)?|\(?\d+\)?|ARTICLE\s+[IVXLCDM\d]+|SECTION\s+\d+)\s*',
            re.IGNORECASE
        )
        text_no_num = re.sub(legal_num_regex, '', text, count=1)
        return re.sub(r'\W+', '', text_no_num).lower()

    def get_content(self, pdf_path):
        doc = fitz.open(pdf_path)
        content = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            for b in blocks:
                text = b[4].strip().replace('\n', ' ')
                if text:
                    content.append({
                        "text": text,
                        "rect": fitz.Rect(b[:4]),
                        "page": page_num,
                        "semantic": self.semantic_cleanup(text)
                    })
        return doc, content

    def compare(self, file1, file2):

        doc1, blocks1 = self.get_content(file1)
        doc2, blocks2 = self.get_content(file2)

        sem1 = [b["semantic"] for b in blocks1]
        sem2 = [b["semantic"] for b in blocks2]
        full_pool1, full_pool2 = "".join(sem1), "".join(sem2)

        sm = difflib.SequenceMatcher(None, sem1, sem2)
        opcodes = sm.get_opcodes()

        final_added, final_removed, final_modified = [], [], []
        stats_pages = {"pages1": set(), "pages2": set()}

        delta_blocks1, delta_blocks2 = [], []

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                continue
            if tag in ('replace', 'delete'):
                delta_blocks1.extend(blocks1[i1:i2])
            if tag in ('replace', 'insert'):
                delta_blocks2.extend(blocks2[j1:j2])

        used_new_indices = set()
        for b1 in delta_blocks1:
            best_match_idx, best_ratio = -1, 0

            for idx, b2 in enumerate(delta_blocks2):
                if idx in used_new_indices: continue

                ratio = difflib.SequenceMatcher(None, b1["semantic"], b2["semantic"]).ratio()
                if ratio > best_ratio:
                    best_ratio, best_match_idx = ratio, idx

            if best_match_idx != -1 and best_ratio > self.similarity_threshold:
                final_modified.append((b1, delta_blocks2[best_match_idx]))
                used_new_indices.add(best_match_idx)
            else:
                if b1["semantic"] not in full_pool2:
                    final_removed.append(b1)

        for idx, b2 in enumerate(delta_blocks2):
            if idx not in used_new_indices:
                if b2["semantic"] not in full_pool1:
                    final_added.append(b2)

        COLORS = {"red": (1, 0, 0), "green": (0, 0.8, 0), "blue": (0, 0, 1)}

        for b in final_removed:
            self.draw_box(doc1, b, COLORS["red"])
            stats_pages["pages1"].add(b["page"] + 1)

        for b in final_added:
            self.draw_box(doc2, b, COLORS["green"])
            stats_pages["pages2"].add(b["page"] + 1)

        for b1, b2 in final_modified:
            self.draw_box(doc1, b1, COLORS["blue"])
            self.draw_box(doc2, b2, COLORS["blue"])
            stats_pages["pages1"].add(b1["page"] + 1)
            stats_pages["pages2"].add(b2["page"] + 1)

        summary = {
            "added": len(final_added),
            "removed": len(final_removed),
            "modified": len(final_modified),
            "pages1": stats_pages["pages1"],
            "pages2": stats_pages["pages2"]
        }

        base_name = os.path.splitext(os.path.basename(file1))[0]
        out_rem = os.path.join(self.output_dir, f"{base_name}_REMOVED.pdf")
        out_add = os.path.join(self.output_dir, f"{base_name}_ADDED.pdf")

        doc1.save(out_rem);
        doc2.save(out_add)
        return summary, out_rem, out_add

    def draw_box(self, doc, block, color):
        page = doc[block["page"]]
        page.draw_rect(block["rect"], color=color, width=1.5)