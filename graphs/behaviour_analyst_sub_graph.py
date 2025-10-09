from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
from typing import TypedDict
import ast
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import logging

warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

logging.getLogger().setLevel(logging.ERROR)


class BehaviourAnalystState(TypedDict):
    request: str
    analysis: str
    message: str
    user: str
    sender: str
    data_acquired: list[str]
    
def add_to_logs(sender, receiver, message):
    with open("./data/logs.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([sender, receiver, message])


def analyser(state: BehaviourAnalystState):
    print("===> Analyser Invoked <===")
    data_acquired = state.get("data_acquired", [])
    request = state.get("request", "")
    message = state.get("message", "")
    analysis = state.get("analysis", "")
    Output = Analyser.invoke({"data_acquired": data_acquired, "message": message, "user_request": request, "previous_analysis": analysis})
    analysis = Output.output
    message = Output.message
    print("Analysis: ", analysis)
    add_to_logs("analyser", "orchestrator", message)
    return {"analysis": analysis, "message": message, "sender": "analyser", "analysis": analysis}

def orchestrator(state: BehaviourAnalystState):
    print("===> Orchestrator Invoked <===")
    request = state.get("request", "")
    analysis = state.get("analysis", "")
    data_acquired = state.get("data_acquired", [])
    message = state.get("message", "")
    sender = state.get("sender", "")
    Output = Behaviour_analyser_orchestrator.invoke({"request": request,
                                                    "analysis": analysis,
                                                    "message": message,
                                                    "data_acquired": data_acquired,
                                                    "sender": sender,
                                                    "user": state.get("user", "")})
    message = Output.message
    next_step = Output.next_step
    print("Next step: ", next_step)
    print("Message to {}: ".format(next_step), message)
    
    add_to_logs("orchestrator", next_step, message)
    return Command(update = {
            "data_acquired": data_acquired,
            "message": message, 
            "analysis": analysis,
            "user": state.get("user", ""),
            "request": request,
            "sender": "orchestrator"   
            },
            goto = next_step)

def query_planner(state: BehaviourAnalystState):
    print("===> Query Planner Invoked <===")
    request = state.get("request", "")
    message = state.get("message", "")
    data_acquired = state.get("data_acquired", [])
    Output = Query_planner.invoke({"request": request, "message": message, "data_acquired": data_acquired, "user": state.get("user", "")})
    message = Output.message
    steps = Output.output
    
    if isinstance(steps, str):
        try:
            steps = ast.literal_eval(steps)
        except Exception:
            steps = [steps]
    
    add_to_logs("query_planner", "orchestrator", message)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_step = {executor.submit(run_step, step): step for step in steps}
        for future in as_completed(future_to_step):
            step = future_to_step[future]
            try:
                print("===> Query Planner Invoked <===")
                data, result = future.result()
                print(data)
                data_acquired.extend(result)
            except Exception as exc:
                print(f'Step {step} generated an exception: {exc}')
    
    return {"data_acquired": data_acquired, "sender": "query_planner", "message": message}


def run_step(step):
    data_acquired = []
    db_state = database_agent_super_agent.invoke({"request": step})
    step = db_state.get("result", {}).get("step", "")
    query = db_state.get("result", {}).get("query", "")
    table = db_state.get("result", {}).get("data", [])
    data_to_written = "The request was: " + str(step) \
                        + "\n\n" + "The result was: " + str(table) + "\n"
    ex_out = Explainer_agent.invoke({"request": data_to_written})
    try:
        explanation = ex_out.explanation
        data_acquired.append(explanation)
        print("explanation: ", explanation)
    except Exception:
        print("Could not get explanation")
    return data_to_written,data_acquired

builder = StateGraph(BehaviourAnalystState)
builder.add_node("analyser", analyser)
builder.add_node("orchestrator", orchestrator)
builder.add_node("query_planner", query_planner)

builder.add_edge(START, "orchestrator")
builder.add_edge("orchestrator", END)

builder.add_edge("query_planner", "orchestrator")
builder.add_edge("analyser", "orchestrator")

behaviour_analyst_super_agent = builder.compile()