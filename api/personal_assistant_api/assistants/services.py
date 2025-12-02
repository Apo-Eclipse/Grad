from agents.behaviour_analyst.orchestrator import Behaviour_analyser_orchestrator
from agents.personal_assistant.assistant import PersonalAssistant

class PersonalAssistantService:
    def __init__(self):
        self.orchestrator = Behaviour_analyser_orchestrator

    def analyze_behavior(self, user_id: int, user_prompt: str, current_date: str):
        # This is where the main orchestration logic happens
        # For now, we'll just call the orchestrator
        result = self.orchestrator.invoke({
            "user": str(user_id),
            "request": user_prompt,
            "current_date": current_date
        })
        return result

    def get_health(self):
        return {"status": "healthy", "service": "Personal Assistant"}
