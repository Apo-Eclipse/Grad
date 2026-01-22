from typing import List
from core.utils.dynamic_db_schema import get_dynamic_schema

from langchain_core.prompts import ChatPromptTemplate
from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from pydantic import Field, BaseModel
from langchain_core.messages import BaseMessage
import json


class query_plannerOutput(BaseModel):
    output: List[str] = Field(
        default=[],
        description="A list of no more than 4 clear, text-only steps for another database agent to create aggregated SQL queries about a single user's behavior.",
    )
    message: str = Field(
        default="",
        description="One concise sentence summarizing what the steps cover and any notable gaps.",
    )


system_prompt = """
You are the Query Planner Agent.
Produce a numbered list of no more than 4 short, text-only steps. Each step must describe ONE aggregated query for ONE user_id.

What a step MUST include (plain language, no SQL):
  • Metric: one aggregate (SUM | COUNT | AVG | MAX | MIN)
  • Dimension: choose exactly ONE lens (time | store_name | city | budget/category | type_spending)
  • Time window: explicit (e.g., current month, last 90 days, last 6 months)
  • Filters: must include user_id, and any request-specific filters
  • Output size: limit results to no more than 10 rows (e.g., “top 10”, “last 6 months”)
  • Ordering: logical order (chronological or top/bottom by metric)

General rules:
  1) Aggregations only (no raw row listings).
  2) One lens per step (no mixing multiple dimensions in one step).
  3) Avoid duplicates: consider steps done (already completed) and do not repeat them.
  4) Prefer comparisons when helpful (e.g., current vs prior period).
  5) If the request is vague, cover a compact baseline plan (trend, top category, overspend vs limit)

Available schema (key fields only; PostgreSQL 18, schema public):
{schema}

Output JSON format (STRICT):
Return ONLY valid JSON. 
1.Do not include explanations, comments, markdown, or trailing text.
2.The response must be a single JSON object and must parse with a standard JSON parser.
3.The "output" field must be a LIST of strings.
4.Each string in the list must be a single step.
5.DO NOT include newlines inside the steps.
6.DO NOT use Unicode line separators (u2028) or paragraph separators (u2029).
7.DO NOT include Markdown code blocks (```json ... ```).

Correct Example:
{{
  "message": "Brief plan explanation.",
  "output": [
    "1) Step one",
    "2) Step two"
  ]
}}

Incorrect Example (Illegal Markdown):
```json
{{
  "output": ...
}}
```

Notes:
- **CRITICAL:** Budget limits are **PER MONTH**. When checking overspending, ALWAYS aggregate transactions by month (e.g., "current month", "last month"). Never compare a yearly total against a monthly limit.
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

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("user", user_prompt),
    ]
).partial(schema=get_dynamic_schema())

def parse_output(message: BaseMessage | str) -> query_plannerOutput | None:
    text = message.content if isinstance(message, BaseMessage) else message
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(text)
        return query_plannerOutput(**data)
    except Exception as e:
        print(f"Parsing error: {e}")
        print(f"Raw Output: {text}")
        return None

Query_planner = prompt | gpt_oss_120b_digital_ocean | parse_output
