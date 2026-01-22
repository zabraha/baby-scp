from fastapi import FastAPI, Request
import uvicorn
from google import genai
from dotenv import load_dotenv
import os


load_dotenv() #load gemini api key from .env and initialize the client
client = genai.Client()


def solve_scp(question: str)->str:
    try:
        response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=question)
        content = response.text.strip()
        return content
    except Exception as e:
        print("ERROR response from calling LLM  "+ str(e))
        return "{}"
 

app = FastAPI()

@app.post("/a2a/message")
async def handle_message(request: Request):
    body = await request.json()
    
    if body.get("method") != "message.create":
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
        "name": "purple-supply-chain-planning-solver", 
        "description": "AgentBeats purple agent using google gemini",
        "protocols": ["a2a"],
        "endpoints": {"message": "/a2a/message"},
        "tags": ["purple", "solver", "supply chain planning", "google gemini"]
    }
    # Conditionally add top-level url from env var if set
    card_url = os.getenv("CARD_URL")
    if card_url:
        result["url"] = card_url
    
    return result



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9090)
