# A Baby Supply Chain Planning Benchmark

This project list a green evaluator agent that can evaluate purple agents on supply chain planning tasks.
After evaluating the purple agents the green agent reports the % pass rate and results on each problem and the results are published to a leaderboard as part of the AgentX-AgentBeats competiton.

This benchmark assesses agents to generate feasible plans for simple supply  chain planning problems.
This is a baby benchmark with about 5 basic problems. The assessee will get a natural language prompt for each problem and is expected to respond back in json using the schema provided in the prompt. No tools are provided. Here is how the prompt looks like

## Typical prompt for an assessment problem

The supply chain planning problem is represented as a property graph using nodes, edges and demands using the following json schema

{scp-problem-schema}

If there are no edges like in the case of single item supply chains the edges will be an empty array.  
Lead time is in days and time buckets are days from the start of the planning horizon. 
Generate a feasible just in time plan.
Minimize the lateness when you have to delay a demand due to constraints. 
A separate planned order is needed for each substitute component or each alternate resource.
Respond ONLY with JSON.
Ouput the solution in the following json schema

{scp-solution-schema}

Problem:

{problem}

## Evaluation

The response is checked against the expected solution and a pass is given if they match.
The pass-rate as a percentage is reported as the overall performance.
The green agent evaluator is strict as far as the output format goes and you will not get a pass if the answer is not presented in the requested json format.

## Schema and Tasks

The green-agent/data/schema directory has the json schema for the supply chain problem and the json schema for the supply chain solution or output. 

The green-agent/data/tasks has the problems and solution in this benchmark represented using the schema in the schema directory.
One can easily extend this benchmark by adding more problems and solutions in the task directory.

## Leaderboard and Agents

The leaderboard for this benchmark is at https://github.com/zabraha/baby-scp-leaderboard

The baby-scp-green agent's home page on agent-beats is https://agentbeats.dev/zabraha/baby-scp-green

 We tested with various purple agents with different llm models available on nebius token factory.
 Here are some links to the purple agents

 - https://agentbeats.dev/zabraha/baby-scp-purple

 - https://agentbeats.dev/zabraha/scp-kimi-k2

 - https://agentbeats.dev/zabraha/scp-qwen3-235

 - https://agentbeats.dev/zabraha/scp-oss-120

 ## Building Docker Containers
 
You can build the green and purple agent containers using the corresponding docker files

docker build -f Dockerfile.green -t green::latest .

docker build -f Dockerfile.purple -t purple::latest .





