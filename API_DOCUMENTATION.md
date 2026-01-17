# API Documentation

**Base URL**: `http://localhost:8000/api`  
**Version**: 1.0.0  
**Auth**: Bearer Token (JWT) is required for all endpoints.

---

## 🔐 Authentication

### Login
**POST** `/auth/login`
Authenticates the user using email and password. Returns a pair of JWT tokens (access and refresh) for subsequent authenticated requests.

**Request Schema** (`LoginSchema`):
```json
{
  "email": "user@example.com",  // required
  "password": "strongpassword"   // required
}
```

**Response Schema** (`TokenSchema`):
```json
{
  "access": "eyJhbGCI...",
  "refresh": "eyJhbGCI...",
  "user_id": 1,
  "email": "user@example.com"
}
```

---

## 🤖 Personal Assistant (Chat Agents)

### General Analysis (Orchestrator)
**POST** `/personal_assistant/analyze`
The primary interaction point for the chat assistant. It analyzes the user's natural language `query` and routes it to the most appropriate internal agent (e.g., Database Agent for retrieval, Behaviour Analyst for insights, or Personal Assistant for general chat).

**Request Schema** (`AnalysisRequestSchema`):
```json
{
  "query": "How much did I spend on food?", // required
  "conversation_id": 12,                    // optional: maintains chat history context
  "filters": { "time_range": "last_30_days" }, // optional: pre-filter data
  "metadata": {}                            // optional
}
```

**Response Schema** (`AnalysisResponseSchema`):
```json
{
  "final_output": "You spent 500 EGP.",  // The text reply for the user
  "data": { ... },                       // optional: structured data (e.g. chart points)
  "conversation_id": 12
}
```

### Specialized Assistants
These endpoints bypass the general router to directly invoke specific tasks ("Makers").

#### 1. Budget Maker
**POST** `/personal_assistant/budget/assist`
Interactive agent for creating or modifying budgets. It parses a user's intent (e.g., "Set food budget to 500") and performs the necessary database actions.

**Request Schema** (`BudgetMakerRequestSchema`):
```json
{
  "user_request": "I want to create a food budget for 5000", // required
  "conversation_id": 10                                     // optional
}
```

**Response Schema** (`BudgetMakerResponseSchema`):
```json
{
  "conversation_id": 10,
  "message": "I've created your budget.",
  "action": "create",           // "create" or "update"
  "budget_name": "Food",        // optional
  "budget_id": 5,               // optional
  "total_limit": 5000.0,        // optional
  "is_done": true               // true if the task completed successfully
}
```

#### 2. Goal Maker
**POST** `/personal_assistant/goal/assist`
Interactive agent for setting financial goals. It helps guide the user to define a SMART goal (Specific, Measurable, Achievable, etc.).

**Request Schema** (`GoalMakerRequestSchema`):
```json
{
  "user_request": "I want to save for a vacation", // required
  "conversation_id": 10                            // optional
}
```

**Response Schema** (`GoalMakerResponseSchema`):
```json
{
  "conversation_id": 10,
  "message": "What is your target amount?",
  "goal_name": "Vacation",       // optional
  "target": 0.0,                 // optional
  "is_done": false               // false if more information is needed
}
```

#### 3. Transaction Maker
**POST** `/personal_assistant/transaction/assist`
Parses natural language input to log a new transaction (e.g., "Just spent 20 dollars on coffee").

**Request Schema** (`TransactionMakerRequestSchema`):
```json
{
  "user_request": "Spent 50 at Walmart on groceries", // required
  "conversation_id": 10                               // optional
}
```

**Response Schema** (`TransactionMakerResponseSchema`):
```json
{
  "conversation_id": 10,
  "message": "Transaction recorded.",
  "amount": 50.0,
  "is_done": true
}
```

---

## 🗄️ Database Resources (CRUD)

### Users
**POST** `/database/user/`
Registers a new user account and creates their associated profile.

**Request Schema** (`UserRegistrationSchema`):
```json
{
  "email": "user@example.com", // required
  "username": "user123",       // required
  "password": "password",      // required (min 8 chars)
  "first_name": "John",        // required
  "last_name": "Doe",          // required
  "job_title": "Engineer",     // optional
  "address": "123 Main St",    // optional
  "birthday": "1990-01-01",    // optional
  "gender": "male",            // optional
  "employment_status": "Employed Full-time", // optional
  "education_level": "Bachelor degree"       // optional
}
```

### Transactions
**POST** `/database/transaction/`
Creates a new single transaction record manually.

**Request Schema** (`TransactionCreateSchema`):
```json
{
  "date": "2023-10-27",      // required (YYYY-MM-DD)
  "amount": 50.00,           // required
  "store_name": "Store",     // optional
  "type_spending": "Food",   // optional
  "city": "Cairo",           // optional
  "neighbourhood": "Maadi",  // optional
  "budget_id": 1             // optional
}
```

**PUT** `/database/transaction/{id}`
Updates an existing transaction. Only fields provided in the body will be updated.

**Request Schema** (`TransactionUpdateSchema`):
*   All fields are optional, but at least one must be provided.
```json
{
  "amount": 60.00,
  "active": false
}
```

### Budgets
**POST** `/database/budget/`
Creates a new budget category (e.g., "Groceries", "Transport").

**Request Schema** (`BudgetCreateSchema`):
```json
{
  "budget_name": "Groceries", // required
  "total_limit": 500.00,      // required (default 0.0)
  "description": "Monthly",   // optional
  "priority_level_int": 1,    // optional
  "is_active": true           // optional (default true)
}
```

**PUT** `/database/budget/{id}`
Updates details of a budget, such as its name or spending limit.

**Request Schema** (`BudgetUpdateSchema`):
*   All fields are optional, but at least one must be provided.

### Goals
**POST** `/database/goal/`
Creates a new savings goal.

**Request Schema** (`GoalCreateSchema`):
```json
{
  "goal_name": "New Laptop", // required
  "target": 1500.00,         // required (default 0.0)
  "active": true,            // required (default true)
  "start_date": "2024-01-01",// optional
  "due_date": "2024-06-01",  // optional
  "plan": "Save 10% salary"  // optional
}
```

**PUT** `/database/goal/{id}`
Updates an existing goal's target, deadline, or status.

**Request Schema** (`GoalUpdateSchema`):
*   All fields are optional, but at least one must be provided.

### Income
**POST** `/database/income/`
Logs a new source of income.

**Request Schema** (`IncomeCreateSchema`):
```json
{
  "type_income": "Salary",   // required
  "amount": 3000.00,         // required
  "description": "Main job"  // optional
}
```

### Conversations
**POST / GET** `/database/conversation/start`
Initiates a new chat session. Returns the new conversation ID. Supports GET for easy testing (defaults to "web" channel).

**Request Schema** (`ConversationStartSchema`):
```json
{
  "channel": "web" // optional (default "web")
}
```

**Response Schema** (`ConversationResponseSchema`):
```json
{
  "conversation_id": 1,
  "user_id": 1,
  "channel": "web",
  "started_at": "2024-01-01T12:00:00Z"
}
```
