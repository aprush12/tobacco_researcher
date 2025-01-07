import requests
from collections import defaultdict

class UCSFContentStore:
    def __init__(self):
        self.base_url = "https://solr.idl.ucsf.edu/solr/ltdl3/select"
        self.ocr_base = "https://download.industrydocuments.ucsf.edu/"
        self.document_frequencies = defaultdict(int)
        self.document_store = {}  # Single source of truth for all document data
        self.title_hash = defaultdict(lambda: defaultdict(int))
        self.max_chars = 99300

    def _normalize_title(self, title: str) -> str:
        """Create a normalized version of the title for comparison"""
        # Remove punctuation, convert to lowercase, and remove extra whitespace
        normalized = ''.join(c.lower() for c in title if c.isalnum() or c.isspace())
        return ' '.join(normalized.split())

    def _count_document(self, doc_id, title):
        """Track document appearances, allowing content with same titles but different doc IDs"""
        self.title_hash[title][doc_id] += 1

    def _cache(self, doc, doc_id, title, search_strategy):
        """Add document to store if entirely new"""
        if title not in self.title_hash and doc_id not in self.document_store:
            self.document_store[doc_id] = {
                    'search_strategy': search_strategy,
                    'id': doc_id,
                    'title': title,
                    'type': doc.get('dt', 'No type'),
                    'bates': doc.get('bn', 'No bates number'),
                    'date': {doc.get('dd', 'No date')},
                    'ocr_text': None
            }
        return

    def process_docs(self, docs, search_strategy):
        """Caches documents and updates frequencies of seen documents for results of a search strategy"""
        for doc in docs:
            if (self.is_public_doc(doc)):
                doc_id = doc['id']
                title = self._normalize_title(doc.get('ti', ''))
                self._cache(doc, doc_id, title, search_strategy)
                self._count_document(doc_id, title)
        self._update_missing_ocr()
    
    def _update_missing_ocr(self):
        [self.document_store[doc_id].__setitem__('ocr_text', self.get_ocr_text(doc_id, self.max_chars)) 
        for doc_id, data in self.document_store.items() 
        if data['ocr_text'] is None]

    def is_public_doc(self, doc):
        """Check if document is public and unrestricted"""
        availability = doc.get('availability', [])
        return "public" in availability or "no restrictions" in availability

    def get_ocr_text(self, doc_id: str, max_chars) -> str:
        """Gets OCR text for a document"""
        path_segment = '/'.join(list(doc_id[:4].lower()))
        url = f"{self.ocr_base}{path_segment}/{doc_id.lower()}/{doc_id.lower()}.ocr"
        try:
            response = requests.get(url, verify=False, timeout=10)
            if response.status_code == 200:
                return response.text[:max_chars]
            return ""
        except Exception as e:
            print(f"Error getting OCR text for {doc_id}: {e}")
            return ""

    def execute_searches(self, strategies, max_results: int = 2):
        """Execute search strategies and return new documents"""
        for strategy in strategies:
            print(f"\nExecuting strategy: {strategy.get('search_terms')}")
            
            params = {
                'q': strategy['search_terms'],
                'fq': ['availability:public'],
                'wt': 'json',
                'rows': str(max_results),
                'sort': 'score desc',
                'fl': 'id,au,ti,bn,dd,dt,availability,pg,attach,access,artifact'
            }
            
            # Add strategy filters
            for field, value in strategy.get('filters', {}).items():
                params['fq'].append(f'{field}:{value}')

            try:
                response = requests.get(self.base_url, params=params, verify=False)
                if response.status_code == 200:
                    docs = response.json()['response']['docs']
                    self.process_docs(docs, strategy)
            except Exception as e:
                print(f"Error executing search: {e}")
        
        return self.document_store