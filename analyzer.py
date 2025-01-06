import requests
import json
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlencode
import re
from prompts import BATCH_DOC_EVAL_V1, EXAMPLE_JSON_EVAL_V1, SING_SUMMARIZE_V1 #, SING_DOC_EVAL_V1, SING_DOC_SUMMARY_V1

class Analyzer:
    def __init__(self, model, strategies, content_store):
        self.model = model
        self.strategies = strategies
        self.content_store = content_store

    def analyze_topic(self, user_query: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Main analysis pipeline"""
        print(f"\nStarting analysis for: {user_query}")
        cached_docs = self.content_store.execute_searches(self.strategies)
        self.analyze_documents_in_batches(cached_docs, user_query)
        return self.analyze_documents_in_batches(cached_docs, user_query), cached_docs
        
    def _create_document_batch(self, batch):
        """Format batch of documents for analysis"""
        return "\n---\n".join([
            "\n".join([
                f"Document ID: {doc['id']}",  # ID is inside the doc object
                f"Title: {doc['title']}",
                f"Type: {doc['type']}",
                f"Date: {doc['date']}"
                "Content:",
                f"{doc['ocr_text'][:3000]}..."
            ])
            for doc in batch
        ])

    def _create_prompt(self, batch, user_query, metadata_analysis, summarize):
        if summarize:
            doc_texts = self._create_document_batch(batch)
            prompt = SING_SUMMARIZE_V1.format(
                uq=user_query,
                dt=doc_texts
            )
        elif metadata_analysis:
            doc_texts = self._create_metadata_batch(batch)
            prompt = BATCH_DOC_EVAL_V1.format(
                uq=user_query,
                ej=EXAMPLE_JSON_EVAL_V1,
                dt=doc_texts
            )
        else:
            doc_texts = self._create_document_batch(batch)
            prompt = BATCH_DOC_EVAL_V1.format(
                uq=user_query,
                ej=EXAMPLE_JSON_EVAL_V1,
                dt=doc_texts
            )
        return prompt

    def _parse_response(self, response_text: str) -> Dict:
        """Parse model response into JSON"""
        json_match = re.search(r'\{.*\}', response_text.strip(), re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}

    def analyze_documents_in_batches(self, docs: Dict[str, Any], user_query: str, BATCH_SIZE=5):
        """Analyze document(s) in batches with fallback for problematic batches"""
        batch_results = {}
        doc_list = list(docs.values())  # Each doc still has its ID inside

        for i in range(0, len(doc_list), BATCH_SIZE):
            batch = doc_list[i:i+BATCH_SIZE]
            try:
                results = self._try_batch_analysis(self._create_prompt(batch, user_query, False, False))
                batch_results.update(results)
            except ValueError as e:
                if "reciting from copyrighted material" in str(e):
                    print(f"\n⚠️ Copyright detection in batch {i} - processing individually")
                    results = self._handle_copyright_batch(batch, user_query)
                    batch_results.update(results)
            except Exception as e:
                print(f"\nError in batch {i}: {e}. Defaulting to metadata analysis.")
                results = self._try_batch_analysis(self._create_prompt(batch, user_query, True, False))
                batch_results.update(results)
                    
        return batch_results

    def _try_batch_analysis(self, prompt) -> Dict:
        """Attempt to analyze a batch of documents"""
        response = self.model.generate_content(prompt)
        analysis = self._parse_response(response.text)
        if analysis:
            self._print_batch_scores(analysis)
        return analysis

    def _create_metadata_batch(self, batch):
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

    def _handle_copyright_batch(self, batch: List[Dict], user_query: str) -> Dict:
        """Handle batch that triggered copyright detection by processing each document individually"""
        results = {}
        for doc in batch:
            doc_id = doc['id']
            try:
                result = self._try_batch_analysis(self._create_prompt([doc], user_query, False, False))
                if result:
                    print(f"Document {doc_id}: Score {result[doc_id]['score']}/10")
                    results.update(result)
            except Exception as e:
                print(f"Error with document {doc_id}: {e}, defaulting to metadata analysis")
                result = self._try_batch_analysis(self._create_prompt([doc], user_query, True, False))
                results.update(result)
        return results

    def _print_batch_scores(self, analysis: Dict):
        """Print scores for a batch of documents"""
        print(f"\nScores for batch:")
        for doc_id, details in analysis.items():
            print(f"Document {doc_id}: Score {details['score']}/10")
    
    def summarize(self, user_query, doc):
        return self.model.generate_content(self._create_prompt([doc], user_query, False, True)).text

    def summarize_top_documents(self, user_query, cached_docs, analysis_results, n = 3):
        # Sort documents by score in descending order
        top_docs = dict(
            sorted(
                analysis_results.items(),
                key=lambda item: item[1]['score'],
                reverse=True
            )[:n]
        )

        # Summarize directly!
        for doc_id in top_docs.keys():
            summary = self.summarize(user_query, cached_docs[doc_id])
            print(f"\nDocument {doc_id}: {summary}")
