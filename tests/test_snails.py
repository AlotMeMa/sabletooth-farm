# -*- coding: utf-8 -*-
"""3.40: скачки улиток в Игровой."""
import random
import unittest

from tests import helpers  # noqa: F401
from farmgame import snails as sn
from farmgame.tavern import Tavern


class Odds(unittest.TestCase):
    def test_probabilities_and_payout(self):
        rnd = random.Random(1)
        for _ in range(200):
            odds = sn.make_odds(rnd)
            self.assertEqual(len(odds), 5)
            self.assertAlmostEqual(sum(o["p"] for o in odds), 1.0)
            for o in odds:
                self.assertGreaterEqual(o["k"], 1.2)
                self.assertLessEqual(o["p"] * o["k"], sn.RTP + 1e-9)       # коэффициент не щедрее честного

    def test_return_to_player_about_rtp(self):
        rnd = random.Random(2)
        bet, back = 0, 0.0
        for n in range(20000):
            g = sn.SnailRace(rnd)
            t = Tavern()
            t.tokens = 10
            g.select(n % 5)
            g.add_bet(t, 10)
            g.start(t, rnd)
            bet += 10
            back += g.paid
        self.assertTrue(0.85 < back / bet < 0.97, back / bet)

    def test_winner_follows_odds(self):
        rnd = random.Random(3)
        odds = [dict(p=p, k=1.2, mood="") for p in (0.5, 0.2, 0.15, 0.1, 0.05)]
        first = [sn.finish_order(odds, rnd)[0] for _ in range(20000)]
        self.assertAlmostEqual(first.count(0) / 20000, 0.5, delta=0.02)
        self.assertAlmostEqual(first.count(4) / 20000, 0.05, delta=0.01)


