"""Django Ninja API configuration."""

from ninja import NinjaAPI

from features.budget_maker.endpoints import router as budget_router
from features.crud.conversations.endpoints import router as conversations_router
from features.crud.analytics.endpoints import router as db_analytics_router
from features.crud.budgets.endpoints import router as db_budgets_router
from features.crud.goals.endpoints import router as db_goals_router
from features.crud.income.endpoints import router as db_income_router
from features.crud.transactions.endpoints import router as db_transactions_router
from features.crud.users.endpoints import router as db_users_router
from features.goal_maker.endpoints import router as goal_router
from features.orchestrator.endpoints import router as orchestrator_router
from features.transaction_maker.endpoints import router as transaction_router

# Create the main API instance
api = NinjaAPI(
    title="Personal Assistant API",
    version="1.0.0",
    description="Multi-Agent Personal Financial Assistant API",
)

# Register routers
api.add_router("/personal_assistant", orchestrator_router, tags=["Personal Assistant"])
# api.add_router(
#     "/personal_assistant/conversations", conversations_router, tags=["Conversations"]
# )
api.add_router("/personal_assistant/budget", budget_router, tags=["Budget Maker"])
api.add_router("/personal_assistant/goals", goal_router, tags=["Goal Maker"])
api.add_router(
    "/personal_assistant/transaction", transaction_router, tags=["Transaction Maker"]
)
api.add_router(
    "/database/transactions", db_transactions_router, tags=["Database - Transactions"]
)
api.add_router("/database/budgets", db_budgets_router, tags=["Database - Budgets"])
api.add_router("/database/goals", db_goals_router, tags=["Database - Goals"])
api.add_router("/database/income", db_income_router, tags=["Database - Income"])
api.add_router("/database/users", db_users_router, tags=["Database - Users"])
api.add_router(
    "/database/conversations",
    conversations_router,
    tags=["Database - Conversations"],
)
api.add_router(
    "/database/analytics", db_analytics_router, tags=["Database - Analytics"]
)
