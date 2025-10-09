from typing import List,TypedDict
from pydantic import BaseModel
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate


class SummaryResponse(TypedDict):
    long_summary: str
    concise_summary: str
    title: str
    

PROMPT_THEME_SUMMARY_SYSTEM = """
Your job is to build a personalized news synthesis based on pre-identified themes for a person with this profile:

Name: {name}
Personality: {personality}
User notes: {user_interests}
Wants concise summaries? {concise_summaries}

You will receive:
1. A theme analysis with ranked themes and key points
2. Full keyword data for the time period "{time_period}"

Your task is to write focused synthesized reports that cover the identified themes in order of relevance. Use data from the key points and the full dataset to build your answer.
Get to the point but don't overload the user with information. 
Don't repeat the dataset—extract patterns, second-order effects, and contrarian takes.

What you should create:
- Short summary: 3-4 body paragraphs with up to 3 themes, 1400-2000 characters
- Long summary: 5-7 body paragraphs with up to 6 themes, less than 7000 characters
- Title: 2-3 words maximum

Always do this when building the summaries:
- Start the report with one or two sentences in one small introduction paragraph about what it covers and name the user to make it personal.
- Use bold **title:** formatting for each paragraph titles.
- End with a short paragraph on what this means for them and what to look out for.

Do not:
- Overload the user with information so it becomes incomprehensive. 
- Present the data as facts, it is what people are saying on social media, blogs and tech forums.
- Add in themes or information that the user may not be interested in.

Build around the themes provided, never repeat the data, instead focus on the themes and explain "so what" based on the user profile, 
Pull in what people are discussing (consensus vs skepticism) and why it matters for this specific user.
Focus only on what the user will find interesting based on the theme analysis. Never generalize.

Keep citations exactly as provided [n:n] format (ex. [1:12]) as we will parse them later.
"""

summary_prompt_template = ChatPromptTemplate.from_messages([
    ("system", PROMPT_THEME_SUMMARY_SYSTEM), # Shortened for clarity
    ("user", """
     Based on this theme analysis:
     {analysis_output}

     And this full data:
     {formatted_data}

     Write comprehensive long_summary and concise_summary focusing on the identified themes. Keep citations intact [n:n] format. Return a title too.
     """)
])

writer_chain = summary_prompt_template | azure_llm.with_structured_output(SummaryResponse)