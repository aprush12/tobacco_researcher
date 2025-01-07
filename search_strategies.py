import re
from typing import List, Dict, Any, Set, Tuple
import json

class SearchStrategies:
    def __init__(self, model, query):
        self.model = model
        self.query = query

    def generate_search_strategies(self, prompt) -> List[Dict[str, Any]]:
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Try to find JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    strategies = json.loads(json_match.group())
                    print("\nGenerated search strategies:")
                    for idx, strat in enumerate(strategies['strategies'], 1):
                        print(f"\nStrategy {idx}:")
                        print(f"Terms: {strat.get('search_terms')}")
                        print(f"Filters: {strat.get('filters')}")
                    return strategies['strategies']
                else:
                    return self._fallback_search_strategy()
                    
            except Exception as e:
                print(f"Error generating search strategies: {e}")
                return self._fallback_search_strategy()

    def _fallback_search_strategy(self) -> List[Dict[str, Any]]:
            """Generate basic search strategies from query terms"""
            print("\nFalling back to query text parsing")
            query_terms = self.query.lower()
            # Extract any quoted phrases or word combinations
            terms = re.findall(r'"([^"]*)"|\b\w+\s+\w+\b|\b\w+\b', query_terms)
            
            strategies = []
            if len(terms) >= 2:
                strategies.append({
                    "search_terms": f"{terms[0]} AND {terms[1]}",
                    "filters": {},
                    "rationale": "Primary terms combination"
                })
            
            if len(terms) >= 3:
                strategies.append({
                    "search_terms": f"{terms[1]} AND {terms[2]}",
                    "filters": {},
                    "rationale": "Secondary terms combination"
                })
            
            all_terms = " AND ".join(terms[:4])
            strategies.append({
                "search_terms": all_terms,
                "filters": {},
                "rationale": "Combined key terms"
            })
            
            return strategies
