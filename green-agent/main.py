from fastapi import FastAPI, Request
from pydantic import BaseModel
import httpx
from typing import Dict, Any
import uuid
import json
import time
import os

app = FastAPI()

class A2AMessage(BaseModel):
    kind: str
    parts: list
    metadata: Dict[str, Any] = {}

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

@app.post("/a2a/message")
async def handle_message(request: Request):
    body = await request.json()
    
    if body.get("method") != "message.create":
        return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32601}}
    
    # Extract from raw dict - NO Pydantic needed
    task_message = body["params"]["message"]
    parts = task_message.get("parts", [])
    
    # Fix: Use dict access, not object attributes
    user_prompt = ""
    if parts and len(parts) > 0 and "text" in parts[0]:
        user_prompt = parts[0]["text"]
    
    purple_url = task_message.get("metadata", {}).get("purple_endpoint", "")
    
    if not purple_url:
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "kind": "message",
                "parts": [{"kind": "text", "text": "❌ No purple_endpoint in metadata"}]
            }
        }
    
    results = []
    passes = 0

    try: 
        for task in TASKS:  # Run assessment on each task
            start = time.time()
            task.prompt = generate(task.id)
    
            # Call purple agent
            purple_payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "message.create",
                "params": {
                    "message": {
                        "kind": "message",
                        "parts": [{"kind": "text", "text": task.prompt}]
                    }
                }
            }
     
            async with httpx.AsyncClient(timeout=10.0) as client:
                purple_resp = await client.post(purple_url, json=purple_payload)
                purple_resp.raise_for_status()
                purple_data = purple_resp.json()
            
            # Extract purple response safely
            purple_text = "No response"
            if (purple_data.get("result") and 
                "parts" in purple_data["result"] and 
                len(purple_data["result"]["parts"]) > 0 and 
                "text" in purple_data["result"]["parts"][0]):
                purple_text = purple_data["result"]["parts"][0]["text"]
            
            # Simple scoring logic
            print(purple_text)
            latency = time.time() - start
            success = score(task.id,purple_text)
        
            if success: 
                passes += 1
            results.append({"task_id": task.task_id, "success": success, "latency": latency})
            #score = 1.0 if "PURPLE" in purple_text.upper() else 0.5
        
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "kind": "message",
                "parts": [{
                    "kind": "data",
                    "mimeType": "application/json",
                    "data": {
                        "domain": user_prompt,
                        "pass_rate": passes / len(results),
                        "total_tasks": len(results),
                        "results": results
                   }
                }]
            }
        }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "kind": "message",
                "parts": [{"kind": "text", "text": f"❌ Error calling purple: {str(e)}"}],
                "metadata": {"score": 0.0}
            }
        }


@app.get("/.well-known/agent-card.json")
async def agent_card():

    result =  {
        "schema_version": "v1",
        "name": "baby-supply-chain-planning-evaluator",
        "description": "AgentBeats green agent for a baby supply chain planning benchmark",
        "protocols": ["a2a"],
        "endpoints": {"message": "/a2a/message"},
        "tags": ["green", "evaluator", "supply chain planning"]
    }
    # Conditionally add top-level url from env var if set
    card_url = os.getenv("CARD_URL")
    if card_url:
        result["url"] = card_url
    
    return result



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
