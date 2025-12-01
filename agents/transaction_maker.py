from LLMs.azure_models import gpt_oss_llm
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
    is_done: bool = Field(
        False,
        description="True if all necessary details (amount, category/budget_id) are present and confirmed."
    )


system_prompt = r"""
You are the Transaction Maker Agent. Your job is to help the user record a new financial transaction from natural language.

OUTPUT FORMAT:
Return a JSON object matching:
{{
  "message": "...",
  "amount": 150.0,
  "budget_id": 12,
  "store_name": "Walmart",
  "date": "2024-01-01",
  "is_done": true
}}

CONTEXT PROVIDED:
- "active_budgets": A list of active budgets with their IDs (e.g., "Food (ID: 1)", "Transport (ID: 2)").
- "current_date": Today's date.
- "user_request": The user's input.

RULES:
1. **Extract Details**: Look for Amount, Category, Store, and Date.
   - If Date is missing, assume "current_date".
   - If Store is missing, leave null.
2. **Map Category to Budget ID**:
   - Compare the user's category (e.g., "groceries") to the "active_budgets" list.
   - If a match is found (e.g., "Food"), set "budget_id" to that ID.
   - If NO match is found, set "budget_id" to null and ASK the user if they want to proceed without a category or select one from the list.
3. **Validation**:
   - **Amount is MANDATORY**. If missing, ask for it.
   - **Category is Recommended**. If missing/invalid, warn/ask as above.
4. **Confirmation**:
   - If Amount and Budget ID are found (or user confirmed no category), set "is_done": true.
   - In the "message", confirm what will be added: "Adding 50 EGP for Food..."

EXAMPLES:
- User: "Spent 50 on food" (Active: Food ID 1)
  -> {{"message": "Recorded 50 EGP for Food.", "amount": 50, "budget_id": 1, "is_done": true}}

- User: "Spent 100"
  -> {{"message": "What was this 100 EGP for?", "amount": 100, "is_done": false}}

- User: "Spent 50 on Gaming" (No Gaming budget)
  -> {{"message": "'Gaming' isn't in your budgets. Available: Food, Transport. Proceed without category?", "amount": 50, "budget_id": null, "is_done": false}}
"""

user_prompt = """
active_budgets: {active_budgets}
current_date: {current_date}
user_request: {user_request}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt),
])

Transaction_maker_agent = prompt | gpt_oss_llm.with_structured_output(TransactionMakerOutput)
