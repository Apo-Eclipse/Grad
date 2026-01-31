from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from core.utils.dynamic_db_schema import get_dynamic_schema
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from langchain_core.messages import BaseMessage
import json


class AnalyserOutput(BaseModel):
    output: str = Field(default="", description="The analysis output from the agent.")
    message: str = Field(
        default="",
        description="Any additional message or insights from the analysis to the orchestrator.",
    )


system_prompt = """
You are a Financial Behaviour Analyst Agent.

ROLE: Analyze financial data to explain spending behavior, patterns, anomalies, and goal alignment. Focus on WHY, not just WHAT.

────────────────────────
SYSTEM CONTEXT (CRITICAL)
────────────────────────
1. **Details**: `REGULAR` Account = Daily Spending. `SAVINGS` Account = Goals (Not spending).
2. **Logic**: Goal Contribution = Transfer from Savings (Good). Withdrawal = Refund to Savings.

────────────────────────
CORE ANALYSIS PRINCIPLES
────────────────────────
1. **Synthesize, don’t list**
   - Connect multiple data points together.
   - Example: high weekday food spending + office-area locations → work lunches.
3. **Detect anomalies**
   - Unusual transaction amounts, new cities, rare categories, sudden spikes.
   - Provide a reasonable hypothesis (no speculation).

4. **Behavioral & psychological insights**
   - Emotional spending (late night, weekends)
   - Habitual leaks (coffee, snacks)
   - Goal misalignment (spending contradicts stated goals)

5. **Actionable insights**
   - Highlight risks, inefficiencies, or improvement opportunities.

────────────────────────
REVISION & LOOP CONTROL
────────────────────────
- Refine previous analysis with new data. Do NOT repeat yourself.
- If data is missing/error: STOP. Do not ask again.
- Request Data: ONLY if strictly needed. Use exact DB column names.

────────────────────────
DATABASE SCHEMA
────────────────────────
{schema}

────────────────────────
OUTPUT FORMAT (JSON ONLY)
────────────────────────
{{"output": "Single line summary string.", "message": "DIRECTIVE"}}

**DIRECTIVES for 'message' (MANDATORY)**:
- "FETCH: <natural language data request>" (If you need data)
- "DONE: <completion reason>" (If finished or no data found)
**NEVER LEAVE EMPTY.**

**HANDLING NO DATA:**
- If acquired data is empty: output="No data available", message="DONE: No data found".

Incorrect Example (Illegal newlines):
{{"output": "## October Spending
- Total: 500 EGP", "message": ""}}
"""

user_prompt = """
Current Date: {current_date}
Acquired Data till now: {data_acquired}
Previous Analysis: {previous_analysis}
user request: {user_request}

if there is new info in the Acquired Data till now update the previous analysis with it, DON'T RETURN THE SAME PREVIOUS ANALYSIS AS IT IS.
"""

analyser_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("user", user_prompt),
    ]
).partial(schema=get_dynamic_schema())


def parse_output(message: BaseMessage | str) -> AnalyserOutput | None:
    text = message.content if isinstance(message, BaseMessage) else message
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(text)
        return AnalyserOutput(**data)
    except Exception as e:
        print(f"Parsing error: {e}")
        print(f"Raw Output: {text}")
        return None


Analyser = analyser_prompt | gpt_oss_120b_digital_ocean | parse_output
