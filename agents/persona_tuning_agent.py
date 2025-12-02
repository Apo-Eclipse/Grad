import sys
from pathlib import Path

# Ensure project root is on sys.path so sibling packages (like `LLMs`) can be
# imported when this file is executed directly (e.g. `python agents/persona_tuning_agent.py`).
# ----------------for testing--------------------
# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# if str(PROJECT_ROOT) not in sys.path:
#   sys.path.insert(0, str(PROJECT_ROOT))
# from dotenv import load_dotenv

# load_dotenv()
#---------------------------------------------------
from LLMs.azure_models import gpt_oss_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
import datetime

# 1. Get the current date (CRITICAL for memory freshness)
today_str = datetime.date.today().isoformat()

# --- 1. The "Why" (Financial Psychology) ---
class MoneyPsychology(BaseModel):
    money_script: Literal['money_avoidance', 'money_worship', 'money_status', 'money_vigilance'] = Field(
        ...,
        description=(
            "The user's unconscious beliefs about money (Klontz scripts): "
            "1. 'Avoidance': Believes money is bad/anxious, ignores statements, feels guilty having money. "
            "2. 'Worship': Believes money solves all problems, chases windfalls, never feels they have enough. "
            "3. 'Status': Equates net worth with self-worth, spends to impress, hides debt. "
            "4. 'Vigilance': Anxious/watchful, frugal, saves secretly, fears ruin, pays cash."
        )
    )
    spending_trigger: Optional[Literal['emotional_stress', 'social_pressure', 'boredom', 'scarcity_panic', 'necessity_only']] = Field(
        None,
        description=(
            "The primary psychological driver for non-essential spending: "
            "'emotional_stress' (Retail Therapy/coping mechanism), "
            "'social_pressure' (FOMO/Keeping up with peers), "
            "'boredom' (Dopamine seeking/scrolling shops), "
            "'scarcity_panic' (Buying because 'it might run out' or is on sale)."
        )
    )
    financial_anxiety_level: Literal['high', 'moderate', 'low'] = Field(
        ...,
        description=(
            "High: Expresses fear/panic about future, checks balance obsessively or avoids it entirely. "
            "Moderate: Concerned but rational; wants a plan. "
            "Low: Confident, perhaps over-confident; sleeps well despite market volatility."
        )
    )

# --- 2. The "How" (Investment & Risk) ---
class RiskProfile(BaseModel):
    risk_tolerance: Literal['conservative', 'moderate', 'aggressive'] = Field(
        ...,
        description=(
            "The PSYCHOLOGICAL willingness to lose money (The 'Sleep Test'). "
            "Conservative: Panics at 5% drop. Moderate: Accepts volatility for growth. Aggressive: Views 20% drops as buying opportunities."
        )
    )
    risk_capacity: Literal['low', 'high'] = Field(
        ...,
        description=(
            "The MATHEMATICAL ability to lose money without ruining their life. "
            "Low: Needs money <3 years (student, buying house soon, low income). "
            "High: Stable income, high savings, long timeline (can afford to wait for market recovery)."
        )
    )
    time_horizon: Literal['short_term', 'medium_term', 'long_term'] = Field(
        ...,
        description=(
            "When they need the liquidity: "
            "Short (<3 yrs, e.g., wedding/car). "
            "Medium (3-10 yrs, e.g., house downpayment). "
            "Long (10+ yrs, e.g., retirement/generational wealth)."
        )
    )

# --- 3. The "What" (Knowledge & Communication) ---
class FinancialLiteracy(BaseModel):
    knowledge_level: Literal['novice', 'intermediate', 'advanced'] = Field(
        ...,
        description=(
            "Novice: Confused by basic terms (APR, inflation, ETF). Needs simple analogies. "
            "Intermediate: Understands savings vs investing, 401k match. Needs guidance on strategy. "
            "Advanced: Discusses asset allocation, tax efficiency, derivatives. Wants debate, not education."
        )
    )
    nudge_preference: Literal['tough_love', 'gentle_encouragement', 'data_driven', 'gamified'] = Field(
        ...,
        description=(
            "How the user responds to behavior correction: "
            "Tough Love: 'Stop spending or you will go broke.' (Direct/Blunt). "
            "Gentle: 'It's okay, let's get back on track.' (Empathetic). "
            "Data Driven: 'You spent 15% more than average.' (Analytical). "
            "Gamified: 'Streak broken! Earn this badge by saving.' (Challenge-based)."
        )
    )


# 4. Define the structure of a single memory "atom"
class ContextItem(BaseModel):
    value: str = Field(..., description="The fact content (e.g. 'Wife is pregnant').")
    created_at: str = Field(..., description="ISO Date string (YYYY-MM-DD) of when this was learned.")
    expiry_hint: Optional[str] = Field(None, description="Optional. If the user implies a deadline (e.g. 'Until next March', 'Permanent', 'For the wedding').")



