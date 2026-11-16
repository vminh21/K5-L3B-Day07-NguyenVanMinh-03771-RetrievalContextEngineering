"""Check the API key, confirm LLM_MODEL exists, and run one tool-calling round trip."""
import json
import sys
import time

from openai import OpenAI

from src import config

# Responses API tool format (gpt-5.6-luna rejects function tools on /v1/chat/completions).
TOOL = {
    "type": "function",
    "name": "search_document",
    "description": "Search the Communist Manifesto and return relevant chunks with chunk_id and page.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    },
    "strict": True,
}


def main() -> int:
    client = OpenAI()  # reads OPENAI_API_KEY from the environment (.env loaded by src.config)
    ids = sorted(m.id for m in client.models.list())
    if config.LLM_MODEL not in ids:
        close = [i for i in ids if "luna" in i or "5.6" in i]
        print(f"Model {config.LLM_MODEL!r} not found. Similar IDs on this key: {close or ids[:20]}")
        return 1
    print(f"model OK: {config.LLM_MODEL}")
    t0 = time.perf_counter()
    resp = client.responses.create(
        model=config.LLM_MODEL,
        input="Use the tool to find what is haunting Europe.",
        tools=[TOOL],
        reasoning={"effort": "low"},
        max_output_tokens=300,
    )
    calls = [(o.name, json.loads(o.arguments)) for o in resp.output if o.type == "function_call"]
    print(f"tool calls: {calls}  ({(time.perf_counter() - t0):.1f}s, usage={resp.usage})")
    return 0 if calls else 1


if __name__ == "__main__":
    sys.exit(main())
