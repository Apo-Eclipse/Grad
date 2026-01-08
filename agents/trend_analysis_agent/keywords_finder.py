import requests
from typing import List, Optional, Dict,TypedDict
from pydantic import BaseModel


class KeywordItem(TypedDict):
    keyword: str
    mentions: int
    sentiment: Optional[str]
    authority: Optional[float]
    category: Optional[str]
    type: Optional[str]
    source: Optional[str]


class KeywordsResponse(TypedDict):
    period: str
    total: int
    keywords: List[KeywordItem]

def get_keywords(period="daily", slim=True, limit=2,
                 sort="trending", category=None,
                 type_=None, source=None,
                 sentiment=None, min_mentions=None,
                 authority=None, search=None,
                 irrelevant=True):
    """
    Fetch keywords from Safron API.

    Args:
        period (str): "daily", "weekly", "monthly", "quarterly", "yearly"
        slim (bool): whether to omit source IDs & detailed sentiment; slim results are lighter
        limit (int): how many keywords to return (default 100)
        sort (str): "trending", "top", "alphabetical-a", "alphabetical-z"
        category (str): one of Safron's categories (e.g. "Companies & Organizations", "Tools & Services", etc.)
        type_ (str): type of source mentions (e.g. post, article, comment, newsletter)
        source (str): platform / origin (reddit, hackernews, etc.)
        sentiment (str): "positive", "negative", "neutral"
        min_mentions (int): minimum number of mentions a keyword must have to be included
        authority (int): minimum authority score
        search (str): a search term to filter specific keywords
        irrelevant (bool): whether to include the “Bucket (other)” / “irrelevant” category; default true

    Returns:
        dict: parsed JSON from Safron keywords endpoint.
    """

    url = "https://public.api.safron.io/v2/keywords"
    params = {
        "period": period,
        "slim": str(slim).lower(),
        "limit": limit,
        "sort": sort,
        "irrelevant": str(irrelevant).lower()
    }
    if category is not None:
        params["category"] = category
    if type_ is not None:
        params["type"] = type_
    if source is not None:
        params["source"] = source
    if sentiment is not None:
        params["sentiment"] = sentiment
    if min_mentions is not None:
        params["minMentions"] = min_mentions
    if authority is not None:
        params["authority"] = authority
    if search is not None:
        params["search"] = search

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Validate/parse with Pydantic
    return KeywordsResponse(**data)


def get_keywords_for_categories(categories: List[str],
                                period="daily",
                                slim=True,
                                limit=2,
                                sort="trending",
                                **kwargs) -> Dict[str, KeywordsResponse]:
    """
    Fetch keywords for multiple categories.

    Args:
        categories (List[str]): List of category names to search in.
        period, slim, limit, sort, **kwargs: passed to `get_keywords`.

    Returns:
        Dict[str, KeywordsResponse]: Mapping from category name to its keywords result.
    """
    results = {}
    for cat in categories:
        try:
            print(f"Fetching keywords for category: {cat}")
            results[cat] = get_keywords(period=period,
                                        slim=slim,
                                        limit=limit,
                                        sort=sort,
                                        category=cat,
                                        **kwargs)
        except Exception as e:
            print(f"Failed to fetch for {cat}: {e}")
            results[cat] = None
    return results
