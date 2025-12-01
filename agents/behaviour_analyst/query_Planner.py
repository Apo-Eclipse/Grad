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
<<<<<<< HEAD
<<<<<<< HEAD
    message: str = Field(
        "",
        description="One concise sentence summarizing what the steps cover and any notable gaps."
    )

system_prompt = r"""
You are the Query Planner Agent.
Produce a numbered list of ≤6 short, text-only steps. Each step must describe ONE aggregated query for ONE user_id.

What a step MUST include (plain language, no SQL):
  • Metric: one aggregate (SUM | COUNT | AVG | MAX | MIN)
  • Dimension: choose exactly ONE lens (time | store_name | city | budget/category | type_spending)
  • Time window: explicit (e.g., current month, last 90 days, last 6 months)
  • Filters: must include user_id={user}, and any request-specific filters
  • Output size: limit results to ≤24 rows (e.g., “top 10”, “last 6 months”)
  • Ordering: logical order (chronological or top/bottom by metric)

General rules:
  1) Aggregations only (no raw row listings).
  2) One lens per step (no mixing multiple dimensions in one step).
  3) Avoid duplicates: consider {steps} (already completed) and do not repeat them.
  4) Prefer comparisons when helpful (e.g., current vs prior period).
  5) If the request is vague, cover a compact baseline plan (trend, top category, overspend vs limit).
  6) If the user request cannot be planned from available fields, return a single step:
       "Query rejected"

Output JSON format:
{{
  "output": ["1) ...", "2) ..."],
  "message": "..."
}}

Inputs provided to you:
- Request: {request}
- User ID: {user}
- Completed Steps: {steps}
- Orchestrator message (context): {message}

Available schema (key fields only; PostgreSQL 18, schema public):
- transactions(transaction_id, date, amount, time, store_name, city, neighbourhood, type_spending, user_id, budget_id, created_at)
- budget(budget_id, user_id, budget_name, description, total_limit, priority_level_int, is_active, created_at, updated_at)
- income(income_id, user_id, type_income, amount, description, created_at, updated_at)
- goals(goal_id, goal_name, description, target, user_id, start_date, due_date, status, created_at, updated_at)
- users(user_id, first_name, last_name, ...)

Notes:
- “budget/category” refers to transactions.budget_id → budget.budget_name.
- Timestamps are WITHOUT time zone; use simple date windows like “current month” or “last 90 days”.
- Keep steps short and implementation-ready for a downstream SQL generator.
- Do NOT emit SQL. Only plain-language step descriptions.
=======
=======
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
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
<<<<<<< HEAD
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
=======
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
"""

metadata = """
------------------------------------------------------------
1. user_table
------------------------------------------------------------
Purpose: Stores demographic and socioeconomic information for each user.

<<<<<<< HEAD
<<<<<<< HEAD
last steps generated: {steps}

Orchestrator request: {message}
=======
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

=======
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

>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
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
<<<<<<< HEAD
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
=======
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
    ("user", "The request is: {request}, user ID is: {user}"),
    ("user", "orchestrator's message: {message}"),
])

Query_planner = prompt | azure_llm.with_structured_output(query_plannerOutput)