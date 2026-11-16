"""I5 — deterministic check that every number in an answer is written in the cited passages.

Numbers are compared after normalising number words ("forty-five" -> 45, "twelve" -> 12, "hundred" -> 100)
in both the answer and the passages. Numbers that occur in the question itself are allowed.
Citation markers like [S3] / [chunk-id] are removed first.
"""
import re

_UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
         "sixteen seventeen eighteen nineteen".split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
WORDS = {w: i for i, w in enumerate(_UNITS)}
WORDS.update({w: 20 + 10 * i for i, w in enumerate(_TENS)})
WORDS["hundred"] = 100
_WORD_RE = re.compile(r"\b(" + "|".join(_TENS) + r")[\s-]+(" + "|".join(_UNITS[1:10]) + r")\b|\b(" +
                      "|".join(sorted(WORDS, key=len, reverse=True)) + r")\b", re.I)
_CITE_RE = re.compile(r"\[[^\]]*\]")
_NUM_RE = re.compile(r"\d+")


def numbers(text: str) -> set[int]:
    text = _CITE_RE.sub(" ", text)
    out = {int(n) for n in _NUM_RE.findall(text.replace(",", ""))}
    for m in _WORD_RE.finditer(text):
        if m.group(1):
            out.add(WORDS[m.group(1).lower()] + WORDS[m.group(2).lower()])
        else:
            out.add(WORDS[m.group(3).lower()])
    return out


def unsupported_numbers(answer: str, passages: list[str], question: str = "") -> list[int]:
    allowed = set().union(*(numbers(p) for p in passages)) if passages else set()
    allowed |= numbers(question)
    return sorted(n for n in numbers(answer) if n not in allowed)
