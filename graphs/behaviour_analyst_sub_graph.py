<<<<<<< HEAD
<<<<<<< HEAD
import asyncio
import ast
import logging
import warnings
from datetime import datetime
from typing import TypedDict, List

from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner, ValidationAgent
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
=======
from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
=======
from agents import Explainer_agent, Analyser, Behaviour_analyser_orchestrator, Query_planner
from graphs.database_sub_graph import database_agent_super_agent
from langgraph.graph import StateGraph, END, START
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
from langgraph.types import Command
from typing import TypedDict
import ast
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import logging
<<<<<<< HEAD
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
=======
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20

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
    current_date: str       # Current date for context

def analyser(state: BehaviourAnalystState):
    print("===> Analyser Invoked <===")
    data_acquired = state.get("data_acquired", [])
    request = state.get("request", "")
    message = state.get("message", "")
    analysis = state.get("analysis", "")
    
    Output = Analyser.invoke({
        "data_acquired": data_acquired,
        "message": message,
        "user_request": request,
        "previous_analysis": analysis,
        "current_date": datetime.now().strftime("%Y-%m-%d")
    })
    
    analysis = Output.output
    message = Output.message
    print("Analysis: ", analysis)
    add_to_logs("analyser", "orchestrator", message)
    return {"analysis": analysis, "message": message, "sender": "analyser", "analysis": analysis}

<<<<<<< HEAD
<<<<<<< HEAD
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
        "user_id": state.get("user_id", ""),
        "steps": state.get("steps", []),
        "current_date": datetime.now().strftime("%Y-%m-%d")
    })
    next_step = Output.next_step
    message = Output.message
    print(f"Orchestrator message to {next_step}: {message}")
    return {"message": message, "sender": "orchestrator", "next_step": next_step, "user_id": state.get("user_id", "")}

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
        "user": state.get("user_id", ""),
        "current_date": datetime.now().strftime("%Y-%m-%d")
    })
    
    message = Output.message
    steps = Output.output
    
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
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


<<<<<<< HEAD
<<<<<<< HEAD
    # Create a list of async tasks for the database agent subgraph
    tasks = [database_agent_super_agent.ainvoke({"request": step, "user_id": state.get("user_id")}) for step in steps]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results to extract the necessary data payload
    processed_results = [db_state.get("result", {}) if not isinstance(db_state, Exception) else {"error": str(db_state)} for db_state in results]
    curr_message = f"Executed {len(processed_results)} DB queries in parallel."
    print(curr_message)
    message = state.get("sender", "") + ": " + state.get("message", "")
    return {"db_results": processed_results, "sender": "db_agent", "message": message+ "\n" + "Database agent: "+ curr_message, "user_id": state.get("user_id", "")}

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
    
    validation_feedback = state.get("validation_results", [])
    tasks = []
    items_for_llm = []
    fallback_validation_tasks = []

    for idx, db_result in enumerate(db_results_to_explain):
        if not isinstance(db_result, dict) or not db_result:
            continue

        feedback = validation_feedback[idx] if idx < len(validation_feedback) else None
        if feedback:
            past_explanation, problem = feedback
        else:
            past_explanation, problem = "No Past Explanation", "No Problems because there is no past explainantion"

        if db_result.get("error"):
            explanation = f"Database error: {db_result['error']}"
            data_acquired.append(explanation)
            fallback_validation_tasks.append({
                "db_result": db_result,
                "explanation": explanation
            })
            continue

        step = db_result.get("step", "no step provided")
        table = db_result.get("data", "no data provided")
        request_text = f"The request was: {step}\n\nThe result was: {table}\n"

        ainvoke_payload = {
            "request": request_text,
            "previous_analysis": past_explanation,
            "problems": problem
        }

        tasks.append(Explainer_agent.ainvoke(ainvoke_payload))
        items_for_llm.append((db_result, past_explanation, problem))
        
    ex_outputs = []
    if tasks:
        ex_outputs = await asyncio.gather(*tasks, return_exceptions=True)

    new_validation_tasks = list(fallback_validation_tasks)
    for (db_result, _, _), ex_out in zip(items_for_llm, ex_outputs):
        if isinstance(ex_out, Exception):
            explanation = "Could not generate explanation"
        else:
            explanation = getattr(ex_out, "explanation", "Could not get an explanation.")

        data_acquired.append(explanation)
        new_validation_tasks.append({
            "db_result": db_result,
            "explanation": explanation
        })
            
    curr_message = f"Generated {len(db_results_to_explain)} new explanations."

    print(curr_message)
    
    message = state.get("message", "")
    
    return {
        "data_acquired": data_acquired, # This now contains both old valid and new explanations
        "validation_tasks": new_validation_tasks,
        "sender": "explainer",
        "message": message + "\n" + "Explainer: " + curr_message,
        "user_id": state.get("user_id", "")
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

    # Update the state for the next step in the graph
    return {
        "data_acquired": clean_data_acquired,
        "db_results": db_results_for_correction, # This list will be sent back to the explainer
        "validation_results": past_explanations_and_reasoning,
        "sender": "validation",
        "message": message + "\n" + "Validation: " + validation,
        "user_id": state.get("user_id", "")
    }

# --- Build the Graph ---
=======
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
=======
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
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
        ex_out += "\n\n" + "The explanation was: " + str(explanation) + "\n"
    except Exception:
        ex_out += "\n\n" + "Could not get explanation"
    return data_to_written,data_acquired
<<<<<<< HEAD
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
=======
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20

builder = StateGraph(BehaviourAnalystState)
builder.add_node("analyser", analyser)
builder.add_node("orchestrator", orchestrator)
builder.add_node("query_planner", query_planner)

builder.add_edge(START, "orchestrator")
builder.add_edge("orchestrator", END)

builder.add_edge("query_planner", "orchestrator")
builder.add_edge("analyser", "orchestrator")

<<<<<<< HEAD
<<<<<<< HEAD
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
    if random.random() < 0.40:
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
=======
behaviour_analyst_super_agent = builder.compile()
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
=======
behaviour_analyst_super_agent = builder.compile()
>>>>>>> c5cc8a00b674920893a03711ccfe2a7e80167f20
