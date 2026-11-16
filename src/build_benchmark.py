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


# Gold completion AFTER the runs (2026-11-16, round 3): the prefaces repeat passages, and these valid
# alternative evidence sentences were found while grading. Added as alternatives (any one is enough);
# agent outputs are NOT re-run; retrieval metrics are re-scored from stored traces (see results/gold_correction.md).
GOLD_ADDITIONS = {
    "t06": "The working class of 1874, at the dissolution of the International, was altogether different from that of 1864, at its foundation.",
    "u06": "Socialism in 1847 signified a bourgeois movement, communism a working-class movement.",
}


def add_gold(rec, chunks):
    extra = GOLD_ADDITIONS.get(rec["id"])
    if extra:
        spans = exact_spans(extra, chunks)
        assert spans, rec["id"]
        have = {(g["page"], g["evidence"]) for g in rec["gold"]}
        for s in spans:
            if (s["page"], s["evidence"]) not in have:
                rec["gold"].append({k: s[k] for k in ("source_id", "page", "evidence")})
                have.add((s["page"], s["evidence"]))
        rec["gold_note"] = "alternative evidence added after the test run (gold completion, round 3)"
    return rec


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
        add_gold(questions[-1], chunks)
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


if __name__ == "__main__" and not ({"--test-v2", "--round3"} & set(__import__("sys").argv)):
    main()


# ---------------------------------------------------------------------------------------------
# TEST v2 (written 2026-11-16 AFTER test v1 was used to diagnose t06 -> test v1 is contaminated
# for tuning). Written and committed BEFORE any new change is made or evaluated; pages never used
# by dev or test v1. Output: data/day7/test_v2/{questions,cases}.json with split="test".
NEW_TEST_V2 = [
    dict(id="u01", type="direct", filter=None,
         question="According to the Manifesto, whose ideas have always been the ruling ideas of each age?",
         expected_answer="The ideas of its ruling class.",
         evidence="The ruling ideas of each age have ever been the ideas of its ruling class."),
    dict(id="u02", type="direct", filter=None,
         question="Which work by Proudhon is cited as an example of Conservative or Bourgeois Socialism?",
         expected_answer="Proudhon's 'Philosophie de la Misère' (spelled 'Philosophis de la Misère' in this edition).",
         evidence="We may cite Proudhon’s Philosophis de la Misère as an example of this form."),
    dict(id="u03", type="paraphrase", filter=None,
         question="How does the Manifesto characterise feudal Socialism in relation to the past and the future?",
         expected_answer="Half lamentation, half lampoon; half an echo of the past, half menace of the future.",
         evidence="half lamentation, half lampoon; half an echo of the past, half menace of the future"),
    dict(id="u04", type="conditional", filter=None,
         question="In Switzerland, which party do the Communists support, and what do they keep in mind about that party?",
         expected_answer="They support the Radicals, without losing sight of the fact that this party consists of antagonistic elements: partly Democratic Socialists (in the French sense), partly radical bourgeois.",
         evidence="In Switzerland, they support the Radicals, without losing sight of the fact that this party consists of antagonistic elements, partly of Democratic Socialists, in the French sense, partly of radical bourgeois."),
    dict(id="u05", type="metadata_filter", filter={"chapter": "Chapter II"},
         question="In Chapter II, on what foundation is the present, bourgeois family based?",
         expected_answer="On capital, on private gain.",
         evidence="On what foundation is the present family, the bourgeois family, based? On capital, on private gain."),
    dict(id="u06", type="direct", filter=None,
         question="According to the prefaces, what kind of movement was socialism in 1847, and what kind was communism?",
         expected_answer="Socialism was a middle-class movement; communism was a working-class movement.",
         evidence="Thus, in 1847, socialism was a middle-class movement, communism a working-class movement."),
    dict(id="u07", type="conditional", filter=None,
         question="According to the 1892 Polish preface, in which year did Poland succumb to Russia, and how much greater was the Russian force?",
         expected_answer="In 1863, to a tenfold greater Russian force.",
         evidence="was left to its own resources when it succumbed in 1863 to a tenfold greater Russian force."),
]
NO_EVIDENCE_V2 = [
    dict(id="un01", split="test",
         question="In what year was Karl Marx born, according to the Manifesto and its prefaces?",
         absence_reason="Grep 'born', 'birth', '1818' over all 167 chunks: '1818' only appears as Lewis Henry Morgan's dates (1818-1861, p.3); 'birth' only about the proletariat (p.9) and a 'new proletarian era' (p.44). No birth date for Marx anywhere."),
    dict(id="un02", split="test",
         question="What does the Manifesto say about Abraham Lincoln and the abolition of slavery in the American Civil War?",
         absence_reason="Grep 'Lincoln' = 0; 'civil war' only 'veiled civil war' (p.12) and the title 'The Civil War in France' (p.33, p.39); 'slavery' only generic (p.12); 'American' hits (p.30, 34, 40, 42) are about Icaria, agriculture, translations and May Day. Nothing about Lincoln or US abolition."),
]


