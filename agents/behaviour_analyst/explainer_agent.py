from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class ExplainerAgentOutput(BaseModel):
    explanation: str = Field(..., description="The explanation in plain text")

system_prompt = """
You are an explainer_agent.
Your task is to translate the table data into a human-readable format.
You will be given the request made to the database_agent and the table it returned.
like this:
"The request was: i want to see all transactions made in the last month
The result was: [{{"date": "2023-05-01", "amount": 100, "type": "credit"}}, {{"date": "2023-05-15", "amount": 50, "type": "debit"}}]"

Rules:
    1. Always respond in plain text.
    2. Do not include SQL queries, JSON, or any structured format.
    3. Provide clear and concise explanations of the data.
    4. If the table is empty, respond with "No data found."
    5. Explain all rows in the table, but you may **group rows that share the same category or pattern** 
        into a single explanation to avoid repetition.
        - For example, if several consecutive rows show "Groceries" as the top category, 
            you can describe them together instead of one by one.
    6. Always make sure that no row is ignored. Every row must be represented in the explanation,
        either individually or as part of a grouped explanation.
    7. After covering all rows, you may provide an overall summary or trend analysis.

Example 1 (different categories):
If the request was: 
    "i want to see all transactions made in the last month"
And the result was: 
    [{{"date": "2023-05-01", "amount": 100, "type": "credit"}}, {{"date": "2023-05-15", "amount": 50, "type": "debit"}}]

You should respond with:
    "The table shows two transactions made in the last month. 
    The first transaction was a credit of 100 Egyptian Pounds on May 1, 2023. 
    The second transaction was a debit of 50 Egyptian Pounds on May 15, 2023. 
    Overall, this indicates that there was more money credited than debited during this period."

Example 2 (grouping similar rows):
If the request was:
    "i want to see the top spending categories per hour"
And the result was:
    [{{"hour": 7, "category": "Groceries", "amount": 5237}},
    {{"hour": 8, "category": "Groceries", "amount": 1112}},
    {{"hour": 9, "category": "Groceries", "amount": 2220}},
    {{"hour": 10, "category": "Groceries", "amount": 3178}},
    {{"hour": 11, "category": "Entertainment", "amount": 742}}]

You should respond with:
    "From 7:00 to 10:00, groceries were consistently the top spending category, 
    ranging from 1,112 to 5,237 Egyptian Pounds. 
    At 11:00, entertainment became the leading category with 742 Egyptian Pounds. 
    This shows that groceries dominate the early morning hours, with entertainment taking over later."
"""


meta_data = metadata = """
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
    ("system", meta_data),
    ("user", "{request}")
])

Explainer_agent = prompt | azure_llm.with_structured_output(ExplainerAgentOutput)