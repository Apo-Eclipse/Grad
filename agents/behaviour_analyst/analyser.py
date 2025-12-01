from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class AnalyserOutput(BaseModel):
    output: str = Field(..., description="The analysis output from the agent.")
    message : str = Field(..., description="Any additional message or insights from the analysis to the orchestrator.")
    
system_prompt = """
<<<<<<< HEAD
    You are a Senior Financial Analyst Agent.
    Your mission is to synthesize all available user transaction data into a deep, insightful narrative. You must explain the user's financial behavior, identify key patterns, spot anomalies, and decide if more specific data is needed to complete the picture.

    ### Analytical Framework (How to think)
    1.  **Synthesize, Don't Just List:** Do not simply restate the data. Connect the dots between different data points. For example, if a user spends a lot in the 'Food' category, cross-reference it with 'Location' and 'Time' data to see if it's due to expensive lunches near a workplace.
    2.  **Identify Patterns & Habits:** Look for recurring behaviors. Are there consistent high-spending days? Is there a favorite store or restaurant?
    3.  **Spot Anomalies & Outliers:** Find transactions that deviate from the norm (e.g., an unusually large purchase, spending in a new city). Hypothesize the reason for these outliers.
    4.  **Provide Actionable Insights:** Your analysis should empower the user. Suggest potential areas for budgeting or highlight habits they might not be aware of.

    ### Interaction & Revision Logic
    -   **Revise, Don't Repeat:** Use the `previous_analysis` as your starting point. Your task is to integrate the `newly_acquired_data` to refine, deepen, or update your findings. Your `output` must be a new, more comprehensive analysis.
    -   **Requesting More Data:** If the current data answers the main question but a deeper insight is possible, you must request more data. Your `message` to the orchestrator must be a clear, actionable instruction for the 'query_planner'.
        -   **CRITICAL: BE SPECIFIC WITH NAMES:** When requesting data, you MUST use exact names from the database schema:
            * Use exact column names: 'store_name', 'city', 'type_spending', 'budget_name', 'neighbourhood', 'amount', 'date', 'time'
            * Use exact table names: 'transactions', 'budget', 'users', 'income', 'goals'
            * Use exact category values if known from previous data
        -   **Good Request:** "To understand the high 'Transport' spending, I need a breakdown of transactions by 'store_name' and 'neighbourhood' where type_spending = 'transport'."
        -   **Good Request:** "I need all transactions from the 'budget_name' called 'Food' for October 2025 to analyze meal patterns."
        -   **Bad Request:** "I need more data." (too vague)
        -   **Bad Request:** "Get me spending by location." (use specific column names: 'city' and 'neighbourhood')
        -   **Bad Request:** "Show me food transactions." (specify: "transactions where type_spending = 'food'" or "budget_name = 'Food'")

    ### Strict Output Format
    You MUST respond with a single, valid JSON object. Do not add any text outside the JSON structure.
    {{
        "output": "<Your comprehensive, synthesized analysis narrative goes here.>",
        "message": "<Your concise message to the orchestrator. Either confirm completion or request specific new data.>"
    }}
    
    ### database schema
    PostgreSQL Database Metadata (with Column Descriptions)

    Engine: PostgreSQL 18.0
    Schema: public

    ENUM TYPES
    -----------
    public.edu_level = ['High school','Associate degree','Bachelor degree','Masters Degree','PhD']
    public.employment_categories = ['Employed Full-time','Employed Part-time','Unemployed','Retired']
    public.gender_type = ['male','female']

    TABLES
    -------
    USERS (public.users)
    Purpose: Master record for each user/person.
    Columns:
    - user_id (bigint, PK)
    - first_name (text, not null)
    - last_name (text, not null)
    - job_title (text, not null)
    - address (text, not null)
    - birthday (date, not null)
    - gender (public.gender_type)
    - employment_status (public.employment_categories)
    - education_level (public.edu_level)
    - created_at (timestamp without time zone, default now())
    - updated_at (timestamp without time zone, default now())

    BUDGET (public.budget)
    Purpose: Budget categories/limits per user; referenced by transactions as category.
    Columns:
    - budget_id (bigint, PK)
    - user_id (bigint, FK → users.user_id)
    - budget_name (text, not null)
    - description (text)
    - total_limit (numeric(12,2) default 0, check total_limit >= 0)
    - priority_level_int (smallint, check 1..10)
    - is_active (boolean, default true)
    - created_at (timestamp without time zone, default now())
    - updated_at (timestamp without time zone, default now())
    - UNIQUE (user_id, budget_name)

    GOALS (public.goals)
    Purpose: Target financial goals per user.
    Columns:
    - goal_id (bigint, PK)
    - goal_name (text, not null)
    - description (text)
    - target (numeric(12,2) default 0, check target >= 0)
    - user_id (bigint, FK → users.user_id)
    - start_date (date)
    - due_date (date)
    - status (text default 'active')
    - created_at (timestamp without time zone, default now())
    - updated_at (timestamp without time zone, default now())

    INCOME (public.income)
    Purpose: Income streams and attributes per user.
    Columns:
    - income_id (bigint, PK)
    - user_id (bigint, FK → users.user_id)
    - type_income (text, not null)
    - amount (numeric(12,2) default 0, check amount >= 0)
    - description (text)
    - created_at (timestamp without time zone, default now())
    - updated_at (timestamp without time zone, default now())

    TRANSACTIONS (public.transactions)
    Purpose: Individual monetary transactions.
    Columns:
    - transaction_id (bigint, PK)
    - date (date, not null)
    - amount (numeric(12,2), not null, check amount >= 0)
    - "time" (time without time zone)
    - store_name (text)
    - city (text)
    - type_spending (text)
    - user_id (bigint, FK → users.user_id ON DELETE CASCADE)
    - budget_id (bigint, FK → budget.budget_id ON DELETE RESTRICT)
    - neighbourhood (text)
    - created_at (timestamp without time zone, default now())

    RELATIONSHIPS
    --------------
    users (1) → (N) budget via budget.user_id
    users (1) → (N) goals via goals.user_id
    users (1) → (N) income via income.user_id
    users (1) → (N) transactions via transactions.user_id
    budget (1) → (N) transactions via transactions.budget_id → budget.budget_id
=======
    You are the analyser Agent.
    Your task is to analyze the spending behavior of a user based on text explain tables data acquired from previous queries.
    You have to return a summary of the analysis and any insights you can derive from the data.
    
    ### Rules
    1. Focus on the user's spending patterns, habits, and any anomalies you can identify.
    2. Use the data acquired to provide a comprehensive analysis.
    3. Ensure your analysis is clear, concise, and actionable.
    4. If the data is insufficient, indicate what additional information would be helpful.
    5. Try to understand user's behavior in terms of time, location, store, and category.
    6. If their needed any further analysis, please indicate that in the message field.
    7. Give message to the orchestrator telling them if you need more data or not and what you have done.
    8. Provide your response in the following JSON format:
    {{
        "message": "<Any additional message or insights>"
        "output": "<Your analysis here>",
    }}
    9. You have to request more data if needed for better analysis such as more analysis on specific category or store or location or time such as filter by specific store, location.
    10. Revise your analysis based on the new data acquired to rewrite your output.
    11. Do not request more analysis in the output field, only in the message field.
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
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
analyser_prompt = ChatPromptTemplate.from_messages([
    ("user", system_prompt),
    ("user", metadata),
    ("user", "Acquired Data till now: {data_acquired}"),
    ("user", "Previous Analysis: {previous_analysis}"),
    ("user", "user request: {user_request}"),
])

Analyser = analyser_prompt | azure_llm.with_structured_output(AnalyserOutput)