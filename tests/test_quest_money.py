# -*- coding: utf-8 -*-
"""3.32: деньги за задания таверны — минуты дохода с потолком от цены следующей закрытой грядки."""
import unittest

from tests.helpers import summer_farm
from farmgame import tavern as tv


def income_minutes(f, minutes):
    return sum(f.income_per_sec(i, False) for i in range(len(f.levels))) * 60 * minutes


class QuestMoney(unittest.TestCase):
    def test_daily_never_buys_a_new_bed(self):
        f = summer_farm()                       # тыква (9-я грядка) закрыта
        bed = f.cost(8, 1)
        for diff, (minutes, _tok) in tv.DAILY_REWARD.items():
            self.assertLess(tv.quest_money(f, minutes), bed)

    def test_weekly_buys_at_most_one_bed(self):
        f = summer_farm()
        self.assertLessEqual(tv.quest_money(f, tv.WEEKLY_REWARD["minutes"]), f.cost(8, 1) + 1e-6)

    def test_minutes_rule_when_cap_is_far(self):
        f = summer_farm()
        f.levels = [10, 0, 0, 0, 0, 0, 0, 0, 0]          # начало забега: потолок (половина моркови) не мешает?
        self.assertLessEqual(tv.quest_money(f, 3), 0.25 * f.cost(1, 1) + 1e-6)
        f.levels = [200, 100, 100, 50, 50, 50, 25, 10, 5]   # все грядки открыты — потолка нет
        self.assertAlmostEqual(tv.quest_money(f, 3), income_minutes(f, 3))

    def test_harder_task_pays_more(self):
        f = summer_farm()
        pays = [tv.quest_money(f, m) for m, _t in tv.DAILY_REWARD.values()]
        self.assertEqual(pays, sorted(pays))
        self.assertLess(pays[0], pays[-1])

    def test_old_owed_rewards_are_capped(self):
        f = summer_farm()
        self.assertLessEqual(tv.quest_money(f, 40), 0.6 * f.cost(8, 1) + 1e-6)
        self.assertLessEqual(tv.quest_money(f, 180), f.cost(8, 1) + 1e-6)

    def test_boost_does_not_inflate_reward(self):
        f = summer_farm()
        f.levels[8] = 5
        plain = tv.quest_money(f, 5)
        f.boost_left = 60
        self.assertAlmostEqual(tv.quest_money(f, 5), plain)

    def test_rewards_are_smaller_than_before(self):
        self.assertEqual({d: m for d, (m, _t) in tv.DAILY_REWARD.items()}, {1: 3, 2: 5, 3: 8})
        self.assertEqual(tv.WEEKLY_REWARD["minutes"], 30)


if __name__ == "__main__":
    unittest.main()
