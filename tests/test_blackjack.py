# -*- coding: utf-8 -*-
"""3.28: блэкджек — упрощённые правила, только зимой, без удвоения."""
import random
import unittest

from farmgame import blackjack as bj
from farmgame import config as cfg
from farmgame.tavern import Tavern


def rigged(deck_top):
    """rng, после shuffle которого сверху колоды лежат карты deck_top (pop берёт с конца)."""
    class R:
        def shuffle(self, deck):
            rest = [c for c in deck if c not in deck_top]
            deck[:] = rest + list(reversed(deck_top))
    return R()


class Values(unittest.TestCase):
    def test_hand_value(self):
        self.assertEqual(bj.hand_value([("A", "hearts"), ("K", "spades")]), 21)
        self.assertEqual(bj.hand_value([("A", "hearts"), ("A", "spades"), ("9", "clubs")]), 21)
        self.assertEqual(bj.hand_value([("K", "hearts"), ("Q", "spades"), ("5", "clubs")]), 25)
        self.assertTrue(bj.is_natural([("A", "hearts"), ("10", "spades")]))
        self.assertFalse(bj.is_natural([("7", "hearts"), ("7", "spades"), ("7", "clubs")]))


class Rounds(unittest.TestCase):
    def setUp(self):
        self.t = Tavern()
        self.t.tokens = 100
        self.g = bj.Blackjack()

    def test_min_bet(self):
        self.g.add_bet(self.t, 4)
        self.assertFalse(self.g.deal(self.t))
        self.g.clear_bet(self.t)
        self.assertEqual(self.t.tokens, 100)

    def test_win_pays_double(self):
        # игрок 10+9=19, дилер 10+7=17 — стоит; игрок «хватит» и выигрывает
        self.g.add_bet(self.t, 10)
        self.g.deal(self.t, rigged([("10", "hearts"), ("9", "hearts"), ("10", "clubs"), ("7", "clubs")]))
        self.g.stand(self.t)
        self.assertEqual(self.g.result, "win")
        self.assertEqual(self.t.tokens, 110)

    def test_natural_pays_3_to_2(self):
        self.g.add_bet(self.t, 10)
        self.g.deal(self.t, rigged([("A", "hearts"), ("K", "hearts"), ("10", "clubs"), ("7", "clubs")]))
        self.assertEqual(self.g.result, "blackjack")
        self.assertEqual(self.t.tokens, 115)

    def test_bust_and_dealer_draws_to_17(self):
        self.g.add_bet(self.t, 10)
        self.g.deal(self.t, rigged([("10", "hearts"), ("6", "hearts"), ("10", "clubs"), ("6", "clubs"),
                                    ("9", "spades")]))
        self.g.hit(self.t)
        self.assertEqual(self.g.result, "bust")
        self.assertEqual(self.t.tokens, 90)
        self.g.next_round(self.t)
        self.assertEqual(self.g.bet, 10)        # та же ставка — сама
        g2 = bj.Blackjack()
        t2 = Tavern()
        t2.tokens = 50
        g2.add_bet(t2, 5)
        g2.deal(t2, random.Random(4))
        g2.stand(t2)
        self.assertTrue(bj.hand_value(g2.dealer) >= 17 or bj.is_natural(g2.player))

    def test_push(self):
        self.g.add_bet(self.t, 10)
        self.g.deal(self.t, rigged([("10", "hearts"), ("8", "hearts"), ("10", "clubs"), ("8", "clubs")]))
        self.g.stand(self.t)
        self.assertEqual(self.g.result, "push")
        self.assertEqual(self.t.tokens, 100)

    def test_no_double_or_split(self):
        self.assertFalse(hasattr(self.g, "double"))
        self.assertFalse(hasattr(self.g, "split"))

    def test_fair_over_many_rounds(self):
        """Тысячи раздач по простой стратегии «брать до 17»: жетоны не уходят в минус, игра не зависает."""
        t = Tavern()
        t.tokens = 10 ** 6
        g = bj.Blackjack()
        rng = random.Random(7)
        for _ in range(3000):
            g.add_bet(t, 5)
            g.deal(t, rng)
            while g.state == "player" and bj.hand_value(g.player) < 17:
                g.hit(t)
            g.stand(t)
            self.assertEqual(g.state, "done")
            g.next_round(t, same_bet=False)
        self.assertGreater(t.tokens, 10 ** 6 - 3000 * 5)

    def test_only_winter(self):
        winter = next(n for n, fm in enumerate(cfg.FARMS) if fm["id"] == "winter")
        self.assertFalse(bj.unlocked(winter - 1))
        self.assertTrue(bj.unlocked(winter))


if __name__ == "__main__":
    unittest.main()
