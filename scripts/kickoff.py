#!/usr/bin/env python3
"""
AgentBeats kickoff script - tests green → purple agent communication
Run with: uv run scripts/kickoff.py
Requires both agents running on default ports (8080 green, 9090 purple)
"""

import asyncio
import httpx
import uuid
import json
#from typing import Dict, Any

# Configuration
GREEN_URL = "http://localhost:8080"
PURPLE_URL = "http://localhost:9090"
TIMEOUT = 30.0

async def test_agent_discovery():
    """Test /.well-known/agent.json endpoints"""
    print("🧪 Testing agent discovery...")
    
    for name, url in [("Green", GREEN_URL), ("Purple", PURPLE_URL)]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{url}/.well-known/agent.json", timeout=5.0)
                resp.raise_for_status()
                agent_card = resp.json()
                print(f"✅ {name} agent card: {agent_card['name']} ({agent_card.get('tags', [])})")
        except Exception as e:
            print(f"❌ {name} discovery failed: {e}")
            return False
    return True

async def kickoff_evaluation():
    """Send A2A task to green agent (which calls purple agent)"""
    print("\n🚀 Starting evaluation...")
    
    # Create realistic test task
    task_id = str(uuid.uuid4())
    domain = "Supply Chain Planning"
    
    payload = {
        "jsonrpc": "2.0",
        "id": task_id,
        "method": "message.create",
        "params": {
            "message": {
                "kind": "message",
                "parts": [{"kind": "text", "text": domain}],
                "metadata": {
                    "purple_endpoint": f"{PURPLE_URL}/a2a/message"
                }
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            print(f"📤 Sending task to green agent: {GREEN_URL}/a2a/message")
            resp = await client.post(f"{GREEN_URL}/a2a/message", json=payload)
            resp.raise_for_status()
            
            result = resp.json()
            print(f"📥 Green agent response: {json.dumps(result, indent=2)}")
            
            # Extract score and purple response
            if "result" in result and "metadata" in result["result"]:
                score = result["result"]["metadata"].get("score", "N/A")
                print(f"🎯 Evaluation score: {score}")
            return True
            
    except httpx.TimeoutException:
        print("⏰ Timeout - agents not responding fast enough")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return False

async def main():
    print("🎯 AgentBeats FastAPI Test Suite")
    print("=" * 50)
    
    # Step 1: Verify agents are discoverable
    if not await test_agent_discovery():
        print("\n💡 Start agents first:")
        print("  uv run scripts/run-green.sh")
        print("  uv run scripts/run-purple.sh  (separate terminals)")
        return
    
    # Step 2: Run evaluation
    success = await kickoff_evaluation()
    
    if success:
        print("\n🎉 SUCCESS! Green agent → Purple agent communication works!")
        print("✅ Ready for AgentBeats competition submission")
        print("\n📦 Next: docker build -t green-agent . && docker run -p 8080:8080 green-agent")
    else:
        print("\n❌ Test failed. Check agent logs and try again.")

if __name__ == "__main__":
    asyncio.run(main())
