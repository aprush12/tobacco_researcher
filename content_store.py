import os
import requests
from collections import defaultdict

# Solr server enforces 100 docs per request; use paging via `start`.
SERVER_PAGE_SIZE = 100

class UCSFContentStore:
    def __init__(self):
        # Allow overriding endpoints via environment for compatibility with IDL updates
        self.base_url = os.getenv(
            "SOLR_BASE_URL",
            # Default to the public metadata endpoint per updated IDL docs
            "https://metadata.idl.ucsf.edu/solr/ltdl3/query",
        )
        self.ocr_base = os.getenv(
            "OCR_BASE",
            # Keep existing default OCR host unless overridden
            "https://download.industrydocuments.ucsf.edu/",
        )
        self.document_frequencies = defaultdict(int)
        self.document_store = {}  # Single source of truth for all document data
        self.title_hash = defaultdict(lambda: defaultdict(int))
        self.max_chars = 99300
        # Optional: enable cursorMark paging via env var
        self.use_cursor_mark = (os.getenv("USE_CURSOR_MARK", "false").strip().lower() in {"1", "true", "yes", "y"})
        # Optional: skip OCR fetch (tests / faster runs)
        self.skip_ocr = (os.getenv("SKIP_OCR", "false").strip().lower() in {"1", "true", "yes", "y"})

    def _normalize_title(self, title: str) -> str:
        """Create a normalized version of the title for comparison"""
        # Remove punctuation, convert to lowercase, and remove extra whitespace
        normalized = ''.join(c.lower() for c in (title or '') if c.isalnum() or c.isspace())
        tokens = normalized.split()
        # Merge consecutive single-letter tokens (e.g., "r j" -> "rj") to collapse spacing differences like
        # "R. J. Reynolds" vs "R.J. Reynolds" -> "rj reynolds"
        merged: list[str] = []
        buf = []
        for tok in tokens:
            if len(tok) == 1:
                buf.append(tok)
            else:
                if buf:
                    merged.append(''.join(buf))
                    buf = []
                merged.append(tok)
        if buf:
            merged.append(''.join(buf))
        return ' '.join(merged)

    def _count_document(self, doc_id, title):
        """Track document appearances, allowing content with same titles but different doc IDs"""
        self.title_hash[title][doc_id] += 1

    def _cache(self, doc, doc_id, title, search_strategy):
        """Add document to store. Deduplicate by normalized title when available."""
        # If we've already cached this specific doc, nothing to do
        if doc_id in self.document_store:
            return

        # If we have a non-empty normalized title and have seen this title before,
        # skip caching to avoid duplicates across different doc IDs with the same title.
        if isinstance(title, str) and title.strip():
            if title in self.title_hash and len(self.title_hash[title]) > 0:
                return

        safe_title = title if title else '(untitled)'
        # Field compatibility: prefer new names, fallback to legacy short names
        get = lambda *keys: next((doc.get(k) for k in keys if k in doc), None)
        doc_type = get('type', 'dt') or 'No type'
        bates = get('bates', 'bn') or 'No bates number'
        # Prefer ISO date; fallback to legacy 'dd'
        date_val = get('documentdateiso', 'dd') or 'No date'
        self.document_store[doc_id] = {
            'search_strategy': search_strategy,
            'id': doc_id,
            'title': safe_title,
            'type': doc_type,
            'bates': bates,
            'date': {date_val},
            'ocr_text': None
        }
        return

    def process_docs(self, docs, search_strategy):
        """Caches documents and updates frequencies of seen documents for results of a search strategy"""
        for doc in docs:
            doc_id = doc['id']
            # Prefer full field names if present, fallback to short legacy names
            raw_title = doc.get('title') or doc.get('ti', '')
            title = self._normalize_title(raw_title)
            self._cache(doc, doc_id, title, search_strategy)
            self._count_document(doc_id, title)
        self._update_missing_ocr()
    
    def _update_missing_ocr(self):
        if self.skip_ocr:
            [self.document_store[doc_id].__setitem__('ocr_text', '')
             for doc_id, data in self.document_store.items()
             if data['ocr_text'] is None]
        else:
            [self.document_store[doc_id].__setitem__('ocr_text', self.get_ocr_text(doc_id, self.max_chars)) 
             for doc_id, data in self.document_store.items() 
             if data['ocr_text'] is None]

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

    def execute_searches(self, strategies, max_results: int = 2, additional_fqs=None, use_cursor: bool | None = None):
        """Execute search strategies and return new documents.
        The upstream Solr endpoint returns up to 100 records per request regardless of `rows`.
        We page in SERVER_PAGE_SIZE chunks using `start`, then trim to `max_results` per strategy.
        """
        if use_cursor is None:
            use_cursor = self.use_cursor_mark
        for strategy in strategies:
            print(f"\nExecuting strategy: {strategy.get('search_terms')}")

            # Base params (rows fixed to server page size; we'll trim client-side)
            base_params = {
                'q': strategy['search_terms'],
                'fq': ['availability:public'],
                'wt': 'json',
                'rows': str(SERVER_PAGE_SIZE),
                # For cursorMark, add a unique tiebreaker. Many Solr setups allow 'score desc, id asc'.
                'sort': 'score desc, id asc' if use_cursor else 'score desc',
                # Request both legacy short names and new full names for stability
                'fl': ','.join([
                    'id',
                    # title/author/type
                    'title','author','type','ti','au','dt',
                    # date fields
                    'documentdateiso','dd',
                    # bates/pages
                    'bates','pages','bn','pg',
                    # other fields used downstream
                    'availability','attach','access','artifact','collection','brand',
                    'score',
                ])
            }
            if additional_fqs:
                base_params['fq'].extend(additional_fqs)

            # Add strategy filters
            for field, value in strategy.get('filters', {}).items():
                base_params['fq'].append(f'{field}:{value}')

            # Page until we collect at least max_results, then trim
            collected = []
            try:
                if use_cursor:
                    cursor = '*'
                    while len(collected) < max_results:
                        params = dict(base_params)
                        params['cursorMark'] = cursor
                        response = requests.get(self.base_url, params=params, verify=False)
                        if response.status_code != 200:
                            break
                        payload = response.json()
                        docs = payload.get('response', {}).get('docs', [])
                        if not docs:
                            break
                        collected.extend(docs)
                        next_cursor = payload.get('nextCursorMark')
                        if not next_cursor or next_cursor == cursor:
                            break
                        cursor = next_cursor
                else:
                    start = 0
                    while len(collected) < max_results:
                        params = dict(base_params)
                        params['start'] = str(start)
                        response = requests.get(self.base_url, params=params, verify=False)
                        if response.status_code != 200:
                            break
                        docs = response.json().get('response', {}).get('docs', [])
                        if not docs:
                            break
                        collected.extend(docs)
                        # Advance page
                        start += SERVER_PAGE_SIZE
                # Process only up to max_results
                self.process_docs(collected[:max_results], search_strategy=strategy)
            except Exception as e:
                print(f"Error executing search: {e}")

        return self.document_store
