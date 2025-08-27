from typing import List, Dict, Any


class AnalyzerV2:
    def __init__(self, model, strategies, content_store, prompt_manager_v2):
        self.model = model
        self.strategies = strategies
        self.content_store = content_store
        self.pm = prompt_manager_v2

    def analyze_topic(self, user_query: str, num_results_per_search: int, additional_fqs=None) -> Dict[str, Any]:
        print(f"\n[V2] Starting analysis for: {user_query}")
        cached_docs = self.content_store.execute_searches(self.strategies, num_results_per_search, additional_fqs)
        results = self._analyze_documents_in_batches(cached_docs, user_query)
        return results, cached_docs

    def _analyze_documents_in_batches(self, docs: Dict[str, Any], user_query: str, BATCH_SIZE=5) -> Dict[str, Any]:
        batch_results: Dict[str, Any] = {}
        doc_list = list(docs.values())

        for i in range(0, len(doc_list), BATCH_SIZE):
            batch = doc_list[i:i + BATCH_SIZE]
            try:
                prompt = self.pm.create_document_analysis_prompt(batch, user_query)
                response = self.model.generate_content(prompt)
                analysis = self.pm.parse_response(response.text)
                if analysis:
                    batch_results.update(analysis)
                    self._print_batch_labels(analysis)
            except Exception as e:
                print(f"[V2] Error in batch {i}: {e}")
        return batch_results

    def _print_batch_labels(self, analysis: Dict[str, Any]):
        print("\n[V2] Labels for batch:")
        for doc_id, details in analysis.items():
            print(f"{doc_id}: {details.get('label')} (conf={details.get('confidence')})")

    def rank_results(self, analysis: Dict[str, Any], docs: Dict[str, Any]) -> List[str]:
        tier = {"smoking_gun": 3, "strong": 2, "related": 1, "irrelevant": 0}

        def _truthy(v) -> bool:
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            if isinstance(v, str):
                return v.strip().lower() in {"true", "yes", "y", "1"}
            return bool(v)

        def facet_boost(d: Dict[str, Any]) -> float:
            f = d.get("facets", {}) or {}
            boost = 0.0
            if _truthy(f.get("directive_language")):
                boost += 0.05
            if _truthy(f.get("budget_numbers")):
                boost += 0.05
            if _truthy(f.get("date_in_range")):
                boost += 0.02
            if _truthy(f.get("mentions_brands")):
                boost += 0.02
            dt_val = f.get("doc_type") or ""
            if isinstance(dt_val, list):
                dt = " ".join(str(x) for x in dt_val).lower()
            else:
                dt = str(dt_val).lower()
            preferred = {"brand plan", "memo", "budget", "marketing document"}
            if any(p in dt for p in preferred):
                boost += 0.03
            return boost

        def key(doc_id: str):
            d = analysis.get(doc_id, {})
            label = d.get("label", "irrelevant")
            conf = d.get("confidence", 0.0)
            try:
                conf_f = float(conf)
            except Exception:
                conf_f = 0.0
            return (tier.get(label, 0), conf_f, facet_boost(d))
        # Initial sort by tier, confidence, facet boost
        ranked = sorted(analysis.keys(), key=key, reverse=True)

        # Frequency tie-break within same label + confidence band
        # Build frequency map from content_store title_hash (sum counts per normalized title)
        title_counts: Dict[str, int] = {}
        for doc_id, doc in docs.items():
            title = doc.get('title') or ''
            td = self.content_store.title_hash.get(title, {})
            if isinstance(td, dict):
                title_counts[doc_id] = sum(td.values())
            else:
                title_counts[doc_id] = 1

        # Group by (tier, rounded confidence)
        from collections import defaultdict
        groups: Dict[tuple, list] = defaultdict(list)
        for doc_id in ranked:
            d = analysis.get(doc_id, {})
            label = d.get('label', 'irrelevant')
            try:
                conf_f = float(d.get('confidence', 0.0))
            except Exception:
                conf_f = 0.0
            band = round(conf_f, 2)
            groups[(tier.get(label, 0), band)].append(doc_id)

        # Reorder each group by frequency desc, stable to preserve previous ordering otherwise
        final_list: list = []
        for key_group in sorted(groups.keys(), reverse=True):
            ids = groups[key_group]
            ids_sorted = sorted(ids, key=lambda i: title_counts.get(i, 0), reverse=True)
            final_list.extend(ids_sorted)

        # Final collapse: deduplicate by normalized title, then by OCR fingerprint similarity
        def clean_text(s: str) -> str:
            s = s or ""
            s = ''.join(ch.lower() if (ch.isalnum() or ch.isspace()) else ' ' for ch in s)
            return ' '.join(s.split())

        def shingles(s: str, k: int = 5, window: int = 5000) -> set:
            s = clean_text(s)[:window]
            if len(s) < k:
                return set()
            return {s[i:i+k] for i in range(len(s) - k + 1)}

        def jaccard(a: set, b: set) -> float:
            if not a or not b:
                return 0.0
            inter = len(a & b)
            if inter == 0:
                return 0.0
            union = len(a | b)
            return inter / union if union else 0.0

        seen_titles: set = set()
        kept: list = []
        kept_shingles: list[set] = []
        THRESH = 0.92

        for doc_id in final_list:
            doc = docs.get(doc_id) or {}
            title = (doc.get('title') or '').strip()

            # Title-based collapse (skip empty or '(untitled)')
            if title and title != '(untitled)':
                if title in seen_titles:
                    continue

            # OCR-based collapse
            ocr = doc.get('ocr_text') or ''
            cur_sh = shingles(ocr)
            is_dup = False
            for prev in kept_shingles:
                if jaccard(cur_sh, prev) >= THRESH:
                    is_dup = True
                    break
            if is_dup:
                continue

            kept.append(doc_id)
            kept_shingles.append(cur_sh)
            if title and title != '(untitled)':
                seen_titles.add(title)

        return kept