def build_test_v2():
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    used = {q["id"] for q in json.loads((OUT / "questions.json").read_text(encoding="utf-8"))}
    assert not used & {q["id"] for q in NEW_TEST_V2}
    questions = []
    for q in NEW_TEST_V2:
        spans = exact_spans(q["evidence"], chunks)
        assert spans, f"{q['id']}: evidence not found"
        questions.append({"id": q["id"], "split": "test", "type": q["type"], "question": q["question"],
                          "expected_answer": q["expected_answer"], "gold": gold_for(q["evidence"], spans[0]["page"], chunks),
                          "filter": q["filter"], "origin": "day7-test-v2"})
        add_gold(questions[-1], chunks)
    cases = [{"id": q["id"], "split": "test", "question": q["question"], "answerable": True, "filter": q["filter"]}
             for q in questions]
    cases += [{**n, "answerable": False, "expected_behavior": "search_and_abstain", "filter": None} for n in NO_EVIDENCE_V2]
    out = OUT / "test_v2"
    out.mkdir(exist_ok=True)
    for name, data in (("questions.json", questions), ("cases.json", cases)):
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"test_v2: {len(questions)} answerable + {len(NO_EVIDENCE_V2)} no-evidence;",
          "pages:", [g["page"] for q in questions for g in q["gold"]])


if __name__ == "__main__" and "--test-v2" in __import__("sys").argv:
    build_test_v2()


# ---------------------------------------------------------------------------------------------
# ROUND 3 (written BEFORE any round-3 change): harder + larger independent TEST v3 and a HARD DEV
# set (dev was saturated at 22/22). Types: paraphrase (low word overlap), numeric (numbers that are
# stated in the text; some tempt arithmetic), multi_hop (needs ALL evidence groups), chunk-boundary
# list items, footnotes, metadata_filter, and near-miss no-evidence traps.
# Multi-hop: "groups" = list of evidence quotes that must ALL be in context / supported.
def Q(id, type, question, expected_answer, evidence=None, groups=None, filter=None):
    return dict(id=id, type=type, question=question, expected_answer=expected_answer,
                evidence=evidence, groups=groups, filter=filter)


