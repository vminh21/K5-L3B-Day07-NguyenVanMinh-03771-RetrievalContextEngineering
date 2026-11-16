"""Agent loop logic with a scripted fake LLM (tests only — never used for benchmark results)."""
import json
import unittest
from types import SimpleNamespace as NS

from src.agent import ABSTAIN_TEXT, Agent
from src.llm import BudgetExceeded
from src.retrievers.base import RetrievalError

CHUNK = {"id": "doc_p0002_B_0000", "text": "A spectre is haunting Europe — the spectre of communism.",
         "source_id": "doc", "source": "doc.pdf", "page": 2, "metadata": {"chapter": "Preamble"}}


class FakeRetriever:
    name, params = "fake", {}

    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def search(self, q, *, filters=None, top_k=5):
        self.calls.append((q, filters))
        if self.fail:
            raise RetrievalError("db down")
        return [dict(CHUNK, score=0.9, rank=1, strategy="fake")]


class FakeLLM:
    params = {}

    def __init__(self, script, exc=None):
        self.script, self.exc, self.n = list(script), exc, 0

    def call(self, **kw):
        if self.exc:
            raise self.exc
        name, args = self.script.pop(0)
        self.n += 1
        out = [NS(type="function_call", name=name, arguments=json.dumps(args), call_id=f"c{self.n}")]
        return NS(output=out), {"tokens_in": 10, "tokens_out": 5, "cost_usd": 0.0, "ms": 1}


def ans(text, cites, abstain=False):
    return ("final_answer", {"answer": text, "citations": cites, "abstain": abstain})


class TestAgent(unittest.TestCase):
    def test_answer_maps_labels_to_chunk_ids(self):
        r = Agent(FakeRetriever(), FakeLLM([("search", {"query": "spectre"}), ans("A spectre [S1].", ["S1"])])).run("q")
        self.assertEqual(r["status"], "answered")
        self.assertEqual(r["citations"], [CHUNK["id"]])
        self.assertIn(f"[{CHUNK['id']}]", r["answer"])
        self.assertEqual(sum(e["event"] == "search" for e in r["events"]), 1)

    def test_unknown_or_missing_citation_abstains(self):
        for final in (ans("x [S9].", ["S9"]), ans("no citation", []), ans("x", ["S1"])):
            r = Agent(FakeRetriever(), FakeLLM([("search", {"query": "s"}), final])).run("q")
            self.assertEqual((r["status"], r["answer"], r["citations"]), ("abstain", ABSTAIN_TEXT, []))

    def test_answer_without_search_has_no_valid_labels(self):
        r = Agent(FakeRetriever(), FakeLLM([ans("guess [S1].", ["S1"])])).run("q")
        self.assertEqual(r["status"], "abstain")

    def test_model_abstain(self):
        r = Agent(FakeRetriever(), FakeLLM([("search", {"query": "s"}), ans("", [], True)])).run("q")
        self.assertEqual(r["status"], "abstain")

    def test_search_limit(self):
        script = [("search", {"query": f"s{i}"}) for i in range(4)] + [ans("", [], True)]
        r = Agent(FakeRetriever(), FakeLLM(script), max_searches=2).run("q")
        self.assertEqual(sum(e["event"] == "search" for e in r["events"]), 2)
        self.assertTrue(any(e["event"] == "search_limit" for e in r["events"]))

    def test_filter_passed_and_errors_reported(self):
        ret = FakeRetriever()
        Agent(ret, FakeLLM([("search", {"query": "s"}), ans("", [], True)])).run("q", filters={"chapter": "Chapter I"})
        self.assertEqual(ret.calls[0][1], {"chapter": "Chapter I"})
        r = Agent(FakeRetriever(fail=True), FakeLLM([("search", {"query": "s"})])).run("q")
        self.assertEqual((r["status"], r["answer"]), ("error", None))
        r = Agent(FakeRetriever(), FakeLLM([], exc=BudgetExceeded("cap"))).run("q")
        self.assertEqual(r["status"], "error")
        self.assertIn("BudgetExceeded", r["error"])



class TestNumberVerifier(unittest.TestCase):
    def test_unsupported_number_gets_one_retry_then_abstain(self):
        llm = FakeLLM([("search", {"query": "s"}), ans("Ended in 1873 [S1].", ["S1"]), ans("Ended in 1873 [S1].", ["S1"])])
        r = Agent(FakeRetriever(), llm, verify_numbers=True).run("When?")
        self.assertEqual((r["status"], r["stop"]), ("abstain", "unverified_numbers"))
        self.assertEqual([e["retry"] for e in r["events"] if e["event"] == "number_check_failed"], [True, False])

    def test_retry_can_fix_answer(self):
        llm = FakeLLM([("search", {"query": "s"}), ans("Ended in 1873 [S1].", ["S1"]), ans("A spectre [S1].", ["S1"])])
        r = Agent(FakeRetriever(), llm, verify_numbers=True).run("What?")
        self.assertEqual(r["status"], "answered")


if __name__ == "__main__":
    unittest.main()
