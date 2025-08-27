from typing import Dict, List, Any
import prompts_v2


class SummaryPromptManagerV2:
    def __init__(self, summary_template=prompts_v2.SING_SUMMARIZE_V2, max_char_limit=3000):
        self.summary_template = summary_template
        self.max_char_limit = max_char_limit

    def join_document_text(self, documents: List[Dict[str, Any]]) -> str:
        return "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",
                f"Title: {doc.get('title', '')}",
                f"Type: {doc.get('type', '')}",
                f"Date: {doc.get('date', '')}",
                "Content:",
                f"{(doc.get('ocr_text') or '')[: self.max_char_limit]}..."
            ])
            for doc in documents
        ])

    def create_summary_prompt(self, documents: List[Dict[str, Any]], user_query: str) -> str:
        return self.summary_template.format(
            uq=user_query,
            dt=self.join_document_text(documents)
        )

