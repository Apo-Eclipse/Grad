from langchain_gradient import ChatGradient
import os

gpt_oss_120b_digital_ocean = ChatGradient(
    model="openai-gpt-oss-120b",
    api_key=os.getenv("DIGITALOCEAN_INFERENCE_KEY_GPT_120B"),
    max_completion_tokens=4096,
    temperature=0.4,
)

# gpt5_mini_digital_ocean = ChatGradient(
#     model="openai-gpt-5-mini",
#     api_key=os.getenv("DIGITALOCEAN_INFERENCE_KEY_GPT_5_MINI")
# )

# gpt5_digital_ocean = ChatGradient(
#     model="openai-gpt-5",
#     api_key=os.getenv("DIGITALOCEAN_INFERENCE_KEY_GPT_5")
# )