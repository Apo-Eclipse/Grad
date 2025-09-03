from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.azure_models import azure_llm
import sqlite3

conn = sqlite3.connect("D:/projects/HR_Chatbot/Data/database.db")

class DatabaseAgentOutput(BaseModel):
    final_output: str = Field(..., description="The final output of the agent")


system_prompt = """
    You are a database_agent
    Your task is to understand user request and provide the necessary SQLite queries to extract the required data.
    Rules:
    1. Focus only in responding with the SQL compatible queries.
    2. Do not provide any explanations or additional information.
    3. You must only provide queries that are valid in SQLite.
    4. You are not allowed to provide any queries that update or delete any data, and if you do, the query will be rejected and respond only with "Query rejected".
    5. Our focus is mainly on one User given
    6. You will receive multiple steps respond with the corresponding SQL queries for each step.
    7. You cannot write more than one query per step.
    8. Respond with this formate:
    Like
    [
        {{
            "step":"step given from the behaviour_analyst",
            "query": "SQL query corresponding to the step"
        }},
        {{
            "step": "second step from the behaviour_analyst",
            "query": "SQL query corresponding to the second step"
        }},
        ...
    ]
    9. You are not allowed to provide any queries that update or delete any data.
"""

metadata = """
    Here is the database metadata:
    Table Name: user_table 
    Description: Contain personal data for the user
    columns:
    ------------------------------------------
    Name : "ID": 
    Type : INTEGER PRIMARY KEY
    Description : Unique identifier for each user
    ------------------------------------------
    Name : "Name": 
    Type : TEXT
    Description : The name of the user
    ------------------------------------------
    Name : "Age": 
    Type : INTEGER
    Description : The age of the user
    ------------------------------------------
    Name : "Gender": 
    Type : TEXT
    Description : The gender of the user
    ------------------------------------------
    Name : "Job_Title": 
    Type : TEXT
    Description : The job title of the user
    ------------------------------------------
    Name : "Employment_Status": 
    Type : TEXT
    Description : The employment status of the user
    ------------------------------------------
    Name : "Education": 
    Type : TEXT
    Description : The education level of the user
    ------------------------------------------
    Name : "Marital_Status": 
    Type : TEXT
    Description : The marital status of the user
    ------------------------------------------
    Name : "Address": 
    Type : TEXT
    Description : The address of the user
    ------------------------------------------
    Name : "Income_EGP": 
    Type : INTEGER
    Description : The income of the user in EGP
    ------------------------------------------
    
    ==========================================
    
    Table Name: transactions_table
    Description: Contain transaction data for the user
    columns:
    ------------------------------------------
    Name : "Transaction_ID": 
    Type : INTEGER PRIMARY KEY
    Description : Unique identifier for each transaction
    ------------------------------------------
    Name : "User_ID": 
    Type : INTEGER
    Description : The ID of the user associated with the transaction
    ------------------------------------------
    Name : "Category": 
    Type : TEXT
    Description : The category of the transaction
    ------------------------------------------
    Name : "Store_Name": 
    Type : TEXT
    Description : The name of the store where the transaction took place
    ------------------------------------------
    Name : "DateTime": 
    Type : TEXT
    Description : The date and time when the transaction occurred
    ------------------------------------------
    Name : "Neighborhood": 
    Type : TEXT
    Description : The neighborhood where the transaction took place
    ------------------------------------------
    Name : "City": 
    Type : TEXT
    Description : The city where the transaction took place
    ------------------------------------------
    Name : "Amount_EGP": 
    Type : INTEGER
    Description : The amount of money involved in the transaction in EGP
    ------------------------------------------
"""

#Note: all dates are written in day/month/year in text like 1/4/2023 no zero paddings 

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
    ("user", "focus on user_id 1"),
    ("user", "{request}")
])

DatabaseAgent = prompt | gemini_llm.with_structured_output(DatabaseAgentOutput)