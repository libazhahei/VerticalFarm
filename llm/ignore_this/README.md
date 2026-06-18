# Legacy LLM modules

These files are kept for reference only. Use the modular packages instead:

- Local agent workflow: `llm.workflow.LocalWorkflow`
- LLM clients: `llm.clients.OpenAIClient`
- Demo entry: `python -m llm.demo`

## Files

- `local.py` — original monolithic LocalPlanner (~1340 lines)
- `ollama.py`, `_ollama.py` — legacy Ollama HTTP client
- `tcp_server.py` — legacy TCP + ctransformers Llama-2 server
