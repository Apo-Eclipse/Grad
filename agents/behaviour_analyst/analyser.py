from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class AnalyserOutput(BaseModel):
    output: str = Field(..., description="The analysis output from the agent.")
    message : str = Field(..., description="Any additional message or insights from the analysis to the orchestrator.")
    
system_prompt = """
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
        -   **Good Request:** "To understand the high 'Transport' spending, I need a breakdown of transactions by 'Store_Name' within that category."
        -   **Bad Request:** "I need more data."

    ### Strict Output Format
    You MUST respond with a single, valid JSON object. Do not add any text outside the JSON structure.
    {{
        "output": "<Your comprehensive, synthesized analysis narrative goes here.>",
        "message": "<Your concise message to the orchestrator. Either confirm completion or request specific new data.>"
    }}
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


Acquired Data till now: {data_acquired}/n
Previous Analysis: {previous_analysis}/n
user request: {user_request}

if there is new info in the Acquired Data till now update the previous analysis with it, DON'T RETURN THE SAME PREVIOUS ANALYSIS AS IT IS.
"""
analyser_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
])

Analyser = analyser_prompt | azure_llm.with_structured_output(AnalyserOutput)