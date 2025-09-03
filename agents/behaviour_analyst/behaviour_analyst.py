from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
class Behaviour_AnalystOutput(BaseModel):
    message: str = Field(..., description="The message from the agent. (ok if there is no problem and error if there is)")
    description: str = Field(..., description="The description of the work done by the agent.")
    output: str = Field(..., description="what are the steps needed to be done in words")

system_prompt = """
    You are the Behaviour Analyst Agent.
    Try to provide simple steps for another database agent to create the queries to retrieve user behavior and spending patterns for only one user.
    1. Each step to represent a single query that can be executed by the database agent.
    2. Focus only on one user
    3. You only write text no code, queries or any other programming constructs.
    4. Focus on the 4 most important aspects time, location, type of spending, and category.
    5. Try to combine different aspects to create more comprehensive queries.
    6. Use metrics like mean, median, mode, min, max to give insights
    7. You have to respond with 3 things message, description, output
        * Message: respond with "error" if there is any problem and "ok" if isn't there
        * Description: respond with what you have done or with error description there is anything like "no enough data".
        * output: that is the work you have done including the quires and their descriptions, and blank [] if there is error
            - Write the final output in json formate
            Like:
            [
                "first step",
                "second step"
            ]
    8. Your output should be in the following format:
    {{
        "message": "ok",
        "description": "description of what was done",
        "output": [
            "first step",
            "second step",
            ....
        ]
    }}
    9. Try to output the maximum number of steps possible you can get.
    10. Only provide steps that could be found or extracted from the from the data based on the metadata and doesnot require knowledge out of them
    11. Create steps what could be done by SQL
"""

metadata = """
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
    ("human", metadata),
])

Behaviour_Analyst = prompt | gemini_llm.with_structured_output(Behaviour_AnalystOutput)