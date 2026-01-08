from typing import List,TypedDict
from pydantic import BaseModel
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate

CATEGORY_MAP = {
    "subjects": "Subjects",
    "companies": "Companies & Organizations", 
    "ai": "AI Models & Assistants",
    "frameworks": "Frameworks & Libraries",
    "languages": "Languages & Syntax",
    "concepts": "Concepts & Methods",
    "tools": "Tools & Services",
    "platforms": "Platforms & Search Engines",
    "hardware": "Hardware & Systems",
    "websites": "Websites & Applications",
    "people": "People",
    "bucket": "Bucket (other)",
}

class ProfileNotesResponse(TypedDict):
    personality: str
    major_categories: List[str]
    minor_categories: List[str]
    keywords: List[str]
    time_period: str
    concise_summaries: bool


PROMPT_PROFILE_NOTES = """
You are tasked with defining a user persona based on the user's profile summary.
Your job is to:
1. Pick a short personality description for the user.
2. Select the most relevant categories (major and minor).
3. Choose keywords the user should track, strictly following the rules below (max 6).
4. Decide on time period (based only on what the user asks for).
5. Decide whether the user prefers concise or detailed summaries.

---

Step 1. Personality
- Write a short description of how we should think about the user.
- Examples:
  - CMO for non-technical product → "non-technical, skip jargon, focus on product keywords."
  - CEO → "only include highly relevant keywords, no technical overload, straight to the point."
  - Developer → "technical, interested in detailed developer conversation and technical terms."

---

Step 2. Categories
Choose only from this catalog (use these exact keys in the output; explanations are just for guidance):

- companies → Companies & Organizations: Meta, Google, Tesla, OpenAI, Nvidia, etc.
- ai → AI Models & Assistants: ChatGPT, Claude, Llama, Gemini, Qwen, DeepSeek, Wan
- people → People: Elon Musk, Sam Altman, etc.
- platforms → Platforms & Search Engines: AWS, Azure, GCP, Docker, Kubernetes, GitHub, Hugging Face, Vercel, Replit
- websites → Websites & Applications: Reddit, YouTube, X/Twitter, Hacker News, LinkedIn, Discord, TikTok, App Store
- subjects → Subjects: AI, software development, open source, machine learning, cybersecurity, performance, China, US, EU, regulation, automation, data analysis, lawsuit, tariffs, privacy, security, job market, valuation, layoffs, inflation, etc.
- tools → Tools & Services: Copilot, Cursor, VS Code, ComfyUI, Terraform, Grafana, Airflow, Proxmox
- frameworks → Frameworks & Libraries: React, Next, Node, LangChain, LlamaIndex, PyTorch, TensorFlow, FastAPI, Django
- languages → Languages & Syntax: Python, JavaScript, TypeScript, Rust, Go, Java, SQL, C, C++
- hardware → Hardware & Systems: Linux, Windows, Android, MacOS, iPhone, iOS, Debian, Raspberry Pi, etc.
- concepts → Concepts & Methods: Large Language Models, GPU, API, AGI, RAG, RAM, Loras, embeddings, fine tuning, prompts, algorithms, microservices, etc.

---

Step 2a. To help you pick categories:

Non-technical
- investor → major: companies, subjects, minor: people, ai
- general manager → major: companies, subjects, minor: people, ai
- designer → major: subjects, companies, minor: websites, ai
- product marketer/manager → major: tools, platforms, minor: websites, subjects, ai
- marketing manager (non-technical product) → major: ai, subjects, minor: websites
- CxO → major: companies, subjects, minor: people
- sales → major: companies, subjects, minor: people, websites

Semi-technical
- marketing manager (technical product) → major: tools, platforms, minor: ai, subjects
- product manager → major: tools, platforms, concepts, minor: ai, subjects
- product marketing manager (technical products) → major: tools, platforms, concepts, minor: ai, subjects
- technical product manager → major: tools, platforms, concepts, minor: ai, subjects
- technical product marketer → major: tools, platforms, concepts, minor: ai, subjects

Technical
- frontend developer → major: frameworks, tools, platforms, minor: subjects
- backend developer → major: frameworks, tools, platforms, minor: subjects, concepts
- devops → major: platforms, concepts, tools, minor: hardware, frameworks
- it technician → major: hardware, concepts, minor: platforms

Other
- data scientist → major: ai, concepts, minor: tools, platforms, subjects
- security engineer → major: concepts, platforms, minor: hardware
- researcher → major: ai, concepts, minor: subjects

---

Step 3. Keywords

Strict Priority Rules:
1. Always include user-provided keywords. Never ignore them or filter them out.
HOWEVER, please always:
1. If abbreviated or badly spelled, expand them (LLMs → Large Language Models) and make sure the spelling is correct (low code -> Low Code).
2. After including the user’s keywords, you may add a few additional ones based on their profile but the max keywords should never exceed 6.
3. Do not add vague or non-extractable terms like "Market Trends." Stick to concrete keywords people actually mention (e.g. Valuation, Layoffs, Job Market).
4. Use common sense:
   - Non-technical users → skip heavy jargon keywords unless specified.
   - Technical users → include relevant frameworks, platforms, and methods.
   - CFOs, investors, economists → you can include Valuation, Layoffs, Inflation, Costs, etc.
   - Designers → include Figma, Adobe, Canva, Generative Images.
   - AI engineers → include Agentic AI, Agents, RAG, Hugging Face.
   - Researchers → include Large Language Models, GPU, embeddings, Fine Tuning.

---

Step 4. Time Period
- Only use the time period the user explicitly asks for.
- If one is not provided, use weekly.

---

Step 5. Concise Summaries
- If the user profile suggests they want brevity (investor, CxO, manager) → concise_summaries: true.
- If they prefer detail (developer, researcher) → concise_summaries: false.

---

Output Format (JSON only)

{{
  "personality": "short description",
  "major_categories": ["one to three categories"],
  "minor_categories": ["one to three categories"],
  "keywords": ["3-6 keywords, always including user-provided ones"],
  "time_period": "daily | weekly | monthly | quarterly",
  "concise_summaries": true | false
}}
"""

HUMAN_PROFILE_MESSAGE = """
User Name: {name}
User Work and Interests: {interests}
User Provided Keywords (if any): {user_keywords}
User summary style prefered: {summary_style}
user time period preference (if any): {time_period}
"""
Prompt = ChatPromptTemplate.from_messages([
    ("system", PROMPT_PROFILE_NOTES),
    ("human", HUMAN_PROFILE_MESSAGE)
])


persona_llm = azure_llm.with_structured_output(ProfileNotesResponse)

persona_chain = Prompt | persona_llm 