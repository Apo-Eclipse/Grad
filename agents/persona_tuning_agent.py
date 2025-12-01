import sys
from pathlib import Path

# Ensure project root is on sys.path so sibling packages (like `LLMs`) can be
# imported when this file is executed directly (e.g. `python agents/persona_tuning_agent.py`).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv

load_dotenv()

from LLMs.azure_models import gpt_oss_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel



class Persona_Tuning(BaseModel):
    summary: str = Field(..., description="A 1-sentence high-level summary of who the user is.")
    communication_style: str = Field(..., description="String describing how they talk and how they want to be talked to.")
    likes_and_interests: list[str] = Field(..., description="List of strings representing the user's likes and interests.")
    dislikes_and_constraints: list[str] = Field(..., description="List of strings representing the user's dislikes and constraints.")
    technical_facts: dict[str, str] = Field(..., description="Dictionary of key-value pairs representing technical facts about the user.")
    system_instructions: list[str] = Field(..., description="List of explicit rules for the AI agent.")
    


system_prompt = """
You are an advanced **User Persona & Memory Manager**. Your job is to maintain a "Living Profile" of a user based on their interaction history.

### YOUR GOAL
Compare the `[[CURRENT_PROFILE]]` with the `[[NEW_INTERACTION]]` to produce an `[[UPDATED_PROFILE]]`.

### UPDATE RULES
1. **Conflict Resolution:** If the `[[NEW_INTERACTION]]` contradicts the `[[CURRENT_PROFILE]]`, the NEW information is the truth. Overwrite the old data. (e.g., if user previously liked Python but now says "I hate Python", remove Python from likes and add to dislikes).
2. **Persistence:** Keep existing information that was NOT contradicted or mentioned. Do not delete old facts just because they weren't mentioned today.
3. **Tone Analysis:** Analyze the user's sentence structure and word choice to update the `communication_style` (e.g., "Direct", "Verbose", "Academic", "Casual").
4. **Instruction Extraction:** If the user gives explicit meta-instructions (e.g., "Don't ask me verify questions"), add this to `system_instructions`.

### OUTPUT FORMAT
You must return a **single valid JSON object** matching this schema exactly. Do not include markdown formatting like ```json.

{{
  "summary": "A 1-sentence high-level summary of who the user is.",
  "communication_style": "String describing how they talk and how they want to be talked to.",
  "likes_and_interests": ["list", "of", "strings"],
  "dislikes_and_constraints": ["list", "of", "strings"],
  "technical_facts": {{
    "key": "value (e.g. 'coding_language': 'python')"
  }},
  "system_instructions": [
    "List of explicit rules for the AI agent (e.g. 'Always use metric units', 'Never apologize profusely')"
  ]
}}
"""
user_message = """
    [[CURRENT_PROFILE]]
    {current_persona}

    [[NEW_INTERACTION]]
    {last_conversation}
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