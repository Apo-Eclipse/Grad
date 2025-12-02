from ninja import Router
from personal_assistant_api.assistants.schemas import AnalysisRequestSchema, AnalysisResponseSchema
from personal_assistant_api.assistants.services import PersonalAssistantService
from personal_assistant_api.core.responses import success_response, error_response

router = Router()
service = PersonalAssistantService()

@router.post("/analyze", response=AnalysisResponseSchema)
def analyze_behavior(request, payload: AnalysisRequestSchema):
    try:
        result = service.analyze_behavior(payload.user_id, payload.user_prompt, payload.current_date)
        return {"response": str(result), "data": None}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "data": None}

@router.get("/health")
def health_check(request):
    return success_response(service.get_health())
