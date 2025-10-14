import asyncio
import ast
import csv
import logging
import warnings
from typing import TypedDict, List, Annotated
from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner, ValidationAgent
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
from operator import add
import itertools 

# --- Setup Logging and Warnings ---
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
logging.getLogger().setLevel(logging.ERROR)


class BehaviourAnalystState(TypedDict):
    request: str
    analysis: str
    message: str
    user: str
    sender: str
    validation_tasks: List[dict]
    data_acquired: List[str]
    validation_results: List[tuple]
    steps: List[str]          # To hold the plan from the query_planner
    db_results: List[dict]  # To hold the results from the db_agent
    next_step: str          # To control routing from the orchestrator


def add_to_logs(sender, receiver, message):
    """Appends a log entry to the CSV file."""
    with open(r"D:\projects\Multi-Agent System\data\logs.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([sender, receiver, str(message)])


# --- Graph Nodes ---

def analyser(state: BehaviourAnalystState) -> dict:
    """Node that analyzes the current state and acquired data."""
    print("===> (Node) Analyser Invoked <===")
    data_acquired = state.get("data_acquired", [])
    request = state.get("request", "")
    message = state.get("message", "")
    analysis = state.get("analysis", "")
    
    Output = Analyser.invoke({
        "data_acquired": data_acquired,
        "message": message,
        "user_request": request,
        "previous_analysis": analysis
    })
    
    analysis = Output.output
    message = Output.message
    print("Analysis: ", analysis)
    add_to_logs("analyser", "orchestrator", message)

    return {"analysis": analysis, "message": "Analyser: " + message, "sender": "analyser"}


def orchestrator(state: BehaviourAnalystState) -> dict:
    """
    The central router of the graph. It decides which node to call next
    based on the overall state.
    """
    message = state.get("message", [])
    
    print("===> (Node) Orchestrator Invoked <===")
    Output = Behaviour_analyser_orchestrator.invoke({
        "request": state.get("request", ""),
        "analysis": state.get("analysis", ""),
        "message": message,
        "data_acquired": state.get("data_acquired", []),
        "sender": state.get("sender", ""),
        "user": state.get("user", "")
    })
    next_step = Output.next_step
    message = Output.message
    print(f"Orchestrator message : {message}")
    add_to_logs("orchestrator", next_step, message)
    
    return {"message": message, "sender": "orchestrator", "next_step": next_step}


def query_planner(state: BehaviourAnalystState) -> dict:
    """
    Node that plans which database queries are needed to fulfill the request.
    """
    message = state.get("message", [])
    
    print("===> (Node) Query Planner Invoked <===")
    Output = Query_planner.invoke({
        "request": state.get("request", ""),
        "message": message,
        "steps": state.get("steps", "no completed steps yet"),
        "user": state.get("user", "")
    })
    
    message = Output.message
    steps_output = Output.output
    
    # Ensure steps are in list format
    if isinstance(steps_output, str):
        try:
            steps = ast.literal_eval(steps_output)
        except (ValueError, SyntaxError):
            steps = [steps_output]
    else:
        steps = steps_output
        
    print(f"Planned {len(steps)} DB queries.")
    add_to_logs("query_planner", "db_agent", message)
        
    return {"steps": steps, "sender": "query_planner", "message": message}


async def db_agent(state: BehaviourAnalystState) -> dict:
    """
    Async node that executes all planned database queries in parallel.
    """
    print("===> (Node) Database Agent Invoked <===")
    steps = state.get("steps", [])
    if not steps:
        return {"db_results": [], "sender": "db_agent"}

    # Create a list of async tasks for the database agent subgraph
    tasks = [database_agent_super_agent.ainvoke({"request": step}) for step in steps]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Process results to extract the necessary data payload
    processed_results = [db_state.get("result", {}) for db_state in results]
    
    
    curr_message = f"Executed {len(processed_results)} DB queries in parallel."
    print(curr_message)
    add_to_logs("db_agent", "explainer", curr_message)


    message = state.get("sender", "") + ": " + state.get("message", "")
    return {"db_results": processed_results, "sender": "db_agent", "message": message+ "\n" + "Database agent: "+ curr_message}


async def explainer(state: BehaviourAnalystState) -> dict:
    """
    Generates explanations and pairs them with the full db_result
    for validation and potential correction.
    """
    print("===> (Node) Explainer Invoked <===")
    db_results_to_explain = state.get("db_results", [])

    # IMPORTANT: Get existing valid data to append to it
    data_acquired = state.get("data_acquired", []).copy()
    
    if not db_results_to_explain:
        return { "sender": "explainer", "message": "No new database results to explain." }
    
    # 1. Fetch the entire list of feedback from the state.
    validation_feedback = state.get("validation_results", [])
    tasks = []
    for db_result, feedback in itertools.zip_longest(
        db_results_to_explain,
        validation_feedback
    ):
        # 3. Unpack the feedback tuple *inside* the loop for each item.
        if feedback:   
            past_explanation, problem = feedback
        else:
            past_explanation, problem = "No Past Explanation", "No Problems because there is no past explainantion"
        
        # Build the input dictionary
        step = db_result.get("step", "no step provided")
        table = db_result.get("data", "no data provided")
        request_text = f"The request was: {step}\n\nThe result was: {table}\n"
        
        ainvoke_payload = {
            "request": request_text,
            "previous_analysis": past_explanation,
            "problems": problem
        }
        
        # 4. Create the task with the correct, simple syntax.
        tasks.append(Explainer_agent.ainvoke(ainvoke_payload))
        
    # Use return_exceptions=True so a single LLM failure won't crash the whole graph
    ex_outputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    new_validation_tasks = []
    # Loop through the results that were just processed; handle exceptions per-task
    for db_result, ex_out in zip(db_results_to_explain, ex_outputs):
        explanation = getattr(ex_out, 'explanation', "Could not get an explanation.")
        
        if isinstance(ex_out, Exception):
            explanation = f"Could not generate explanation"
        data_acquired.append(explanation)
        validation_pair = {
            "db_result": db_result, 
            "explanation": explanation
        }
        new_validation_tasks.append(validation_pair)
            
    curr_message = f"Generated {len(db_results_to_explain)} new explanations."

    print(curr_message)

    add_to_logs("explainer", "validation/orchestrator", curr_message)
    
    message = state.get("message", "")
    
    return {
        "data_acquired": data_acquired, # This now contains both old valid and new explanations
        "validation_tasks": new_validation_tasks,
        "sender": "explainer",
        "message": message + "\n" + "Explainer: " + curr_message
    }


async def validation(state: BehaviourAnalystState) -> dict:
    """
    Validates explanations. If any fail, it separates the bad data
    and prepares the state for a correction loop.
    """
    print("===> (Node) Validation Invoked <===")
    tasks_to_validate = state.get("validation_tasks", [])
    user_query = state.get("request", "")
    
    if not tasks_to_validate:
        return {"sender": "validation", "message": "No tasks to validate."}
        
    validation_coroutines = [
        ValidationAgent.ainvoke({
            "user_query": user_query,
            "query_result": (task["db_result"]["data"]),
            "explanation": task["explanation"]
        }) for task in tasks_to_validate
    ]
    validation_results = await asyncio.gather(*validation_coroutines)
    
    # --- CORRECTION LOGIC ---
    passed_explanations = []
    db_results_for_correction = []
    past_explanations_and_reasoning = []

    # Separate passed explanations from those that need correction
    for task, result in zip(tasks_to_validate, validation_results):
        if result.valid:
            passed_explanations.append(task["explanation"])
        else:
            print(f"--- VALIDATION FAILED: Sending for correction. Reason: {result.reasoning}")
            # Add the original db_result object to the correction list
            db_results_for_correction.append(task["db_result"])
            past_explanations_and_reasoning.append((task["explanation"], result.reasoning))
    

    # The data_acquired list should now only contain explanations that have passed validation
    # We find this by taking the set difference
    all_explanations = set(state.get("data_acquired", []))
    failed_explanations = set(task["explanation"] for task, res in zip(tasks_to_validate, validation_results) if not res.valid)
    clean_data_acquired = list(all_explanations - failed_explanations)
    
    message = state.get("message", "")
    validation = f"Validation complete. {len(db_results_for_correction)} items failed and will be corrected."
    
    # print(message)
    add_to_logs("validation", "explainer/orchestrator", validation)

    # Update the state for the next step in the graph
    return {
        "data_acquired": clean_data_acquired,
        "db_results": db_results_for_correction, # This list will be sent back to the explainer
        "validation_results": past_explanations_and_reasoning,
        "sender": "validation",
        "message": message + "\n" + "Validation: " + validation
    }
    


# --- Build the Graph ---

builder = StateGraph(BehaviourAnalystState)

# all the nodes of the graph
builder.add_node("orchestrator", orchestrator)
builder.add_node("analyser", analyser)
builder.add_node("query_planner", query_planner)
builder.add_node("db_agent", db_agent)
builder.add_node("explainer", explainer)
builder.add_node("validation", validation)

builder.add_edge(START, "orchestrator")

# data acquisition flow
builder.add_edge("query_planner", "db_agent")
builder.add_edge("db_agent", "explainer")

# feedback loops back to the orchestrator
# builder.add_edge("explainer", "orchestrator")
builder.add_edge("analyser", "orchestrator")


# routing logic from the orchestrator
def route_from_orchestrator(state: BehaviourAnalystState):
    """Return the next node's name based on the orchestrator's decision."""
    return state.get("next_step", "end")

builder.add_conditional_edges(
    "orchestrator",
    route_from_orchestrator,
    {
        "query_planner": "query_planner",
        "analyser": "analyser",
        "end": END
    }
)


def decision_for_validation(state: BehaviourAnalystState):
    """Return the next node's name based on a probabilistic decision:
    15% chance to return 'audit', otherwise 'pass'."""
    import random
    if random.random() < 0.95:
        return "audit"
    return "pass"

builder.add_conditional_edges(
    "explainer",
    decision_for_validation,
    {
        "audit": "validation",
        "pass": "orchestrator",
    }
)


def route_after_validation(state: BehaviourAnalystState):
    """If there are items to correct, go back to explainer. Otherwise, continue."""
    if state.get("db_results"): # This list now only contains items for correction
        print("--- LOOPING BACK TO EXPLAINER FOR CORRECTION ---")
        return "correct"
    else:
        print("--- ALL ITEMS VALID, CONTINUING TO ORCHESTRATOR ---")
        return "continue"

builder.add_conditional_edges(
    "validation",
    route_after_validation,
    {"correct": "explainer", "continue": "orchestrator"}
)



behaviour_analyst_super_agent = builder.compile()