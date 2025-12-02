from ninja import Router
from personal_assistant_api.assistants.maker_schemas import MakerRequestSchema, MakerResponseSchema
from personal_assistant_api.assistants.helpers import get_user_summary, get_recent_conversations
from agents.transaction_maker import Transaction_maker_agent as TransactionMaker

router = Router()

@router.post("/assist", response=MakerResponseSchema)
def transaction_assist(request, payload: MakerRequestSchema):
    # Get context
    user_summary = get_user_summary(payload.user_id)
    recent_convs = get_recent_conversations(payload.user_id)
    
    # Invoke agent
    result = TransactionMaker.invoke({
        "request": payload.request,
        "user": str(payload.user_id),
        "current_date": payload.current_date,
        "context": {
            "user_summary": user_summary,
            "recent_conversations": recent_convs
        }
    })
    
    return {"response": str(result.get("output", result)), "status": "success"}