# --- The Main Financial Persona ---
class FinancialPersona(BaseModel):
    summary: str = Field(..., description="A 1-sentence behavioral summary focusing on their money mindset (e.g., 'Anxious saver who fears investing despite high capacity').")
    
    psychology: MoneyPsychology
    risk_profile: RiskProfile
    literacy: FinancialLiteracy
    
    recurring_struggles: List[str] = Field(..., description="Repeated behavioral obstacles (e.g., 'Ordering UberEats when stressed', 'Forgetting to pay bills').")

    interaction_guidelines: List[str] = Field(..., description="Instructional rules for the AI agent on how to speak to this specific user (e.g., 'Use bullet points', 'Avoid alarming language').")
    
    user_context: dict[str, ContextItem] = Field(
        default_factory=dict,
        description="Explicit user facts with timestamps."
    )




# 2. The System Prompt (Formatted as an f-string to inject the date)
system_prompt = f"""
You are an expert **Financial Behavioral Analyst & Memory Manager**. Your goal is to build a "Living Financial Profile" of a user to help them manage money better.

### GLOBAL CONTEXT
**Today's Date:** {today_str}

### YOUR GOAL
Compare the `[[CURRENT_PROFILE]]` with the `[[NEW_INTERACTION]]` to produce an `[[UPDATED_PROFILE]]`.

### UPDATE RULES
1. **Psychological Inference:** Look for behavioral cues.
    - *Money Avoidance:* "I hate looking at my bank balance", ignoring bills.
    - *Money Status:* "I need that car to look successful", spending for image.
    - *Money Worship:* "Money solves all problems", "I can't be happy until I'm rich."
    - *Money Vigilance:* "I save everything," excessive anxiety, secrecy.
2. **Risk Analysis:** Differentiate between *Tolerance* (willingness) and *Capacity* (ability).
    - Example: A student might be willing (High Tolerance) but broke (Low Capacity).
3. **Fact Extraction (User Context):**
    - If the user mentions a specific life fact (e.g., "My rent is $1200", "Baby due in May"), add it to `user_context`.
    - **Keys:** Use short `snake_case` keys (e.g., `rent_amount`, `baby_due_date`).
    - **Timestamps:** ALways use Today's Date ({today_str}) for `created_at`.
    - **Expiry:** If the fact is temporary (e.g. "I'm vegan for January"), add an `expiry_hint`.
4. **Conflict Resolution:** New information supersedes old. 
    - *Correction:* If user says "Actually, I paid that off", remove the debt from struggles.

### OUTPUT FORMAT
Return a **single valid JSON object** matching this schema exactly.

{{
  "summary": "1-sentence behavioral summary (e.g. 'Anxious saver who fears investing').",
  "psychology": {{
    "money_script": "money_avoidance | money_worship | money_status | money_vigilance",
    "spending_trigger": "emotional_stress | social_pressure | boredom | celebratory | necessity_only (or null)",
    "financial_anxiety_level": "high | moderate | low"
  }},
  "risk_profile": {{
    "risk_tolerance": "conservative | moderate | aggressive",
    "risk_capacity": "low | high",
    "time_horizon": "short_term | medium_term | long_term"
  }},
  "literacy": {{
    "knowledge_level": "novice | intermediate | advanced",
    "nudge_preference": "tough_love | gentle_encouragement | data_driven | gamified"
  }},
  "recurring_struggles": ["List of bad habits (e.g. 'UberEats daily')"],
  "user_context": {{
    "key_name_snake_case": {{
        "value": "The specific fact string",
        "created_at": "{today_str}",
        "expiry_hint": "String describing when this might be irrelevant, or null"
    }}
  }},
  "interaction_guidelines": [
    "List of specific instructions for the agent (e.g. 'Don't use jargon', 'Celebrate small wins')"
  ]
}}
"""

# 3. The User Message (Injecting the data)
user_message = """
    [[CURRENT_PROFILE]]
    {current_persona_json}

    [[NEW_INTERACTION]]
    {last_conversation_transcript}
"""


prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_message)
])

Persona_Tuning_agent = prompt | gpt_oss_llm.with_structured_output(Persona_Tuning)


# ---------------------------------------Test Case-------------------------------------------------
# old_user_data = {
#     "summary": "User is a junior developer learning web dev.",
#     "communication_style": "Encouraging and simple.",
#     "likes_and_interests": ["Javascript", "React"],
#     "dislikes_and_constraints": [],
#     "technical_facts": {"experience_level": "junior"},
#     "system_instructions": ["Explain concepts like I am 5."]
# }

# # 2. The chat that just happened (User gets annoyed)
# recent_chat = """
# Agent: Great job! Do you want me to explain how `useEffect` works in simple terms?
# User: Stop treating me like a kid. I actually have 5 years of backend experience, I'm just new to React. also, I'm switching this project to TypeScript, so no more plain JS examples, be concise.
# """

# new_persona = Persona_Tuning_agent.invoke({
#     "current_persona": old_user_data,
#     "last_conversation": recent_chat,
# })

# print(new_persona) 