from typing import Dict, List, Any
import re
import json
import prompts_v2


class PromptManagerV2:
    def __init__(self,
                 batch_eval_template=prompts_v2.BATCH_DOC_EVAL_V2,
                 example_json=prompts_v2.EXAMPLE_JSON_EVAL_V2,
                 max_char_limit=3000):
        self.batch_eval_template = batch_eval_template
        self.example_json = example_json
        self.max_char_limit = max_char_limit

    def join_document_text(self, batch: List[Dict[str, Any]]) -> str:
        return "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",
                f"Title: {doc.get('title', '')}",
                f"Type: {doc.get('type', '')}",
                f"Date: {doc.get('date', '')}",
                "Content:",
                f"{(doc.get('ocr_text') or '')[: self.max_char_limit]}"
            ])
            for doc in batch
        ])

    def create_document_analysis_prompt(self, documents: List[Dict[str, Any]], user_query: str) -> str:
        doc_texts = self.join_document_text(documents)
        return self.batch_eval_template.format(
            uq=user_query,
            ej=self.example_json,
            dt=doc_texts
        )

    def parse_response(self, response_text: str) -> Dict[str, Any]:
        json_match = re.search(r'\{.*\}', response_text.strip(), re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception:
                return {}
        return {}

