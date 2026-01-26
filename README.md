# A Baby Supply Chain Planning Benchmark
This project list a green evaluator agent that can evaluate purple agents on supply chain planning tasks.
After evaluating the purple agents the green agent reports the % pass rate and results on each problem and the results are published to a leaderboard as part of the AgentX-AgentBeats competiton.

We were not sure what ERP supply chain data formats the llms might have exposure to, so we used a json schema to communicate the supply chain planning problems to the LLM Agents. A property graph approach is used to represent the supply chain network.

You can build the green and purple agent containers using the corresponding docker files

docker build -f Dockerfile.green -t green::latest .

docker build -f Dockerfile.purple -t purple::latest .

The green-agent/data/schema directory has the json schema for the supply chain problem and the json schema for the supply chain solution or output. 

The green-agent/data/tasks has the problems and solution in this benchmark represented using the schema in the schema directory.
One can easily extend this benchmark by adding more problems and solutions in the task directory.

The leaderboard for this benchmark is at https://github.com/zabraha/baby-scp-leaderboard

The green agent evaluator is strict as far as the output format goes and you will not get a pass if the answer is not presented in the requested json format.

The baby-scp-green agent's home page on agent-beats is https://agentbeats.dev/zabraha/baby-scp-green

 We tested with various purple agents with different llm models available on nebius token factory.
 Here are some links to the purple agents

 https://agentbeats.dev/zabraha/baby-scp-purple

 https://agentbeats.dev/zabraha/scp-kimi-k2

 https://agentbeats.dev/zabraha/scp-qwen3-235

 https://agentbeats.dev/zabraha/scp-oss-120





