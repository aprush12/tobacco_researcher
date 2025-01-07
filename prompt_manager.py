from typing import Dict, List, Any
import re
import json
import prompts

# max char limit not used right now
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
        """Create prompt for document summarization"""
        doc_texts = self.join_document_text(documents)
        return self.summary_template.format(
            uq=user_query,
            dt=doc_texts
        )
    
    def join_metadata(self, batch):
        """Passes in all metadata without OCR data"""
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
        """Format batch of documents for analysis"""
        return "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",  # ID is inside the doc object
                f"Title: {doc['title']}",
                f"Type: {doc['type']}",
                f"Date: {doc['date']}"
                "Content:",
                f"{doc['ocr_text']}..."
            ])
            for doc in batch
        ])

    def create_metadata_analysis_prompt(self, batch, user_query):
        """Create prompt for metadata analysis"""
        doc_texts = self.join_metadata(batch)
        return self.batch_eval_template.format(
            uq=user_query,
            ej=self.example_json,
            dt=doc_texts
        )
    
    def create_document_analysis_prompt(self, documents, user_query):
        """Create prompt for document content analysis"""
        doc_texts = self.join_document_text(documents)
        return self.batch_eval_template.format(
            uq=user_query,
            ej=self.example_json,
            dt=doc_texts
        )
    
    def parse_response(self, response_text: str) -> Dict:
        """Parse model response into JSON"""
        json_match = re.search(r'\{.*\}', response_text.strip(), re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}

