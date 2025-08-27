import requests
import json
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlencode
import re

class Analyzer:
    def __init__(self, model, strategies, content_store, prompt_manager):
        self.model = model
        self.strategies = strategies
        self.content_store = content_store
        self.prompt_manager = prompt_manager

    def analyze_topic(self, user_query, num_results_per_search, additional_fqs=None) -> Dict[str, Any]:
        """Main analysis pipeline"""
        print(f"\nStarting analysis for: {user_query}")
        cached_docs = self.content_store.execute_searches(self.strategies, num_results_per_search, additional_fqs)
        results = self.analyze_documents_in_batches(cached_docs, user_query)
        return results, cached_docs

    def analyze_documents_in_batches(self, docs: Dict[str, Any], user_query: str, BATCH_SIZE=5):
        """Analyze document(s) in batches with fallback for problematic batches"""
        batch_results = {}
        doc_list = list(docs.values())  # Each doc still has its ID inside

        for i in range(0, len(doc_list), BATCH_SIZE):
            batch = doc_list[i:i+BATCH_SIZE]
            try:
                results = self._try_batch_analysis(self.prompt_manager.create_document_analysis_prompt(batch, user_query))
                batch_results.update(results)
            except ValueError as e:
                if "reciting from copyrighted material" in str(e):
                    print(f"\n⚠️ Copyright detection in batch {i} - processing individually")
                else:  
                    print(f"\nError in batch {i}: {e}. Defaulting to individual document analysis.")
                results = self._process_individually(batch, user_query)
                batch_results.update(results)
    
        return batch_results
    
    def _process_individually(self, batch: List[Dict], user_query: str) -> Dict:
        """Process each document individually"""
        results = {}
        for doc in batch:
            doc_id = doc['id']
            try:
                result = self._try_batch_analysis(self.prompt_manager.create_document_analysis_prompt([doc], user_query))
                if result:
                    print(f"Document {doc_id}: Score {result[doc_id]['score']}/10")
                    results.update(result)
            except Exception as e:
                print(f"Error with document {doc_id}: {e}, defaulting to metadata analysis")
                result = self._try_batch_analysis(self.prompt_manager.create_metadata_analysis_prompt([doc], user_query))
                results.update(result)
        return results

    def _try_batch_analysis(self, prompt) -> Dict:
        """Attempt to analyze a batch of documents"""
        response = self.model.generate_content(prompt)
        analysis = self.prompt_manager.parse_response(response.text)
        if analysis:
            self._print_batch_scores(analysis)
        return analysis

    def _print_batch_scores(self, analysis: Dict):
        """Print scores for a batch of documents"""
        print(f"\nScores for batch:")
        for doc_id, details in analysis.items():
            print(f"Document {doc_id}: Score {details['score']}/10")

