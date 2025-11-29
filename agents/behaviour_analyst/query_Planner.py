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
    9. Don't use steps such as "Find all transactions made by the user .." to avoid redundancy.
    10. Give a message summarizing what you have done to the orchestrator.
    
    
    ### Output Format
    Respond in the following JSON format expressing the output as a list of steps: 
    Example:
    "message": "A concise summary of the steps outlined in the output as a confirmation to the orchestrator."
    "output": [
        "Step 1 ...",
        "Step 2 ...",
        ...
    ]
"""

metadata = """
------------------------------------------------------------
1. user_table
------------------------------------------------------------
Purpose: Stores demographic and socioeconomic information for each user.

Columns:
- User_ID (INT, PK, AUTO_INCREMENT): Unique identifier for each user.
- Name (VARCHAR(100)): User's full name.
- Age (INT): User's age in years.
- Gender (ENUM('Male','Female','Other')): Gender of the user.
- Job_Title (VARCHAR(100)): Current job title.
- Employment_Status (ENUM('Full-time','Part-time','Unemployed','Freelancer','Student')): Employment type.
- Education (VARCHAR(100)): Highest level of education completed.
- Marital_Status (ENUM('Single','Married','Divorced','Widowed')): Marital status.
- Address (VARCHAR(200)): Residential address (includes neighborhood and city).
- Income_EGP (DECIMAL(10,2)): Monthly income in Egyptian Pounds.

------------------------------------------------------------
2. transactions_table
------------------------------------------------------------
Purpose: Stores detailed records of every financial transaction for users.

Columns:
- Transaction_ID (INT, PK, AUTO_INCREMENT): Unique transaction identifier.
- User_ID (INT, FK → user_table.User_ID): Linked user.
- Category (VARCHAR(50)): Spending category (e.g., Groceries, Transport, Coffee).
- Store_Name (VARCHAR(100)): Vendor or service provider name.
- Day (TINYINT): Day of the month when the transaction occurred.
- Month (TINYINT): Month of the year when the transaction occurred.
- Year (SMALLINT): Year of the transaction.
- Name_of_day (ENUM('Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday')): Weekday name.
- Hour (TINYINT): Hour of the transaction (24-hour format).
- Minute (TINYINT): Minute of the transaction.
- Neighborhood (VARCHAR(100)): Neighborhood of the transaction.
- City (VARCHAR(100)): City of the transaction (e.g., Cairo, Giza).
- Amount_EGP (DECIMAL(10,2)): Transaction amount in Egyptian Pounds.
- Type_spending (ENUM('Cash','Credit','Debit','E-Wallet','Bank Transfer')): Payment method.

------------------------------------------------------------
3. budget_table
------------------------------------------------------------
Purpose: Tracks spending limits and monitoring for each user and category.

Columns:
- user_id (INT, FK → user_table.User_ID): Linked user.
- budget_name (VARCHAR(100)): Descriptive name for the budget (e.g., 'Groceries Budget Sep 2025').
- priority_level (ENUM('low','mid','high')): Importance of this budget.
- limit (DECIMAL(10,2)): Planned or allowed budget cap.
- description (TEXT): Short status text describing spending performance or targets.

------------------------------------------------------------
4. goals_table
------------------------------------------------------------
Purpose: Tracks long-term financial goals and progress for each user.

Columns:
- user_id (INT, FK → user_table.User_ID): Linked user.
- goal_name (VARCHAR(100)): Goal title (e.g., 'Emergency Fund').
- target_date (DATE): Date by which the user wants to reach the goal.
- target_saving (DECIMAL(10,2)): Total savings target in EGP.
- current (DECIMAL(10,2)): Current amount saved.
- objective (TEXT): Description of the goal.
- query_saving (VARCHAR(255)): Optional computed formula or query for dynamic savings tracking.

------------------------------------------------------------
Relationships:
- user_table (1) ───< transactions_table (many)
- user_table (1) ───< budget_table (many)
- user_table (1) ───< goals_table (many)

------------------------------------------------------------
Indexes and Keys:
- PK: user_table.User_ID, transactions_table.Transaction_ID
- FK: transactions_table.User_ID, budget_table.user_id, goals_table.user_id

------------------------------------------------------------
Notes:
- All monetary values are stored in Egyptian Pounds (EGP).
- Date and time fields enable fine-grained temporal analysis.
- The schema supports both behavioral analytics and personalized financial storytelling.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
    ("user", "The request is: {request}, user ID is: {user}"),
    ("user", "orchestrator's message: {message}"),
])

Query_planner = prompt | azure_llm.with_structured_output(query_plannerOutput)