import requests
from collections import defaultdict

class UCSFContentStore:
    def __init__(self):
        self.base_url = "https://solr.idl.ucsf.edu/solr/ltdl3/select"
        self.ocr_base = "https://download.industrydocuments.ucsf.edu/"
        self.document_frequencies = defaultdict(int)
        self.document_store = {}  # Single source of truth for all document data
        self.title_hash = set()  # Store normalized titles for fast duplicate checking
    
    def normalize_title(self, title: str) -> str:
        """Create a normalized version of the title for comparison"""
        if not title:
            return ""
        # Remove punctuation, convert to lowercase, and remove extra whitespace
        normalized = ''.join(c.lower() for c in title if c.isalnum() or c.isspace())
        return ' '.join(normalized.split())

    
    def cache(self, doc: Dict[str, Any]) -> bool:
        """Add document to store if it's not a duplicate. Return True if added."""
        doc_id = doc['id']
        title = doc.get('ti', '')
        
        # Skip if exact ID already exists
        if doc_id in self.document_store:
            return doc
            
        # Get normalized title
        norm_title = self._normalize_title(title)
        if not norm_title:  # If no title, just add the doc
            self.document_store[doc_id] = {
                'metadata': doc,
                'ocr_text': None
            }
            return doc
            
        # Check for duplicate title
        if norm_title in self.title_hash:
            print(f"Skipping document {doc_id} due to seen title")
            return doc
            
        # Add document and its normalized title
        self.title_hash.add(norm_title)
        self.document_store[doc_id] = {
            'metadata': doc,
            'ocr_text': None
        }
        return doc

    def is_public_doc(self, doc):
        """Check if document is public and unrestricted"""
        availability = doc.get('availability', [])
        return "public" in availability or "no restrictions" in availability

    def get_ocr_text(self, doc_id: str) -> str:
        """Gets OCR text for a document"""
        path_segment = '/'.join(list(doc_id[:4].lower()))
        url = f"{self.ocr_base}{path_segment}/{doc_id.lower()}/{doc_id.lower()}.ocr"
        try:
            response = requests.get(url, verify=False, timeout=10)
            if response.status_code == 200:
                return response.text
            return ""
        except Exception as e:
            print(f"Error getting OCR text for {doc_id}: {e}")
            return ""

    def execute_search(self, strategy, max_results: int = 50):
        """Execute a single search strategy"""
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
                return [self.cache(doc) for doc in response.json()['response']['docs'] 
                       if self.is_public_doc(doc)]
        except Exception as e:
            print(f"Error executing search: {e}")
        return []