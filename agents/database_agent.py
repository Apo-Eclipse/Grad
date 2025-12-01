from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
import sqlite3

conn = sqlite3.connect("D:/projects/Multi-Agent System/data/database.db")

class DatabaseAgentOutput(BaseModel):
    query: str = Field(..., description="The corresponding SQL query")

system_prompt = """
You are a database_agent.
Your task is to translate a single natural language step into one valid SQLite query.

Rules:
    1. Only respond with ONE SQL query.
    2. Output must always be a single JSON object:
    {{
        "query": "the SQL query"
    }}
    3. Do not include explanations, comments, or multiple queries.
    4. SQL must be valid SQLite syntax.
    5. Use single quotes inside the SQL, double quotes for JSON.
    6. Do NOT generate UPDATE or DELETE queries. If asked, respond with:
        {{"query": "Query rejected"}}
    7. If you cannot generate a query, return:
        {{"query": "Query rejected"}}

Date and Time Handling:
    - Use the structured fields directly:
        * Day, Month, Year for calendar values
        * Name_of_day for weekday (e.g., Monday, Tuesday)
        * Hour and Minute for time-of-day analysis
    - Do not reference the raw DateTime column.

<<<<<<< HEAD
RULES:
1. One SQL query only. PostgreSQL 18.0 syntax.
2. Use DATE_TRUNC, EXTRACT for dates. Single quotes in SQL, double quotes in JSON.
3. Available tables: users, budget, goals, income, transactions (read-only)
4. Numeric: ROUND(val::numeric, 2) for 2 decimals. Use aggregates (SUM, COUNT, AVG, MIN, MAX) with GROUP BY.
5. Always constrain by user_id's.
6. In selecting columns dont show id fields, is_active, created_at, updated_at.
7. In selecting columns try to show columns names not index numbers. so the results are easy to read. like {{"budget_name": "Food", "month": "2024-01", "total_spent": 250.75}}, not {{ 0: "Food", 1: "2024-01", 2: 250.75}}

DATABASE SCHEMA (with field types):

TABLE: transactions (NO "updated_at" - only created_at exists)
  - transaction_id (bigint, PK)
  - date (date, not null)
  - amount (numeric(12,2), not null, CHECK amount >= 0)
  - time (time without time zone)
  - store_name (text)
  - city (text)
  - type_spending (text)
  - user_id (bigint, FK -> users.user_id)
  - budget_id (bigint, FK -> budget.budget_id)
  - neighbourhood (text)
  - created_at (timestamp without time zone, default now())

TABLE: budget
  - budget_id (bigint, PK)
  - user_id (bigint, FK -> users.user_id)
  - budget_name (text, not null)
  - description (text)
  - total_limit (numeric(12,2), default 0, CHECK total_limit >= 0)
  - priority_level_int (smallint, 1-10)
  - is_active (boolean, default true)
  - created_at (timestamp without time zone)
  - updated_at (timestamp without time zone)

TABLE: users
  - user_id (bigint, PK)
  - first_name (text, not null)
  - last_name (text, not null)
  - job_title (text, not null)
  - address (text, not null)
  - birthday (date, not null)
  - gender (gender_type: male|female)
  - employment_status (employment_categories: Employed Full-time|Part-time|Unemployed|Retired)
  - education_level (edu_level: High school|Associate degree|Bachelor degree|Masters Degree|PhD)
  - created_at (timestamp without time zone)
  - updated_at (timestamp without time zone)

TABLE: income
  - income_id (bigint, PK)
  - user_id (bigint, FK -> users.user_id)
  - type_income (text, not null)
  - amount (numeric(12,2), default 0, CHECK amount >= 0)
  - description (text)
  - created_at (timestamp without time zone)
  - updated_at (timestamp without time zone)

TABLE: goals
  - goal_id (bigint, PK)
  - user_id (bigint, FK -> users.user_id)
  - goal_name (text, not null)
  - description (text)
  - target (numeric(12,2), default 0, CHECK target >= 0)
  - start_date (date)
  - due_date (date)
  - status (text, default 'active')
  - created_at (timestamp without time zone)
  - updated_at (timestamp without time zone)

COMMON PATTERNS:
- Monthly spend by budget:
  SELECT b.budget_name, DATE_TRUNC('month', t.date) AS month, ROUND(SUM(t.amount)::numeric, 2) AS total_spent
  FROM transactions t JOIN budget b ON t.budget_id = b.budget_id
  WHERE t.user_id = $USER_ID GROUP BY b.budget_name, month ORDER BY month DESC

- Overspend detection:
  SELECT b.budget_name, ROUND(SUM(t.amount)::numeric, 2) AS spent, b.total_limit,
  ROUND(100.0 * SUM(t.amount) / NULLIF(b.total_limit, 0), 2) AS pct_of_limit
  FROM transactions t JOIN budget b ON t.budget_id = b.budget_id
  WHERE t.user_id = $USER_ID AND DATE_TRUNC('month', t.date) = DATE_TRUNC('month', CURRENT_DATE)
  GROUP BY b.budget_name, b.total_limit ORDER BY pct_of_limit DESC
=======
Grouping and Ranking (SQLite-safe):
    - For "most frequent", "top", or "highest" results:
        * Always compute aggregates with GROUP BY.
        * Then restrict results to ONLY the maximum value(s) per group.
        * If multiple results tie for maximum, return all of them.
    - Never just use ORDER BY to imply "top".
    - In SQLite, enforce this with:
        * Subquery + MAX() joined back to the grouped results (always works), OR
        * Window functions (RANK, ROW_NUMBER, DENSE_RANK) if supported.
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

prompt = ChatPromptTemplate.from_messages([
    ("user", system_prompt),
    ("user", metadata),
    ("user", "{request}, user_id: {user}"),
])

DatabaseAgent = prompt | azure_llm.with_structured_output(DatabaseAgentOutput)