TEST_V3 = [
    Q("v01", "paraphrase", "Which works of the bourgeoisie does Chapter I say surpass famous ancient and medieval monuments, and which monuments are named?",
      "It has accomplished wonders far surpassing Egyptian pyramids, Roman aqueducts and Gothic cathedrals (and conducted expeditions that put in the shade all former Exoduses of nations and crusades).",
      "It has accomplished wonders far surpassing Egyptian pyramids, Roman aqueducts, and Gothic cathedrals"),
    Q("v02", "paraphrase", "To what figure does the Manifesto compare modern bourgeois society that can no longer control the forces it has created?",
      "To the sorcerer who is no longer able to control the powers of the nether world whom he has called up by his spells.",
      "is like the sorcerer who is no longer able to control the powers of the nether world whom he has called up by his spells"),
    Q("v03", "paraphrase", "What epidemic, which earlier epochs would have found absurd, breaks out during commercial crises?",
      "The epidemic of over-production.",
      "In these crises, there breaks out an epidemic that, in all earlier epochs, would have seemed an absurdity — the epidemic of over- production."),
    Q("v04", "conditional", "In Germany, under what condition do the Communists fight together with the bourgeoisie, and against whom?",
      "Whenever the bourgeoisie acts in a revolutionary way — against the absolute monarchy, the feudal squirearchy, and the petty bourgeoisie.",
      "In Germany, they fight with the bourgeoisie whenever it acts in a revolutionary way, against the absolute monarchy, the feudal squirearchy, and the petty bourgeoisie."),
    Q("v05", "numeric", "How long did the Cologne Communist Trial last, and what sentences did seven of the prisoners receive?",
      "From October 4 till November 12; seven prisoners were sentenced to imprisonment in a fortress for three to six years.",
      "lasted from October 4 till November 12; seven of the prisoners were sentenced to terms of imprisonment in a fortress, varying from three to six years."),
    Q("v06", "multi_hop", "Where was the Central Board of the Communist League located when the Prussian police hunted it out, and what happened to the League immediately after the sentence in the trial that followed?",
      "It was in Cologne; immediately after the sentence the League was formally dissolved by its remaining members.",
      groups=["Thus the Prussian police hunted out the Central Board of the Communist League, then located in Cologne.",
              "Immediately after the sentence, the League was formlly dissolved by the remaining members."]),
    Q("v07", "numeric", "According to the 1888 preface, at least how many German reprints of the Manifesto had there been?",
      "Twelve altogether at the least.",
      "The German reprints are not to be counted; there have been twelve altogether at the least."),
    Q("v08", "conditional", "Who made the first English translation of the Manifesto, where did it appear, and in what year?",
      "Miss Helen Macfarlane; in George Julian Harney's Red Republican, London, 1850.",
      "The first English translation, by Miss Helen Macfarlane, appeared in George Julian Harney's Red Republican, London, 1850."),
    Q("v09", "numeric", "Who made the first and the second Russian translations of the Manifesto, and when and where was each published?",
      "First by Bakunin, published at Herzen's Kolokol office in Geneva about 1863; second by Vera Zasulich, also in Geneva, in 1882.",
      "The first Russian translation, made by Bakunin, was published at Herzen's Kolokol office in Geneva, about 1863; a second one, by the heroic Vera Zasulich, also in Geneva, in 1882."),
    Q("v10", "multi_hop", "To whom does Engels attribute the fundamental proposition of the Manifesto, and to which scientific theory does he compare its importance?",
      "To Marx; he says it is destined to do for history what Darwin's theory has done for biology.",
      groups=["I consider myself bound to state that the fundamental proposition which forms the nucleus belongs to Marx.",
              "is destined to do for history what Darwin's theory has done for biology"]),
    Q("v11", "conditional", "Which party do the Communists support in Poland, and which insurrection had that party fomented?",
      "The party that insists on an agrarian revolution as the prime condition for national emancipation — the party that fomented the insurrection of Cracow in 1846.",
      "In Poland, they support the party that insists on an agrarian revolution as the prime condition for national emancipation, that party which fomented the insurrection of Cracow in 1846."),
    Q("v12", "metadata_filter", "In Chapter II, which education-related measures appear in the list of measures for the most advanced countries?",
      "Free education for all children in public schools; abolition of children's factory labour in its present form; combination of education with industrial production.",
      "Free education for all children in public schools. Abolition of children’s factory labour in its present form. Combination of education with industrial production",
      filter={"chapter": "Chapter II"}),
    Q("v13", "paraphrase", "What does the Manifesto say will take the place of the old bourgeois society with its classes and class antagonisms?",
      "An association, in which the free development of each is the condition for the free development of all.",
      "we shall have an association, in which the free development of each is the condition for the free development of all."),
    Q("v14", "direct", "According to an editorial note, who was the chief representative and classical type of the 'True' Socialist tendency?",
      "Mr Karl Gruen.",
      "The chief representative and classical type of this tendency is Mr Karl Gruen."),
    Q("v15", "numeric", "In the discussion of feudal Socialism, which Restoration period is meant according to Engels' note, and what are its dates?",
      "The French Restoration (1814-1830), not the English Restoration (1660-1689).",
      "Not the English Restoration (1660-1689), but the French Restoration (1814-1830)."),
    Q("v16", "multi_hop", "Which founders of the Socialist and Communist systems does Chapter III name, and what did Owen call his Communist model societies?",
      "Saint-Simon, Fourier, Owen (and others); Owen called his model societies 'Home Colonies'.",
      groups=["The Socialist and Communist systems, properly so called, those of Saint-Simon, Fourier, Owen, and others",
              "“Home Colonies” were what Owen called his Communist model societies."]),
    Q("v17", "paraphrase", "How radical a break with tradition does the Manifesto say the Communist revolution is?",
      "It is the most radical rupture with traditional relations, and its development involves the most radical rupture with traditional ideas.",
      "The Communist revolution is the most radical rupture with traditional relations; no wonder that its development involved the most radical rupture with traditional ideas."),
    Q("v18", "numeric", "During how long a rule does the Manifesto say the bourgeoisie created more massive productive forces than all preceding generations together?",
      "During its rule of scarce one hundred years.",
      "The bourgeoisie, during its rule of scarce one hundred years, has created more massive and more colossal productive forces than have all preceding generations together."),
    Q("v19", "conditional", "According to the 1893 Italian preface, with which date and which revolutions did the publication of the Manifesto coincide?",
      "With March 18, 1848, the day of the revolution in Milan and Berlin.",
      "coincided, one may say, with March 18, 1848, the day of the revolution in Milan and Berlin"),
    Q("v20", "numeric", "According to the 1893 Italian preface, how many years separated it from the revolutionary epoch of 1848?",
      "Forty-five years.",
      "Nor have the forty-five years separating us from that revolutionary epoch passed to no purpose."),
]
TEST_V3_NO_EVIDENCE = [
    dict(id="w01", question="How many copies of the 1888 English edition translated by Samuel Moore were printed?",
         absence_reason="Grep 'cop(y|ies)': only p.42 (copies circulated as an index of industry); the 1888 edition (p.40) is described by title, translator and publisher only — no print run."),
    dict(id="w02", question="What was the sale price of the 1888 English edition published by William Reeves?",
         absence_reason="Grep 'price': only 'cheap prices of commodities' (p.6), 'price of a commodity' (p.8), 'average price of wage-labour' (p.15); 'shilling|penny|pence' = 0. '185 Fleet Street' (p.40) is an address, not a price."),
    dict(id="w03", question="How many members did the International Working Men's Association have at its peak?",
         absence_reason="Grep 'members', 'membership': no membership figure for the International anywhere (hits are about society, the commune, the League)."),
    dict(id="w04", question="What did Lenin write about the Manifesto in his preface to a Russian edition?",
         absence_reason="Grep 'Lenin' = 0. Russian editions discussed (Bakunin, Zasulich, 1882 preface) have no Lenin preface."),
    dict(id="w05", question="How many workers were killed in the Paris insurrection of June 1848?",
         absence_reason="The June 1848 defeat is mentioned (p.36, p.40) but grep 'killed|casualt|dead|slain' = 0; no casualty figure."),
    dict(id="w06", question="What prison sentence did Karl Marx himself receive at the Cologne Communist Trial?",
         absence_reason="p.36 says seven prisoners got three to six years in a fortress, but no defendant is named and grep 'Marx … prison|sentenced|trial' = 0; Marx's own sentence is not stated (trap: the 3-6 years figure exists)."),
]

