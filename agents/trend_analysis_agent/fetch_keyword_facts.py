import requests
import re
import time
from typing import Dict, List, Optional,TypedDict
from pydantic import BaseModel

class Citation(TypedDict):
    n: int
    url: Optional[str] = None


class KeywordFactsResponse(TypedDict):
    keyword: str
    summary: str
    interesting: List[str]
    citations: List[Citation]


def fetch_keyword_facts(keyword: str, period: str, max_retries: int = 3) -> Dict:
    """Fetch facts for a specific keyword from Safron AI facts API."""
    for attempt in range(max_retries):
        try:
            print(f"Fetching facts for: {keyword} (attempt {attempt + 1}/{max_retries})")
            url = "https://public.api.safron.io/v2/ai-keyword-facts"
            payload = {"keywords": keyword, "period": period}
            r = requests.post(url, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json() or {}
            
            summary = data.get("summary", "")
            interesting = data.get("interesting", [])
            all_citations = data.get("citations", [])
            
            if not summary and not interesting:
                facts = data.get("facts", [])
                if facts:
                    if len(facts) >= 3:
                        summary = " ".join(facts[:3])  
                        interesting = facts[3:]       
                    elif len(facts) >= 1:
                        summary = " ".join(facts)    
                        interesting = []
            
            referenced_citations = set()
            
            for match in re.finditer(r'\[(\d+)\]', summary):
                referenced_citations.add(int(match.group(1)))
            
            for item in interesting:
                for match in re.finditer(r'\[(\d+)\]', item):
                    referenced_citations.add(int(match.group(1)))
            
            filtered_citations = [
                citation for citation in all_citations 
                if citation.get("n") in referenced_citations
            ]
            
            return KeywordFactsResponse(
                keyword=keyword,
                summary=summary,
                interesting=interesting,
                citations=[Citation(**c) for c in filtered_citations]
            )
            
        except Exception as e:
            print(f"Keyword facts fetch failed: {keyword} (attempt {attempt + 1}/{max_retries}) - {e}")
            if attempt < max_retries - 1:
                print(f"Retrying {keyword} in 2 seconds...")
                time.sleep(2)
            else:
                import traceback
                print(traceback.format_exc())
    
    return {}


def fetch_facts_for_keywords(keywords: List[str], period: str = "weekly", max_retries: int = 3) -> List[Dict]:
    """Loop over a list of keywords and fetch facts for each."""
    results = []
    for kw in keywords:
        facts = fetch_keyword_facts(kw, period, max_retries)
        if facts:  # only add if we got something
            results.append(facts)
    return results