"""Build data/day7/questions.json and cases.json.

Dev  = all 22 Day 6 questions (q18-q22 were Day 6 test, already seen -> moved to dev) + 3 no-evidence.
Test = 6 NEW answerable questions (pages never used in Day 6) + 2 no-evidence.
Evidence quotes are matched whitespace-insensitively, then replaced by the EXACT chunk text
(line breaks included) so starter/baseline.py's exact-substring check passes. Every page where the
quote occurs becomes an alternative gold entry.
"""
import json
import re
from pathlib import Path

DAY6_Q = Path("../K5-L3B-Day06-NguyenVanMinh-2A202603771-DataIngestion/benchmark/questions.json")
CHUNKS = Path("data/day7/chunks.json")
OUT = Path("data/day7")
SRC = "communist-manifesto-1848"

NEW_TEST = [
    dict(id="t01", type="direct", filter=None,
         question="According to the prefaces of the Manifesto, for how long did the proletariat hold political power in the Paris Commune?",
         expected_answer="For two whole months (the first time the proletariat held political power).",
         evidence="where the proletariat for the first time held political power for two whole months"),
    dict(id="t02", type="direct", filter=None,
         question="Who does the Manifesto name as the head of the school of petty-bourgeois Socialism?",
         expected_answer="Sismondi, head of this school not only in France but also in England.",
         evidence="Sismondi was the head of this school, not only in France but also in England."),
    dict(id="t03", type="paraphrase", filter=None,
         question="What power does Communism leave to people, and what power does it take away from them?",
         expected_answer="It leaves everyone the power to appropriate the products of society; it only removes the power to subjugate the labour of others by means of such appropriation.",
         evidence="Communism deprives no man of the power to appropriate the products of society; all that it does is to deprive him of the power to subjugate the labour of others by means of such appropriations."),
    dict(id="t04", type="conditional", filter=None,
         question="When an Armenian translation of the Manifesto was offered to a publisher, in what year and city did this happen, and why was it not published under Marx's name?",
         expected_answer="In 1887 in Constantinople; the publisher lacked the courage to publish something bearing Marx's name and suggested the translator put his own name as author, which the translator declined.",
         evidence="in 1887 the manuscript of an Armenian translation was offered to a publisher in Constantinople. But the good man did not have the courage to publish something bearing the name of Marx and suggested that the translator set down his own name as author, which the latter however declined."),
    dict(id="t05", type="metadata_filter", filter={"chapter": "Chapter III"},
         question="In Chapter III, how is Christian Socialism described?",
         expected_answer="As 'but the holy water with which the priest consecrates the heart-burnings of the aristocrat'.",
         evidence="Christian Socialism is but the holy water with which the priest consecrates the heart-burnings of the aristocrat."),
    dict(id="t06", type="paraphrase", filter=None,
         question="How had the International changed the workers by the time it broke up, compared with when it started, and in which years were those two points?",
         expected_answer="When it broke up in 1874 it left the workers quite different men from what it had found them in 1864.",
         evidence="The International, on its breaking in 1874, left the workers quite different men from what it found them in 1864."),
]

NO_EVIDENCE = [
    dict(id="qn01", split="dev",
         question="What does the Manifesto say about the outcome of the Russian Revolution of 1917?",
         absence_reason="Grep over all 167 chunks (pages 2-44): '1917', 'Lenin', 'Bolshevik' = 0 hits. The 1882 Russian preface (p.35) only speculates about a future 'Russian Revolution' as a possible signal for revolution in the West; the documents predate 1917, so nothing on its outcome."),
    dict(id="qn02", split="dev",
         question="How many members did the Communist League have when the Manifesto was written?",
         absence_reason="Grep 'members', 'membership', 'Communist League' over all chunks: the League is described as an international, secret workers' association (p.33, p.36) but no membership count appears anywhere ('membership' only on p.12, about serfs in the commune)."),
    dict(id="qn03", split="dev",
         question="What formula for surplus value or the labour theory of value does the Manifesto give?",
         absence_reason="Grep 'surplus value', 'surplus-value', 'labour theory', 'Capital, Volume', 'Das Kapital' = 0 hits in all chunks. These concepts belong to Marx's later Capital, not the Manifesto."),
    dict(id="tn01", split="test",
         question="What position does the Manifesto take on giving women the right to vote?",
         absence_reason="Grep 'suffrage', 'vote', 'franchise' = 0 hits in all chunks. Chapter II discusses the bourgeois family and 'community of women', but nothing about women's voting rights."),
    dict(id="tn02", split="test",
         question="How many copies of the first 1848 German edition of the Manifesto were printed?",
         absence_reason="Grep 'copies', 'printed', 'print run', '1848 edition': the only 'copies' hit (p.42) says industrial progress can be measured by copies circulated in each language; no figure for the first edition's print run anywhere in pages 2-44."),
]


def exact_spans(quote, chunks):
    pat = re.compile(r"\s+".join(map(re.escape, quote.split())))
    out = []
    for c in chunks:
        m = pat.search(c["text"])
        if m:
            out.append({"source_id": c["source_id"], "page": c["page"], "evidence": m.group(0), "chunk_id": c["id"]})
    return out


def gold_for(quote, page, chunks):
    spans = exact_spans(quote, chunks)
    if not any(s["page"] == page for s in spans):
        raise SystemExit(f"evidence not found on page {page}: {quote[:80]}")
    # gold page first, then other pages where the same passage is repeated (alternatives)
    spans.sort(key=lambda s: (s["page"] != page, s["page"]))
    seen, gold = set(), []
    for s in spans:
        if s["page"] not in seen:
            seen.add(s["page"])
            gold.append({k: s[k] for k in ("source_id", "page", "evidence")})
    return gold


def main():
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    questions = []
    for q in json.loads(DAY6_Q.read_text(encoding="utf-8")):
        questions.append({
            "id": q["id"], "split": "dev", "type": q["type"], "question": q["question"],
            "expected_answer": q["expected_answer"],
            "gold": gold_for(q["evidence_quote"], q["gold_page"], chunks),
            "filter": q.get("filter"),
            "origin": f"day6-{q['split']}",
        })
    for q in NEW_TEST:
        page = next(s["page"] for s in exact_spans(q["evidence"], chunks))
        questions.append({
            "id": q["id"], "split": "test", "type": q["type"], "question": q["question"],
            "expected_answer": q["expected_answer"], "gold": gold_for(q["evidence"], page, chunks),
            "filter": q["filter"], "origin": "day7-new",
        })
    cases = [{"id": q["id"], "split": q["split"], "question": q["question"], "answerable": True,
              "filter": q["filter"]} for q in questions]
    cases += [{**n, "answerable": False, "expected_behavior": "search_and_abstain", "filter": None}
              for n in NO_EVIDENCE]
    for name, data in (("questions.json", questions), ("cases.json", cases)):
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for split in ("dev", "test"):
        a = sum(1 for c in cases if c["split"] == split and c["answerable"])
        n = sum(1 for c in cases if c["split"] == split and not c["answerable"])
        print(f"{split}: {a} answerable + {n} no-evidence")
    multi = [q["id"] for q in questions if len(q["gold"]) > 1]
    print("questions with alternative gold pages:", multi)


if __name__ == "__main__":
    main()