DEV_HARD = [
    Q("h01", "paraphrase", "Why does the Manifesto call the lower middle class not only conservative but reactionary?",
      "Because they try to roll back the wheel of history.",
      "Nay more, they are reactionary, for they try to roll back the wheel of history."),
    Q("h02", "paraphrase", "In bourgeois society versus Communist society, which dominates which — the past or the present?",
      "In bourgeois society the past dominates the present; in Communist society the present dominates the past.",
      "In bourgeois society, therefore, the past dominates the present; in Communist society, the present dominates the past."),
    Q("h03", "numeric", "How many arch-conservative English trade unions does the 1890 preface mention, and in what year did their Swansea Congress chairman speak?",
      "Ten arch-conservative English trade unions; 1887.",
      "even the ten arch-conservative English trade unions were gradually approaching the point where, in 1887, the chairman of their Swansea Congress could say in their name"),
    Q("h04", "multi_hop", "What does Chapter I say the bourgeoisie produces above all, and how does the 1893 Italian preface reuse that phrase?",
      "Its own grave-diggers; the 1893 preface says the bourgeois regime has created a powerful proletariat and thus raised, in the language of the Manifesto, its own grave-diggers.",
      groups=["What the bourgeoisie therefore produces, above all, are its own grave-diggers.",
              "It has thus raised, to use the language of the Manifesto, its own grave-diggers."]),
    Q("h05", "paraphrase", "Does the Manifesto say that working men have a country?",
      "No — the working men have no country; one cannot take from them what they have not got.",
      "The working men have no country. We cannot take from them what they have not got."),
    Q("h06", "conditional", "Which practical measures proposed in the Critical-Utopian publications does the Manifesto list, and what character does it give them?",
      "Abolition of the distinction between town and country, of the family, of industries carried on for private individuals and of the wage system; proclamation of social harmony; turning the state into a superintendence of production — proposals of a purely Utopian character.",
      "These proposals, therefore, are of a purely Utopian character."),
    Q("h07", "numeric", "For what share of the population does the Manifesto say private property is already done away with in existing society?",
      "For nine-tenths of the population.",
      "private property is already done away with for nine-tenths of the population"),
    Q("h08", "metadata_filter", "In Chapter I, which English law was carried by taking advantage of divisions among the bourgeoisie?",
      "The ten-hours' bill.",
      "Thus, the ten- hours’ bill in England was carried.", filter={"chapter": "Chapter I"}),
]
DEV_HARD_NO_EVIDENCE = [
    dict(id="hn01", question="Under the ten-hours' bill, how many hours per week did English factory workers work?",
         absence_reason="Only 'the ten- hours’ bill in England was carried' (p.10); grep 'per week|weekly' only hits 'Claflin's Weekly' (p.37). No weekly hours (trap: tempts computing 10 × 6)."),
    dict(id="hn02", question="What did Charles Darwin himself say about the Manifesto?",
         absence_reason="Darwin appears only as Engels' comparison ('what Darwin's theory has done for biology', p.35, p.38); nothing Darwin said."),
]


