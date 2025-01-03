import requests
import json
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlencode
import time
from difflib import SequenceMatcher
import tempfile
import os
import re

class Analyzer:
    def __init__(self, strategies, content_store, DOC_SUMMARY_PROMPT, BATCH_DOC_SUMMARY_PROMPT):
        self.strategies = strategies
        self.content_store = content_store
    
    def analyze_topic(self, user_query: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Main analysis pipeline"""
        print(f"\nStarting analysis for: {user_query}")
        for strategy in self.strategies:
            search_results = self.get_strategy_results(strategy)
            # Process only new documents in batches
            if search_results:
                for i in range(0, len(search_results), 5):
                    batch = search_results[i:i+5]
                    self._process_document_batch(batch, user_query)

    
    def get_strategy_results(self, strategy):
        print(f"\nExecuting strategy: {strategy.get('search_terms')}")
        docs = self.content_store.execute_search(strategy)
        self.document_frequencies.update({doc['id']: self.document_frequencies[doc['id']] + 1 for doc in docs})
        return docs
            
    def _process_document_batch(self, docs: List[Dict[str, Any]], query_context: str):
        """Process a batch of new documents"""
        # Get OCR text for batch
        for doc in docs:
            doc_id = doc['id']
            if not self.document_store[doc_id]['ocr_text']:
                self.document_store[doc_id]['ocr_text'] = self.content_store.get_ocr_text(doc_id)
        
        # Analyze batch
        analysis = self.analyze_document_batch(docs, query_context)
        
        # Store analysis results
        for doc_id, doc_analysis in analysis.items():
            if doc_id in self.document_store:
                self.document_store[doc_id]['analysis'] = doc_analysis

    def analyze_document_batch(self, docs: List[Dict[str, Any]], query_context: str) -> Dict[str, Any]:
        """Analyze documents in batches with fallback to individual processing for problematic batches"""
        if not docs:
            return {}
        
        BATCH_SIZE = 5
        batch_results = {}
        
        # Define the JSON example template separately
        EXAMPLE_JSON = (
            '{\n'
            '    "doc_id1": {\n'
            '        "score": 7,\n'
            '        "entities": {\n'
            '            "people": ["name1", "name2"],\n'
            '            "projects": ["project1"],\n'
            '            "products": ["product1"],\n'
            '            "terms": ["term1"],\n'
            '            "dates": ["date1"]\n'
            '        }\n'
            '    }\n'
            '}'
        )
        
        # First try batch processing
        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i:i+BATCH_SIZE]
            doc_texts = []
            batch_ids = []
            
            for doc in batch:
                doc_id = doc['id']
                title = doc.get('ti', 'No title')
                batch_ids.append(doc_id)
                doc_texts.append(
                    f"Document ID: {doc_id}\n"
                    f"Title: {title}\n"
                    f"Content:\n{self.document_store[doc_id]['ocr_text'][:3000]}..."
                )

            prompt = (
                f"Research context: {query_context}\n\n"
                "Analyze these tobacco industry documents. For each document, provide:\n"
                "1. A relevance score (0-10)\n"
                "2. Key entities found (people, projects, products, terms, dates)\n\n"
                f"Return only a JSON object like this example:\n{EXAMPLE_JSON}\n\n"
                "Documents to analyze:\n\n"
                f"{chr(10) + '---' + chr(10)}".join(doc_texts)
            )
            
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Try to find JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    print(f"\nScores for batch:")
                    for doc_id, details in analysis.items():
                        print(f"Document {doc_id}: Score {details['score']}/10")
                    batch_results.update(analysis)
                    continue  # Move to next batch if successful
                
            except ValueError as e:
                if "reciting from copyrighted material" in str(e):
                    print(f"\n⚠️ Copyright detection in batch {i//BATCH_SIZE + 1} - processing documents individually")
                    # Process problematic batch one by one
                    for doc in batch:
                        doc_id = doc['id']
                        try:
                            individual_result = self._analyze_single_document(doc, query_context)
                            batch_results.update(individual_result)
                        except Exception as doc_error:
                            print(f"Error with document {doc_id}: {doc_error}")
                            batch_results.update(self._create_basic_analysis([doc]))
                
            except Exception as e:
                print(f"\nError in batch {i//BATCH_SIZE + 1}: {e}")
                # Fallback to basic analysis for the entire batch
                batch_results.update(self._create_basic_analysis(batch))
            
            time.sleep(0.5)  # Rate limiting between batches
        
        return batch_results

    def _analyze_single_document(self, doc: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """Analyze a single document when batch processing fails"""
        doc_id = doc['id']
        title = doc.get('ti', 'No title')
        ocr_text = self.document_store[doc_id]['ocr_text'][:3000] if self.document_store[doc_id]['ocr_text'] else ''
        
        prompt = f"""
        Research context: {query_context}

        Analyze this tobacco industry document. Instead of directly quoting, summarize:
        1. A relevance score (0-10)
        2. Key entities found (people, projects, products, terms, dates)

        Return only a JSON object with NO direct quotes:
        {{
            "{doc_id}": {{
                "score": 7,
                "entities": {{
                    "people": ["name1", "name2"],
                    "projects": ["project1"],
                    "products": ["product1"],
                    "terms": ["term1"],
                    "dates": ["date1"]
                }}
            }}
        }}

        Document to analyze:
        Document ID: {doc_id}
        Title: {title}
        Content summary: {ocr_text}
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                print(f"Document {doc_id}: Score {analysis[doc_id]['score']}/10")
                return analysis
                
        except ValueError as e:
            if "reciting from copyrighted material" in str(e):
                print(f"⚠️ Copyright detection for {doc_id} - using metadata only")
                return self._create_basic_analysis([doc])
        except Exception as e:
            print(f"Error analyzing {doc_id}: {e}")
        
        return self._create_basic_analysis([doc])