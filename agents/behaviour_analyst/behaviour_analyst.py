from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
import sqlite3
conn = sqlite3.connect("D:/projects/Multi-Agent System/data/database.db")

class Behaviour_AnalystOutput(BaseModel):
    final_output: str = Field(..., description="The analysis report.")

system_prompt = """
    You are the Behaviour Analyst Agent.
    Analyze data from the database and provide a report.
    Try to get insights about user behavior and spending patterns from the dataset.
    Rules You must follow:
    1. Focus on key metrics such as average spending, category breakdown, and trends over time.
    2. Highlight any anomalies or significant changes in behavior.
    3. Our focus is for one User only.
    4. Responds with description the the query needed
    5. Write only SQLite supported Queries
    6. Responds with the final output in a structured format with no introduction
    7. Responds in json
    like:
    [
        {{
            "step": 1,
            "description": "the description for step 1",
            "query": "Queries for step 1"
        }},
        {{
            "step": 2,
            "description": "the description for step 2",
            "query": "Queries for step 2"
        }}
    ]
"""

user_prompt = """
    "user_table" Table
        Description: Contains demographic and employment details of one user for each row.
    Columns:
        ID: Unique user identifier
        Name: Full name of the user
        Age: User's age
        Gender: User's gender
        Job_Title: Occupation or role
        Employment_Status: Current employment status
        Education: Highest education level attained
        Marital_Status: User's marital status
        Address: Residential address
        Income_EGP: Monthly income in Egyptian Pounds

    "transactions_table" Table
        Description: Contains spending transactions 
    Columns:
        Transaction_ID: Unique transaction identifier
        User_ID: References the user profile ID
        Category: Spending category (Entertainment, Food & Dining, etc.)
        Store_Name: Specific store or brand where transaction took place
        DateTime: Timestamp of the transaction (YYYY-MM-DD HH:MM:SS)
        Neighborhood: Area/neighborhood of the transaction
        City: City of the transaction
        Amount_EGP: Transaction amount in Egyptian Pounds
"""


prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", user_prompt),
    ("human", "Consider only one user to get insights whose ID is 1")
])

Behaviour_Analyst = prompt | gemini_llm.with_structured_output(Behaviour_AnalystOutput)