def _build_set(items, no_ev, split, folder, origin):
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    questions = []
    for q in items:
        if q["groups"]:
            groups = []
            for ev in q["groups"]:
                spans = exact_spans(ev, chunks)
                assert spans, f"{q['id']}: group evidence not found: {ev[:60]}"
                groups.append(gold_for(ev, spans[0]["page"], chunks))
            gold = [g for grp in groups for g in grp]
        else:
            spans = exact_spans(q["evidence"], chunks)
            assert spans, f"{q['id']}: evidence not found: {q['evidence'][:60]}"
            gold, groups = gold_for(q["evidence"], spans[0]["page"], chunks), None
        rec = {"id": q["id"], "split": split, "type": q["type"], "question": q["question"],
               "expected_answer": q["expected_answer"], "gold": gold, "filter": q["filter"], "origin": origin}
        if groups:
            rec["gold_groups"] = groups  # multi-hop: every group must be covered
        questions.append(rec)
    cases = [{"id": q["id"], "split": split, "question": q["question"], "answerable": True, "filter": q["filter"]}
             for q in questions]
    cases += [{**n, "split": split, "answerable": False, "expected_behavior": "search_and_abstain", "filter": None}
              for n in no_ev]
    out = OUT / folder
    out.mkdir(exist_ok=True)
    for name, data in (("questions.json", questions), ("cases.json", cases)):
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    types = {}
    for q in questions:
        types[q["type"]] = types.get(q["type"], 0) + 1
    print(f"{folder}: {len(questions)} answerable + {len(no_ev)} no-evidence; types {types}")


if __name__ == "__main__" and "--round3" in __import__("sys").argv:
    _build_set(TEST_V3, TEST_V3_NO_EVIDENCE, "test", "test_v3", "day7-test-v3")
    _build_set(DEV_HARD, DEV_HARD_NO_EVIDENCE, "dev", "dev_hard", "day7-dev-hard")
