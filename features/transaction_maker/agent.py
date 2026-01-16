from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from typing import Optional


class TransactionMakerOutput(BaseModel):
    message: str = Field(
        ...,
        description="Natural language response to the user (confirmation, clarification question, or error)."
    )
    amount: Optional[float] = Field(None, description="The transaction amount.")
    budget_id: Optional[int] = Field(None, description="The ID of the matching budget category.")
    store_name: Optional[str] = Field(None, description="Name of the store or merchant.")
    date: Optional[str] = Field(None, description="Date of the transaction (ISO format YYYY-MM-DD).")
    time: Optional[str] = Field(None, description="Time of the transaction (HH:MM:SS).")
    city: Optional[str] = Field(None, description="City where the transaction occurred.")
    neighbourhood: Optional[str] = Field(None, description="Neighbourhood where the transaction occurred.")
    type_spending: Optional[str] = Field(None, description="The category name (e.g., 'Food').")
    is_done: bool = Field(
        False,
        description="True if mandatory details are present AND user has been given a chance to add optional details."
    )


system_prompt = r"""
You are the Transaction Maker Agent. Your job is to help the user record a new financial transaction from natural language.

OUTPUT FORMAT:
Return a SINGLE valid JSON object.

--------------------------------------------------
CRITICAL OUTPUT RULES
--------------------------------------------------
- Return ONLY valid JSON.
- Do NOT include markdown formatting (like ```json ... ```).
- Do NOT include literal newlines in strings. Use \n if needed.
- Use double quotes for all keys and string values.
- Do NOT add comments or explanations outside the JSON.
--------------------------------------------------

Example match:
{{
  "message": "...",
  "amount": 150.0,
  "budget_id": 12,
  "store_name": "Walmart",
  "date": "2024-01-01",
  "time": "14:30:00",
  "city": "Cairo",
  "neighbourhood": "Zamalek",
  "type_spending": "Food",
  "is_done": true
}}

CONTEXT PROVIDED:
- "active_budgets": A list of active budgets with their IDs (e.g., "Food (ID: 1)", "Transport (ID: 2)").
- "current_date": Today's date.
- "user_request": The user's input.
- "last_conversation": Previous messages in this session.

RULES:
1. **Extract Details**: Look for Amount, Category (type_spending), Store, Date, Time, City, and Neighbourhood.
   - If Date is missing, assume "current_date".
   - If Time/City/Neighbourhood/Store are missing, leave null initially.
2. **Map Category to Budget ID**:
   - Compare the user's category (e.g., "groceries") to the "active_budgets" list.
   - If a match is found (e.g., "Food"), set "budget_id" to that ID and "type_spending" to the budget name.
   - If NO match is found, set "budget_id" to null and ASK the user if they want to proceed without a category or select one from the list.
3. **Validation**:
   - **Amount is MANDATORY**. If missing, ask for it.
   - **Category is Recommended**. If missing/invalid, warn/ask as above.
4. **Optional Details Check**:
   - The user might not provide Time, City, or Neighbourhood.
   - **IF** these are missing AND you haven't asked about them in "last_conversation":
     - Ask: "Do you want to add details like time, city, or neighbourhood?"
     - Set `is_done: false`.
   - **IF** the user says "No", "Skip", or "That's all", OR if you see you already asked in history:
     - You can proceed. Set `is_done: true`.
5. **Confirmation**:
   - If Amount is set, Budget is handled, and Optional Check is satisfied:
   - Set "is_done": true.
   - In the "message", confirm what will be added: "Recording 50 EGP for Food at Walmart..."

EXAMPLES:
- User: "Spent 50 on food" (History: Empty)
  -> {{"message": "Recorded 50 EGP for Food. Any details to add (Time, City, Neighbourhood)?", "amount": 50, "budget_id": 1, "type_spending": "Food", "is_done": false}}

- User: "No details" (History: Agent asked about details)
  -> {{"message": "Done. Transaction saved.", "amount": 50, "budget_id": 1, "type_spending": "Food", "is_done": true}}

- User: "Spent 100 at Zara in Cairo"
  -> {{"message": "Recorded 100 EGP at Zara (Cairo). Category?", "amount": 100, "store_name": "Zara", "city": "Cairo", "is_done": false}}
"""

user_prompt = """
active_budgets: {active_budgets}
current_date: {current_date}
last_conversation: {last_conversation}
user_request: {user_request}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt),
])

import json
import re
from langchain_core.messages import BaseMessage

def parse_output(message: BaseMessage | str) -> TransactionMakerOutput | None:
    text = message.content if isinstance(message, BaseMessage) else message
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(text)
        return TransactionMakerOutput(**data)
    except Exception as e:
        print(f"Parsing error: {e}")
        print(f"Raw Output: {text}")
        return None

Transaction_maker_agent = prompt | gpt_oss_120b_digital_ocean | parse_output
