import unittest

from src.numcheck import numbers, unsupported_numbers


class TestNumCheck(unittest.TestCase):
    def test_words_and_digits(self):
        self.assertEqual(numbers("forty-five years, twelve reprints, 1863 [S2]"), {45, 12, 1863})
        self.assertEqual(numbers("scarce one hundred years"), {1, 100})

    def test_computed_year_rejected(self):
        p = ["On September 28, 1864, ... True, the International itself lived only nine years."]
        self.assertEqual(unsupported_numbers("It began in 1864 and ended in 1873 [S1].", p), [1873])
        self.assertEqual(unsupported_numbers("It began in 1864 and lived nine years [S1].", p), [])

    def test_word_vs_digit_and_question_numbers(self):
        self.assertEqual(unsupported_numbers("45 years [S1]", ["the forty-five years separating us"]), [])
        self.assertEqual(unsupported_numbers("In 1847 socialism was ...", ["socialism was a middle-class movement"],
                                             question="what was socialism in 1847?"), [])


if __name__ == "__main__":
    unittest.main()
