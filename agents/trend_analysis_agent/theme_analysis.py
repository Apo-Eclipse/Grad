from typing import List,TypedDict
from pydantic import BaseModel
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate


class Theme(TypedDict):
    title: str
    relevance: int
    key_points: List[str]
    supporting_keywords: List[str]

class AnalysisResponse(TypedDict):
    themes: List[Theme]
    overall_focus: str
    user_priority_reasoning: str

PROMPT_ANALYSIS_SYSTEM = """
Your job is to synthesize data we picked up on tech forums, blogs and social media to identify the most relevant themes for a personalized report on what is going on.
You should cut out noise and identify information important for the user while keeping it entertaining.

Your task:
1. Identify 5–7 cross-cutting themes across the data. It should include what people are discussing (consensus vs skepticism). It should be relevant to the user's profile and to the data itself (don't ignore major happenings). The themes should be about extracting patterns, second-order effects, and contrarian takes.
2. Rank each theme by relevance to the user (1-10 scale, 10 being most relevant)
3. For each theme, provide:
   - "title":A clear title (2-4 words)
   - "relevance": relevance score based on user profile
   - "key_points": 5-7 key_points that should be covered with citations kept in the exact format [n:n].
   - "supporting_keywords": supporting_keywords from the data that support this theme.

Don't:
Don’t repeat the dataset as is only focusing on some of the data.

Do:
Take in all the data and then decide what is most important.

Consider the user's:
- Name: {name}
- Personality: {personality}  
- Interests: {user_interests}
- Time period preference: {time_period}

Remember if they are non-technical, or semi-technical you should not be including keywords that they won't understand. 
Keywords like Kubernetes, Proxmox, and maybe even Docker is not for non-technical people unless they are asking for this specifically (they are working in this domain).
Be smart around what you decide to include based on what you think they already know.

Focus on themes that would be most valuable and interesting to this specific user.
"""

analysis_prompt_template = ChatPromptTemplate.from_messages([
    ("system", PROMPT_ANALYSIS_SYSTEM), # Using a shortened version for clarity
    ("user", "Analyze this keyword data and identify the most relevant themes:\n\n{formatted_data}")
])


analysis_chain = analysis_prompt_template | azure_llm.with_structured_output(AnalysisResponse)
