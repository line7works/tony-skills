import unittest

from turnstile import Counter


class CounterTest(unittest.TestCase):
    def test_two_turns_read_two(self):
        counter = Counter()
        counter.turn()
        counter.turn()
        self.assertEqual(counter.turns, 2)

    def test_a_reset_after_two_turns_reads_zero(self):
        counter = Counter()
        counter.turn()
        counter.turn()
        counter.reset()
        self.assertEqual(counter.turns, 0)


if __name__ == "__main__":
    unittest.main()
