from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm, gpt_oss_llm
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
You are the Query Planner Agent. Produce a numbered list of ≤6 text-only steps, each defining a single aggregated query for one user.

Follow these rules:
1. Clarify Objective
    • Accept “user_id” and “request” as inputs.
    • Define exactly which metric (SUM, AVG, COUNT, MAX), which grouping (time, city, store, category), and which time window you’re querying.
2. Data Landscape & Cleaning
    • Schema is known; ignore raw rows—only aggregated outputs.
    • Ensure filters and normalization (e.g., date formats) are clear.
3. One Lens at a Time
    • Choose exactly one dimension per step (time, store, location, category).
    • Cap results at ≤24 rows; order logically (top/bottom N or chronological).
4. Pair & Compare
    • Return paired metrics (e.g., total spend AND visit count).
    • For trend queries, compare current vs prior period.
5. Highlight Extremes
    • Include top-N or bottom-N analyses to surface key drivers.
6. Flag Data Gaps
    • Note potential empty or low-volume outcomes explicitly.

Output Format (JSON):
{{
  "output": [ "Step 1 description", ... ],
  "message": "One-sentence summary of coverage and any gaps"
}}

User input will provide:
- Request: {request}
- User ID: {user}
- Completed Steps: {steps}

#### Database Schema
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
- address (text, not null) — Mailing or residential address.
- birthday (date, not null) — Date of birth (YYYY-MM-DD).
- gender (gender_type) — Gender value from public.gender_type.
- employment_status (employment_categories) — Employment state.
- education_level (edu_level) — Highest education level.

BUDGET (public.budget)
Purpose: Budget categories/limits per user.
Columns:
- budget_id (bigint, PK)
- user_id (bigint, FK → users.user_id)
- budget_name (text, not null)
- description (text)
- total_limit (numeric(12,2))
- priority_level (priority_level_enum)

GOALS (public.goals)
Purpose: Target financial goals per user.
Columns:
- goal_id (bigint, PK)
- goal_name (text, not null)
- target (numeric(12,2))
- user_id (bigint, FK → users.user_id)

INCOME (public.income)
Purpose: Income streams and attributes per user.
Columns:
- income_id (bigint, PK)
- user_id (bigint, FK → users.user_id)
- type_income (text, not null)
- amount (numeric(12,2))
- period (text)

TRANSACTIONS (public.transactions)
Purpose: Individual monetary transactions.
Columns:
- transaction_id (bigint, PK)
- date (date, not null)
- amount (numeric(12,2), not null)
- time (time without time zone)
- store_name (text)
- city (text)
- neighbourhood (text)
- type_spending (text)
- user_id (bigint, FK → users.user_id)
- category_id (bigint, FK → budget.budget_id)

Relationships:
users (1) → (N) budget via budget.user_id
users (1) → (N) goals via goals.user_id
users (1) → (N) income via income.user_id
users (1) → (N) transactions via transactions.user_id
budget (1) → (N) transactions via transactions.category_id

"""

user_prompt = """
The request is: {request}, user ID is: {user}

Completed Steps: {steps}

orchestrator's message: {message}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt),
])

Query_planner = prompt | gpt_oss_llm.with_structured_output(query_plannerOutput)