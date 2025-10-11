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
    Your mission is to generate a step-by-step, text-only plan for a database agent.
    Each step must define a single, specific query to uncover insights about a single user's spending.

    ### Directives
    
    #### 1. Output Description
    - **List of Steps:** Each step must correspond to a single analytical query.
    - **Text Only:** Describe the query's goal in plain text. Do not write SQL code.
    - **Summary Message:** Conclude with a one-sentence message to the orchestrator summarizing your plan.

    #### 2. Content Focus
    - **Scope:** The entire plan must focus on a single user.
    - **Core Aspects:** Limit your analysis to **Time**, **Location**, **Store**, and **Category**.
    - **Dimensions:** For each aspect, generate steps for both **spending-based** insights (total, average, max spend) and **frequency-based** insights (visit counts).

    #### 3. Query Requirements
    - **No Raw Data:** Every step must request an **aggregated insight** (e.g., `SUM`, `AVG`, `COUNT`, `MAX`). Do not ask for raw transaction lists.
    - **Be Specific:** Avoid vague steps like "Analyze spending." Instead, specify the exact metric and grouping, such as "Calculate the total amount spent per store."
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

The request is: {request}, user ID is: {user}

orchestrator's message: {message}
old steps taken: {steps}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
])

Query_planner = prompt | azure_llm.with_structured_output(query_plannerOutput)