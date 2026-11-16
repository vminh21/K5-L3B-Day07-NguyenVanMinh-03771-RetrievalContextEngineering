"""Real-model client (OpenAI Responses API) with a cumulative, hard spending cap.

Every API call is appended to results/cost_ledger.jsonl. Before each call the total spent so far
(all runs) is checked against MAX_COST_USD; if reached, BudgetExceeded is raised and the caller
records status="error" — no further API calls are made.
Cost = input_tokens × price_in + output_tokens (incl. reasoning) × price_out.
"""
import json
import time

from openai import OpenAI

from src import config


class BudgetExceeded(RuntimeError):
    pass


class CostLedger:
    def __init__(self, path=config.COST_LEDGER, cap_usd: float = config.MAX_COST_USD):
        self.path, self.cap = path, cap_usd
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def spent(self) -> float:
        if not self.path.exists():
            return 0.0
        return sum(json.loads(l)["cost_usd"] for l in self.path.read_text().splitlines() if l.strip())

    def check(self):
        s = self.spent()
        if s >= self.cap:
            raise BudgetExceeded(f"spending cap reached: ${s:.4f} >= MAX_COST_USD ${self.cap:.2f}")

    def add(self, **rec):
        with self.path.open("a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}) + "\n")


def cost_of(tokens_in: int, tokens_out: int) -> float:
    return tokens_in * config.LLM_PRICE_IN_PER_M / 1e6 + tokens_out * config.LLM_PRICE_OUT_PER_M / 1e6


class LLM:
    def __init__(self, model: str = config.LLM_MODEL, effort: str = config.LLM_REASONING_EFFORT,
                 max_output_tokens: int = 1500, ledger: CostLedger | None = None):
        self.client = OpenAI(timeout=60, max_retries=5)  # backoff over short network drops
        self.model, self.effort, self.max_out = model, effort, max_output_tokens
        self.ledger = ledger or CostLedger()
        self.params = {"provider": "openai (Responses API)", "model": model, "reasoning_effort": effort,
                       "max_output_tokens": max_output_tokens, "temperature": "not set (reasoning model)",
                       "price_per_1M": [config.LLM_PRICE_IN_PER_M, config.LLM_PRICE_OUT_PER_M],
                       "max_cost_usd": self.ledger.cap}

    def call(self, *, instructions: str, input: list, tools: list, tag: str = ""):
        self.ledger.check()
        t0 = time.perf_counter()
        resp = self.client.responses.create(
            model=self.model, instructions=instructions, input=input, tools=tools,
            tool_choice="required", parallel_tool_calls=False,
            reasoning={"effort": self.effort}, max_output_tokens=self.max_out, store=False,
            include=["reasoning.encrypted_content"],
        )
        ms = (time.perf_counter() - t0) * 1000
        u = resp.usage
        c = cost_of(u.input_tokens, u.output_tokens)
        self.ledger.add(tag=tag, model=self.model, tokens_in=u.input_tokens, tokens_out=u.output_tokens,
                        reasoning_tokens=getattr(u.output_tokens_details, "reasoning_tokens", 0), cost_usd=c)
        return resp, {"tokens_in": u.input_tokens, "tokens_out": u.output_tokens, "cost_usd": c, "ms": ms}
