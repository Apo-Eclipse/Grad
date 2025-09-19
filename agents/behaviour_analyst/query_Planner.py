from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any, List, Union
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.ollama_llm import ollama_llm

class query_plannerOutput(BaseModel):
    output: List[str] = Field(
        ..., 
        description="A list of clear and simple steps for another database agent to create SQL-style queries that retrieve insights about a single user's behavior and spending patterns."
    )
    message: str = Field("", description="A concise summary of the steps outlined in the output.")
    
system_prompt = """
    You are the Query Planner Agent.  
    Your task is to outline clear and simple steps for another database agent to create SQL-style queries that retrieve insights about a **single user's** behavior and spending patterns.  
    ### Rules
    1. Each step must represent **one query** that can be executed by a database agent.  
    2. Focus only on **one user** at a time.  
    3. Respond with **text only** (no code, SQL, or programming syntax).  
    4. Concentrate on the **4 core aspects**:  
    - Time  
    - Location  
    - Store  
    - Category  
    5. Provide insights based on **two dimensions**:  
    - **Spending-based insights** (highest total amount, averages, min/max, etc.)  
    - **Frequency-based insights** (most frequent store, most visited location, etc.).  
    6. Use metrics like **mean, mode, min, max** when helpful.  
    7. Only propose steps that could be derived from the **data and metadata** available (no external knowledge).  
    8. Ensure all steps could be done with **SQL-like operations**.  
    9. Give a message summarizing what you have done to the orchestrator.

    ### There are already data acquired from the database:
    {data_acquired}

    ### Output Format
    Respond in the following JSON format expressing the output as a list of steps: 
    Example:
    "message": "A concise summary of the steps outlined in the output as a confirmation to the orchestrator."
    "output": [
        "Retrieve the user's personal information such as name and gender",
        "Find the top 5 categories where the user spends the most",
        "Identify the category with the highest spending per hour",
        "Determine the most frequent store visited by the user per each hour",
        "Calculate the average spending per day",
        ...
    ]
"""

metadata = """
        Tables:
        - user_table(
            User_ID           → Unique identifier for each user,
            Name              → User's full name,
            Age               → User's age in years,
            Gender            → User's gender,
            Job_Title         → Current job title,
            Employment_Status → Employment type (e.g., Full-time, Part-time, Unemployed),
            Education         → Highest level of education completed,
            Marital_Status    → User's marital status,
            Address           → Residential address (includes neighborhood/city),
            Income_EGP        → Monthly income in Egyptian Pounds
        )

        - transactions_table(
            Transaction_ID → Unique identifier for each transaction,
            User_ID        → Foreign key referencing user_table(ID),
            Category       → Spending category (e.g., Groceries, Transport),
            Store_Name     → Name of the store or service provider,
            Day            → Day of the month when the transaction occurred,
            Month          → Month of the year when the transaction occurred,
            Year           → Year of the transaction,
            Name_of_day    → Name of the weekday (e.g., Monday, Tuesday),
            Hour           → Hour of the transaction (24-hour format),
            Minute         → Minute of the transaction,
            Neighborhood   → Neighborhood where the transaction took place,
            City           → City of the transaction (e.g., Cairo, Giza),
            Amount_EGP     → Transaction amount in Egyptian Pounds,
            Type_spending  → Payment method used (e.g., Cash, Credit, E-Wallet)
        )
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", metadata),
    ("human", "The request is: {request}"),
    ("human", "orchestrator's message: {message}"),
])

Query_planner = prompt | gemini_llm.with_structured_output(query_plannerOutput)