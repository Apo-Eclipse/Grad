from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class DatabaseAgentOutput(BaseModel):
    query: str = Field(..., description="The corresponding SQL query")

system_prompt = """
You are a database_agent.
Your task is to translate a single natural language step into on SQL query.

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

Grouping and Ranking (SQLite-safe):
    - For "most frequent", "top", or "highest" results:
        * Always compute aggregates with GROUP BY.
        * Then restrict results to ONLY the maximum value(s) per group.
        * If multiple results tie for maximum, return all of them.
    - Never just use ORDER BY to imply "top".
    - In SQLite, enforce this with:
        * Subquery + MAX() joined back to the grouped results (always works), OR
        * Window functions (RANK, ROW_NUMBER, DENSE_RANK) if supported.
"""



metadata = """
PostgreSQL Database Metadata (with Column Descriptions)

Engine: PostgreSQL 18.0
Schema: public

ENUM TYPES
-----------
public.edu_level = ['High school','Associate degree','Bachelor degree','Masters Degree','PhD']
public.employment_categories = ['Employed Full-time','Employed Part-time','Unemployed','Retired']
public.gender_type = ['male','female']
public.priority_level_enum = ['High','Mid','Low']

TABLES
-------
USERS (public.users)
Purpose: Master record for each user/person.
Columns:
- user_id (bigint, PK) — Surrogate identifier for the user.
- first_name (text, not null) — Given name.
- last_name (text, not null) — Family name.
- job_title (text, not null) — Current job title or role.
- address (text, not null) — Mailing or residential address (free text).
- birthday (date, not null) — Date of birth (YYYY-MM-DD).
- gender (gender_type) — Gender value from public.gender_type.
- employment_status (employment_categories) — Employment state from public.employment_categories.
- education_level (edu_level) — Highest education level from public.edu_level.

BUDGET (public.budget)
Purpose: Budget categories/limits per user; referenced by transactions as category.
Columns:
- budget_id (bigint, PK, default seq public.budget_budget_id_seq) — Surrogate identifier for the budget.
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user of this budget.
- budget_name (text, not null) — Human-readable budget/category name.
- description (text) — Additional notes or purpose of the budget.
- total_limit (numeric(12,2)) — Spending cap for this budget (amount in account currency).
- priority_level (priority_level_enum) — Priority for the budget (High/Mid/Low).

GOALS (public.goals)
Purpose: Target financial goals per user.
Columns:
- goal_id (bigint, PK, default seq public.goals_goal_id_seq) — Surrogate identifier for the goal.
- goal_name (text, not null) — Name/label of the goal.
- description (text) — Notes or details about the goal.
- target (numeric(12,2)) — Target amount to reach (account currency).
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user for this goal.

INCOME (public.income)
Purpose: Income streams and attributes per user.
Columns:
- income_id (bigint, PK, default seq public.income_income_id_seq) — Surrogate identifier for the income row.
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user for this income.
- type_income (text, not null) — Type/source of income (e.g., salary, bonus, freelance).
- amount (numeric(12,2)) — Income amount per period (account currency).
- period (text) — Recurrence period descriptor (e.g., monthly, weekly, one-off).
- description (text) — Free-text notes for the income entry.

TRANSACTIONS (public.transactions)
Purpose: Individual monetary transactions.
Columns:
- transaction_id (bigint, PK, default seq public.transactions_transaction_id_seq) — Surrogate identifier for the transaction.
- date (date, not null) — Transaction posting/occurred date (YYYY-MM-DD).
- amount (numeric(12,2), not null) — Transaction amount (account currency; positive for spend unless business rules differ).
- time (time without time zone) — Transaction time of day if available (HH:MM:SS).
- store_name (text) — Merchant or payee name.
- city (text) — Merchant location or free-text place string.
- neighbourhood (text) — Free-form neighbourhood or district name.
- type_spending (text) — Free-form subcategory/type (e.g., groceries, transport).
- user_id (bigint, FK → users.user_id, NOT VALID) — User associated with this transaction.
- category_id (bigint, FK → budget.budget_id, default seq public.transactions_category_id_seq, NOT VALID) — Budget/category reference for this transaction (should not auto-increment; consider removing default).

RELATIONSHIPS
--------------
users (1) → (N) budget via budget.user_id
users (1) → (N) goals via goals.user_id
users (1) → (N) income via income.user_id
users (1) → (N) transactions via transactions.user_id
budget (1) → (N) transactions via transactions.category_id → budget.budget_id

request: {request}/n
user_id: {user}
"""

prompt = ChatPromptTemplate.from_messages([
    ("user", system_prompt),
    ("user", metadata)
])

DatabaseAgent = prompt | azure_llm.with_structured_output(DatabaseAgentOutput)