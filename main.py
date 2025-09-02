from graphs import presentation_super_agent,behaviour_analyst_super_agent, database_agent_super_agent
from IPython.display import Image, display
import json




def main():
    # final_state = presentation_super_agent.invoke({"insights": "This report analyzes the spending behavior of John Doe over the past six months. His average monthly income is $4,500, with average monthly savings of $800, representing 18% of his income. While he has maintained consistent savings, the trend shows a slight decline in the last two months, leaving savings a little below the recommended 20–30% benchmark. The breakdown of his monthly expenses shows housing and utilities as the largest share at $1,500 (33%), followed by food and dining at $900 (20%), transportation at $500 (11%), shopping and lifestyle at $700 (16%), entertainment and subscriptions at $400 (9%), healthcare and insurance at $300 (7%), and education and learning at $200 (4%). Overall, dining and lifestyle spending are above average compared to common benchmarks. In terms of trends, housing costs remain steady and predictable, transportation expenses are consistent, but dining costs have risen by 12% in the last quarter, largely from restaurants and takeout. Lifestyle spending has shown seasonal spikes, suggesting some impulsive behavior. Financial health indicators reveal strengths such as a stable income, regular saving habits, and no major debt repayments. However, risks exist in the form of higher-than-necessary discretionary spending, savings that could be improved, and signs of lifestyle creep where spending rises along with income. Recommendations for improvement include raising the savings rate to at least 25% by trimming dining and lifestyle expenses, setting a dining budget cap at $600 per month, monitoring impulse purchases more closely with tracking tools, automating savings to occur before discretionary spending, and exploring investment options such as index funds or retirement accounts to strengthen long-term wealth growth. In conclusion, John Doe displays generally responsible financial habits with controlled fixed costs and consistent saving, but his growing discretionary spending requires adjustments to secure stronger financial stability for the future."})
    # print("Presentation Super Agent execution completed.")
    # print("Final State:", final_state["final_output"])

    final_state = behaviour_analyst_super_agent.invoke({"final_output": "", "result": ""})
    # convert string to jarray
    jarray = final_state["result"]
    for j in jarray:
        print("Description: " + j['description'])
        print("Query: " + j['query'])
        print(j['result'])
        print("=====================================")

if __name__ == "__main__":
    main()