class Race(unittest.TestCase):
    def setUp(self):
        self.t = Tavern()
        self.t.tokens = 100
        self.g = sn.SnailRace(random.Random(4))

    def test_needs_pick_and_min_bet(self):
        self.assertFalse(self.g.start(self.t))
        self.assertFalse(self.g.add_bet(self.t, 10))                    # улитка не выбрана — фишку некуда класть
        self.assertEqual(self.t.tokens, 100)
        self.g.select(2)
        self.g.clear_bet(self.t)
        self.g.add_bet(self.t, sn.MIN_BET - 1)
        self.assertFalse(self.g.start(self.t))
        self.assertEqual(self.t.tokens, 100 - (sn.MIN_BET - 1))

    def test_paid_at_start_and_progress_matches_order(self):
        self.g.select(1)
        self.g.add_bet(self.t, 20)
        self.assertTrue(self.g.start(self.t, random.Random(5)))
        self.assertEqual(self.t.tokens, 80 + self.g.paid)
        self.assertEqual(self.g.paid > 0, self.g.won())
        for i in range(5):                                                # ползут только вперёд и доползают
            prev = 0.0
            for k in range(200):
                p = self.g.progress(i, k * 0.1)
                self.assertGreaterEqual(p + 1e-9, prev)
                prev = p
            self.assertEqual(self.g.progress(i, self.g.race_length() + 1), 1.0)
        by_time = sorted(range(5), key=lambda i: self.g.times[i])
        self.assertEqual(by_time, self.g.order)                          # финишируют в порядке итога

    def test_next_round_keeps_pick_and_bet(self):
        self.g.select(3)
        self.g.add_bet(self.t, 10)
        self.g.start(self.t)
        self.g.finish()
        old = [o["k"] for o in self.g.odds]
        tokens = self.t.tokens
        self.assertTrue(self.g.next_round(self.t, rng=random.Random(9)))
        self.assertEqual((self.g.state, self.g.pick, self.g.bet), ("bet", 3, 10))
        self.assertEqual(self.t.tokens, tokens - 10)
        self.assertNotEqual(old, [o["k"] for o in self.g.odds])

    def test_chips_stay_on_their_snail(self):
        """3.40.1: выбрал, поставил, выбрал другую, поставил — фишки не переезжают."""
        self.g.select(0)
        self.g.add_bet(self.t, 10)
        self.g.select(3)
        self.g.add_bet(self.t, 25)
        self.g.add_bet(self.t, 5)
        self.assertEqual(self.g.bets, [10, 0, 0, 30, 0])
        self.assertEqual((self.g.bet, self.t.tokens), (40, 60))
        self.g.clear_bet(self.t, 3)                                     # «Убрать» с выбранной
        self.assertEqual((self.g.bets, self.t.tokens), ([10, 0, 0, 0, 0], 90))

    def test_pays_only_the_winner_stack(self):
        self.t.tokens = 1000
        for i, b in ((1, 20), (4, 10)):
            self.g.select(i)
            self.g.add_bet(self.t, b)
        self.g.start(self.t, random.Random(7))
        w = self.g.winner()
        want = int(round(self.g.bets[w] * self.g.odds[w]["k"]))
        self.assertEqual(self.g.paid, want)
        self.assertEqual(self.g.won(), w in (1, 4))
        self.assertEqual(self.t.tokens, 970 + want)

    def test_net_counts_lost_stacks(self):
        """3.40.3: ставки на 4 улитки — выплата за победителя, остальные сгорают; чистыми считаем всё."""
        self.t.tokens = 1000
        for i, b in ((0, 10), (1, 25), (2, 10), (3, 25)):
            self.g.select(i)
            self.g.add_bet(self.t, b)
        sn.FORCE_NEXT = True                                   # первой — самая большая стопка
        self.g.start(self.t, random.Random(8))
        w = self.g.winner()
        self.assertEqual(self.g.net(), self.g.paid - 70)
        self.assertEqual(self.t.tokens, 1000 + self.g.net())
        self.assertTrue(self.g.won())

    def test_covering_everything_still_loses_on_average(self):
        rnd = random.Random(11)
        total = 0
        for _ in range(5000):
            t = Tavern()
            t.tokens = 100
            g = sn.SnailRace(rnd)
            for i in range(5):
                g.select(i)
                g.add_bet(t, 10)
            g.start(t, rnd)
            total += g.net()
        self.assertLess(total, 0)                              # на всех сразу — в среднем минус ~5%

    def test_next_round_repeats_all_stacks(self):
        for i in (0, 2):
            self.g.select(i)
            self.g.add_bet(self.t, 10)
        self.g.start(self.t)
        self.g.finish()
        tokens = self.t.tokens
        self.g.next_round(self.t)
        self.assertEqual(self.g.bets, [10, 0, 10, 0, 0])
        self.assertEqual(self.t.tokens, tokens - 20)

    def test_refund_when_leaving(self):
        self.g.select(0)
        self.g.add_bet(self.t, 25)
        self.g.refund(self.t)
        self.assertEqual((self.t.tokens, self.g.bet), (100, 0))

    def test_force_next(self):
        for want in (True, False):
            g = sn.SnailRace(random.Random(6))
            g.select(4)
            g.add_bet(self.t, 10)
            sn.FORCE_NEXT = want
            g.start(self.t)
            self.assertEqual(g.won(), want)
            self.assertIsNone(sn.FORCE_NEXT)

    def test_unlocked_in_fishing_village(self):
        self.assertFalse(sn.unlocked(2))
        self.assertTrue(sn.unlocked(3))

    def test_intro_flag_saved(self):
        t = Tavern()
        t.sn_intro = True
        t2 = Tavern()
        t2.from_dict(t.to_dict())
        self.assertTrue(t2.sn_intro)


if __name__ == "__main__":
    unittest.main()


class SnailAchievements(unittest.TestCase):
    def test_snail_medals_on_sheet_seven(self):
        from farmgame.achievements import ACHIEVEMENTS
        ids = [a["id"] for a in ACHIEVEMENTS]
        ids = ids[:43] + ["_unused"] * 2 + ids[43:]                    # как в spritefit._ach_orders
        self.assertEqual(ids[54:56], ["snail_1", "snail_2"])           # 55-я и 56-я клетки = лист 7, первые две

    def test_race_counts_for_medal(self):
        from farmgame import achievements as ach
        t = Tavern()
        for _ in range(30):
            t.on("snail_race")
        done = [a["id"] for a in ach.ACHIEVEMENTS if a["id"] == "snail_1" and ach.value(a, None, t) >= a["target"]]
        self.assertEqual(done, ["snail_1"])
