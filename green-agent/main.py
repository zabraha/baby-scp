from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import httpx
import uuid
import time
import os

app = FastAPI()

class Task(BaseModel):
    id: int
    task_id: str
    prompt: str = ""


TASKS = [
    Task(id=1,task_id="p1"),
    Task(id=2, task_id="p2"),
    Task(id=3, task_id="p3"),
    Task(id=4, task_id="p4"),
    Task(id=5, task_id="p5"),
]

async def call_purple_agent(purple_url: str, prompt: str):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send", 
        "params": {
            "message": {
                "kind": "message",
                "parts": [{"kind": "text", "text": prompt}]
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(purple_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", {})
            if "Message" in result:
                purple_text = result["Message"]["parts"][0]["text"]
            else:
                purple_text = "{}"
            
            print("Purple response: " + purple_text)
            return purple_text
    except Exception as e:
        print(f"Purple HTTP error: {e}")
        return f"Error: {e}"

 

async def green_agent_stream(request_payload):

    if request_payload.get("method") != "message/stream":
        yield f'data: {json.dumps({"jsonrpc": "2.0", "id": request_payload.get("id"), "error": {"code": -32601}})}\n\n'
        return
    
    # Extract from request
    params = request_payload.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])
    user_prompt = parts[0].get("text", "") if parts else ""
    
    # Parse participant config
    prompt_data = json.loads(user_prompt)
    purple_url = prompt_data.get("participants", {}).get("supply_chain_planning_agent")

    print("purple url: " + purple_url)
    
    if not purple_url:
        yield f'data: {json.dumps({"jsonrpc": "2.0", "id": request_payload["id"], "error": {"code": -32602}})}\n\n'
        return
    
    # Event 1: Task created
    # Generate IDs
    request_id = request_payload.get("id")
    task_id = str(uuid.uuid4())
    context_id = params.get("contextId")
    if not context_id:
        context_id = str(uuid.uuid4())
    #message_id = str(uuid.uuid4())
    
    print("request_id: " + request_id)
    print("task_id: " + task_id)
    print("contex_id: " + context_id)
 

    # --- PHASE 1: INIT ---
    # Note: 'id' here is the taskId, 'status' is the TaskStatus object
    yield f"data: {json.dumps({
        "jsonrpc": "2.0",
        "id": request_id, 
        "result": {
            "id": "task_3202b913",
            "contextId": context_id,
            "status": {"state": "working"}
        }
    })}\n\n"

    results = []
    passes = 0
    for i, task in enumerate(TASKS):

        msg = "Evaluating purple agent on problem: " + str(i) + " of: " + str(len(TASKS)) + " ..."

        # --- PHASE 2: MESSAGE ---
        yield f"data: {json.dumps({
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'taskId': task_id,
                'contextId': context_id,
                'event': 'TaskStatusUpdateEvent',
                'final': False,
                'status': {'state': 'working'},
                'message': {
                    'messageId': str(uuid.uuid4()),
                    'role': 'assistant',
                    'parts': [{'text': msg}]
                }
            }
        })}\n\n"

        start = time.time()
        task.prompt = generate(task.id)
        purple_response = await call_purple_agent(purple_url, task.prompt)
        #purple_response = "{}"
        success = score(task.id, purple_response)
        latency = time.time() - start
        if success: 
            passes += 1
        results.append({"task_id": task.task_id, "success": success, "latency": latency})

        # --- PHASE 2: MESSAGE ---
    yield f"data: {json.dumps({
        'jsonrpc': '2.0',
        'id': request_id,
        'result': {
            'taskId': task_id,
            'contextId': context_id,
            'event': 'TaskStatusUpdateEvent',
            'final': False,
            'status': {'state': 'working'},
            'message': {
                'messageId': str(uuid.uuid4()),
                'role': 'assistant',
                'parts': [{'text': 'Evaluating final response...'}]
            }
        }
    })}\n\n"

   
    eval_results = {}
    eval_results["pass_rate"] = passes/len(results)
    eval_results["total_tasks"] = len(TASKS)
    eval_results["results"] = results
    
    # --- PHASE 3: FINAL ---
    # --- Artifacts ---
    yield f"data: {json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "event": "TaskArtifactUpdateEvent",
            "taskId": task_id,
            "contextId": context_id,
            "final": False,
            "artifact": {
                "artifactId": f"results_{task_id}",
                "parts": [{"data": eval_results}],
            }
        }
    })}\n\n"

    # -- mark status as completed --
    yield f"data: {json.dumps({
        'jsonrpc': '2.0',
        'id': request_id,
        'result': {
            'taskId': task_id,
            'contextId': context_id,
            'event': 'TaskStatusUpdateEvent',
            'final': True,
            'status': {'state': 'completed'},
            'message': {
                'messageId': str(uuid.uuid4()),
                'role': 'assistant',
                'parts': [{'text': 'Task Completed Successfully'}]
            }
        }
    })}\n\n"

