from typing import Dict, List, Any
import re
import json
from legacy_v1 import prompts_v1 as prompts


class PromptManager:
    def __init__(self,
                 summary_template=prompts.SING_SUMMARIZE_V2,
                 batch_eval_template=prompts.BATCH_DOC_EVAL_V1,
                 example_json=prompts.EXAMPLE_JSON_EVAL_V1,
                 max_char_limit=3000):
        self.summary_template = summary_template
        self.batch_eval_template = batch_eval_template
        self.example_json = example_json
        self.max_char_limit = max_char_limit

    def create_summary_prompt(self, documents, user_query):
        doc_texts = self.join_document_text(documents)
        return self.summary_template.format(
            uq=user_query,
            dt=doc_texts
        )

    def join_metadata(self, batch):
        doc_text = "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",
                f"Title: {doc['title']}",
                f"Date: {doc['date']}",
                f"Type: {doc['type']}"
            ])
            for doc in batch
        ])
        return doc_text

    def join_document_text(self, batch):
        return "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",
                f"Title: {doc['title']}",
                f"Type: {doc['type']}",
                f"Date: {doc['date']}",
                "Content:",
                f"{doc['ocr_text']}..."
            ])
            for doc in batch
        ])

    def create_metadata_analysis_prompt(self, batch, user_query):
        doc_texts = self.join_metadata(batch)
        return self.batch_eval_template.format(
            uq=user_query,
            ej=self.example_json,
            dt=doc_texts
        )

    def create_document_analysis_prompt(self, documents, user_query):
        doc_texts = self.join_document_text(documents)
        return self.batch_eval_template.format(
            uq=user_query,
            ej=self.example_json,
            dt=doc_texts
        )

    def parse_response(self, response_text: str) -> Dict:
        json_match = re.search(r'\{.*\}', response_text.strip(), re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}

