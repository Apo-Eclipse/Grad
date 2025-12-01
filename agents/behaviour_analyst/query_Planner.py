from typing import List
from LLMs.azure_models import gpt_oss_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class query_plannerOutput(BaseModel):
    output: List[str] = Field(
        ...,
        description="A list (≤6) of clear, text-only steps for another database agent to create aggregated SQL queries about a single user's behavior."
    )
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
"""

user_prompt = """
Current Date: {current_date}
Request: {request}
User ID: {user}

last steps generated: {steps}

Orchestrator request: {message}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt),
])

Query_planner = prompt | gpt_oss_llm.with_structured_output(query_plannerOutput)