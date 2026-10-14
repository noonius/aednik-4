"""Kontrollib kahepoolse trüki paigutust, ka viimase mittetäieliku lehe puhul."""
import unittest

from tee_pdf import back_order


class DuplexTests(unittest.TestCase):
    def test_long_edge_flip_matches_every_front_card(self):
        for count in range(1, 420):
            for start in range(0, count, 4):
                front = list(range(start, min(start + 4, count)))
                front += [None] * (4 - len(front))
                back = back_order(front)
                for slot, card in enumerate(front):
                    row, col = divmod(slot, 2)
                    self.assertEqual(card, back[row * 2 + 1 - col])


if __name__ == '__main__':
    unittest.main()