@app.post("/")
@app.post("/a2a/message")
async def handle_message(request: Request):        
    request_payload = await request.json()    
    return StreamingResponse(
        green_agent_stream(request_payload),
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/.well-known/agent-card.json")
async def agent_card():

    result =  {
        "schema_version": "v1",
        "version": "1.0.0",
        "name": "baby-supply-chain-planning-evaluator",
        "description": "AgentBeats green agent for a baby supply chain planning benchmark",
        "protocols": ["a2a"],
        "endpoints": {"message": "/a2a/message"},
        "tags": ["green", "evaluator", "supply chain planning"],
        "capabilities": {    
            "llm": True,
            "chat": True,
            "streaming": True
        },
        "defaultInputModes": ["text"],    # REQUIRED
        "defaultOutputModes": ["text"],   # REQUIRED
        "skills": [                        # REQUIRED
            {
                "id": "supply-chain-evaluator",
                "name": "Supply Chain Planning Evaluator",
                "description": "Evaluates baby supply chain planning solutions",
                 "tags": ["supply-chain", "evaluator", "planning"]  # REQUIRED
            }
        ],
    }
    # Conditionally add top-level url from env var if set
    card_url = os.getenv("CARD_URL")
    if card_url:
        result["url"] = card_url
    
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



with open("green-agent/data/schema/scp_problem.json", "r", encoding="utf-8") as f:
    scp_problem = json.load(f)   
scp_problem_schema_str = json.dumps(scp_problem)  

with open("green-agent/data/schema/scp_solution.json", "r", encoding="utf-8") as f:
    scp_solution = json.load(f)   
scp_solution_schema_str = json.dumps(scp_solution)  

prompt = f"""
The supply chain planning problem is represented as a property graph using nodes, edges and demands using the following json schema

{scp_problem_schema_str}

If there are no edges like in the case of single item supply chains the edges will be an empty array.  
Lead time is in days and time buckets are days from the start of the planning horizon. 
Generate a feasible just in time plan.
Minimize the lateness when you have to delay a demand due to constraints. 
A separate planned order is needed for each substitute component or each alternate resource.
Respond ONLY with JSON.
Ouput the solution in the following json schema

{scp_solution_schema_str}

Problem:


"""

def generate(problem: int)->str:
    pfile = f"green-agent/data/tasks/{problem}-p.json"
    with open(pfile, "r", encoding="utf-8") as f:
        prob = json.load(f)   # Python dict/list
    problem_str = json.dumps(prob)  # JSON as string
    result = prompt + problem_str
    return result

def score(problem: int, response: str)->bool:
    sfile = f"green-agent/data/tasks/{problem}-s.json"
    with open(sfile, "r", encoding="utf-8") as f:
        expected = json.load(f)   # Python dict/list
    
    try:
        answer = json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")

    print("EXPECTED")
    print(normalize_keys(expected))
    print("ANSWER")
    print(normalize_keys(answer))
    result = (normalize_keys(expected) == normalize_keys(answer))
    print(result)
    return result

def normalize_keys(d):
    """Recursively convert all dict keys to lowercase"""
    if isinstance(d, dict):
        return {k.lower(): normalize_keys(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [normalize_keys(item) for item in d]
    else:
        return d

def deep_diff(dict1, dict2, path=""):
    """
        Returns dict of differences: {'path': (value1, value2)}
        # {} if equal, else {'b.y[1]': (4, 5), ...}

    """
    diff = {}
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        new_path = f"{path}.{key}" if path else key
        
        if key not in dict1:
            diff[new_path] = (None, dict2[key])
        elif key not in dict2:
            diff[new_path] = (dict1[key], None)
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            nested_diff = deep_diff(dict1[key], dict2[key], new_path)
            diff.update(nested_diff)
        elif dict1[key] != dict2[key]:
            diff[new_path] = (dict1[key], dict2[key])
    
    return diff

def dicts_equal(d1, d2):
    return json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
