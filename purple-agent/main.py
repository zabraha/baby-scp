from fastapi import FastAPI, Request
import uvicorn
import os
import json
import re
from openai import OpenAI  # pip install openai

url= os.getenv("BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
model = os.getenv("MODEL", "moonshotai/Kimi-K2-Thinking")

# Read Nebius API key from environment
keySet = True
nebius_key = os.getenv("NEBIUS_API_KEY")
if not nebius_key:
    keySet = False
    print("WARNING: NEBIUS_API_KEY IS NOT SET.")
    # raise ValueError("NEBIUS_API_KEY environment variable is required")
else:
    # Configure OpenAI-compatible client for Nebius Token Factory
    client = OpenAI(base_url=url,api_key=nebius_key)

def solve_scp(question: str) -> str:
    if not keySet:
        return "{}"
    try:
        # Choose an appropriate Nebius model, e.g. a reasoning or instruct model
        response = client.chat.completions.create(
            model=model,  # or another model from Nebius
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are a supply chain planning expert.
                        Respond with ONLY valid JSON matching the exact schema requested by the user. 
                        NO explanations, NO thinking, NO markdown except the JSON.
                        Include <think> tags for reasoning internally but FINAL OUTPUT MUST BE:

                        ```json
                            {
                                \"demandsSatisfied\": [...],
                                \"plannedOrders\": [...]
                            }
                        ```
                    """
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question
                        }       
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        print("response from llm:", response)
        content = response.choices[0].message.content
        

        # Parse response safely
        try:
            if response.choices and len(response.choices) > 0:
                
                content = response.choices[0].message.content.strip()
                print("Content:", content)
                try:
                    json_data = extract_json_safely(content)
                    print("Parsed JSON:", json_data)
                except ValueError as e:
                    print(f"JSON extraction failed: {e}")
                    json_data = None
                if json_data:
                    json_str = json.dumps(json_data)
                else:
                    json_str = "{}"
                print("json data str:  ", json_str)
            else:
                print("No choices in response from llm")
                json_str = "{}"
        except json.JSONDecodeError:
            print("Response is not valid JSON")
            json_str = "{}"
        print("response from llm as content: " , json_str)
        return json_str
    except Exception as e:
        print("ERROR response from calling LLM " + str(e))
        return "{}"
 

def extract_json_safely(content):
    """Extract JSON from DeepSeek response (handles both formats)"""
    # Case 1: Plain JSON
    try:
        parsed = json.loads(content)
        # Handle both array [obj] and plain obj cases
        if isinstance(parsed, list) and len(parsed) == 1:
            clean_json = parsed[0]  # Extract single object
        else:
            clean_json = parsed     # Already plain object
        return clean_json
    except json.JSONDecodeError:
        pass
    
    # Case 2: JSON in ```json block (handles <think> + code block)
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL | re.IGNORECASE)
    if json_match:  # ← CHECK IF MATCH EXISTS
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Case 3: Fallback - find any valid JSON object
    json_match = re.search(r'\{[^{}]*?(?:\{[^{}]*?\}[^{}]*?)*?\}', content, re.DOTALL)
    if json_match:  # ← CHECK IF MATCH EXISTS
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    print("No valid JSON found in response")
    return {}



app = FastAPI()

    

@app.post("/")
@app.post("/a2a/message")
async def handle_message(request: Request):
    body = await request.json()
    
    if body.get("method") != "message/send":
        return {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32601}}
    
    # Fix: Raw dict access - NO Pydantic
    message = body["params"]["message"]
    parts = message.get("parts", [])
    
    # Safe dict access
    user_text = ""
    if parts and len(parts) > 0 and "text" in parts[0]:
        user_text = parts[0]["text"]
    
    # Your purple agent logic here
    #response = f"PURPLE AGENT: {user_text.upper()} - Processed successfully!"
    response = solve_scp(user_text)
    print("response text send as rpc:" , response)
    
    return {
        "jsonrpc": "2.0",
        "id": body["id"],
        "result": {
            "kind": "message",
            "parts": [{"kind": "text", "text": response}],
        }
    }

    
@app.get("/.well-known/agent-card.json")
async def agent_card():
    result = {
        "schema_version": "v1",
        "version": "1.0.0",
        "name": "scp-kimi-k2-thinking", 
        "description": "AgentBeats purple agent using nebius token factory and Kimi-K2-Thinking model",
        "protocols": ["a2a"],
        "endpoints": {"message": "/a2a/message"},
        "tags": ["purple", "solver", "supply chain planning", "KimiK2"],
        "capabilities": {    
            "llm": True,
            "chat": True,
            "streaming": True
        },
        "defaultInputModes": ["text"],    # REQUIRED
        "defaultOutputModes": ["text"],   # REQUIRED
        "skills": [                        # REQUIRED
            {
                "id": "supply-chain-planning-solver",
                "name": "Supply Chain Planning Solver",
                "description": "Solves supply chain planning problems and generates feasible plans",
                 "tags": ["supply-chain-solver", "solver", "planning"]  # REQUIRED
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



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9090)
