# -*- coding: utf-8 -*-
"""3.34: достижения и разговоры с барменом."""
import datetime
import json
import random
import unittest

from tests.helpers import summer_farm
from farmgame import achievements as ach
from farmgame import barman_talk as bt
from farmgame.config import PRIZES
from farmgame.tavern import Tavern


class Achievements(unittest.TestCase):
    def setUp(self):
        self.f, self.t = summer_farm(), Tavern()

    def test_ids_unique_and_prizes_exist(self):
        ids = [a["id"] for a in ach.ACHIEVEMENTS]
        self.assertEqual(len(ids), len(set(ids)))
        prize_ids = {p["id"] for p in PRIZES}
        for a in ach.ACHIEVEMENTS:
            self.assertIn(a["sec"], dict(ach.SECTIONS))
            if a["prize"]:
                self.assertIn(a["prize"], prize_ids)
        for p in PRIZES:                      # каждый трофей «за достижение» кто-то выдаёт
            if p.get("achievement"):
                self.assertEqual(ach.BY_ID[p["achievement"]]["prize"], p["id"])

    def test_events_count_even_when_tavern_closed(self):
        self.assertFalse(self.t.unlocked)
        self.t.on("squirrel", 10)
        self.assertEqual(self.t.stats["squirrel"], 10)
        new = [a["id"] for a in ach.check(self.f, self.t)]
        self.assertIn("squirrel_1", new)
        self.assertNotIn("squirrel_2", new)
        self.assertEqual(ach.check(self.f, self.t), [])          # повторно то же самое не «выполняется»

    def test_trophy_given_at_once_tokens_on_claim(self):
        self.t.on("squirrel", 100)
        ach.check(self.f, self.t)
        self.assertTrue(self.t.prizes.get("golden_squirrel"))
        before = self.t.tokens
        self.assertEqual(ach.claim(self.t, "squirrel_3"), 50)
        self.assertEqual(ach.claim(self.t, "squirrel_3"), 0)          # дважды не дают
        self.assertEqual(self.t.tokens, before + 50)
        got = ach.claim_all(self.t)
        self.assertEqual(got, 10 + 25)                                 # squirrel_1 и squirrel_2
        self.assertEqual(ach.claimable(self.t), [])

    def test_farm_based(self):
        self.f.total_earned = 2e12
        self.f.farm_index = 1
        ids = {a["id"] for a in ach.check(self.f, self.t)}
        self.assertTrue({"earned_1", "earned_2", "earned_3", "chapter_1"} <= ids)
        self.assertNotIn("earned_4", ids)

    def test_old_saves_count_trucks_and_dailies(self):
        self.f.prestiges = 30
        self.t.daily_done_total = 12
        ids = {a["id"] for a in ach.check(self.f, self.t)}
        self.assertTrue({"truck_1", "truck_2", "daily_1"} <= ids)

    def test_save_roundtrip(self):
        self.t.on("collect", 150)
        ach.check(self.f, self.t)
        ach.claim(self.t, "collect_1")
        self.t.talk_story = 3
        t2 = Tavern()
        t2.from_dict(json.loads(json.dumps(self.t.to_dict())))
        self.assertEqual(t2.stats["collect"], 150)
        self.assertEqual(t2.ach_done, self.t.ach_done)
        self.assertEqual(t2.ach_claimed, ["collect_1"])
        self.assertEqual(t2.talk_story, 3)

    def test_broken_save_is_ignored(self):
        t2 = Tavern()
        t2.from_dict({"stats": {"collect": "много", "x": -5, 3: 4}, "ach_done": "все", "ach_claimed": [1, "a", "a"]})
        self.assertEqual(t2.stats, {})
        self.assertEqual(t2.ach_done, [])
        self.assertEqual(t2.ach_claimed, ["a"])


class BarmanTalk(unittest.TestCase):
    def setUp(self):
        self.f, self.t = summer_farm(), Tavern()

    def test_every_topic_answers(self):
        for key, _title in bt.TOPICS:
            text = bt.answer(key, self.f, self.t, random.Random(1))
            self.assertTrue(isinstance(text, str) and len(text) > 5, key)

    def test_stories_go_in_order(self):
        a = bt.answer("story", self.f, self.t)
        b = bt.answer("story", self.f, self.t)
        self.assertEqual((a, b), (bt.STORIES[0], bt.STORIES[1]))

    def test_mood_by_time(self):
        self.assertEqual(bt.part_of_day(datetime.datetime(2026, 1, 1, 8)), "morning")
        self.assertEqual(bt.part_of_day(datetime.datetime(2026, 1, 1, 2)), "night")

    def test_news_mentions_achievement_reward(self):
        self.t.on("squirrel", 10)
        ach.check(self.f, self.t)
        self.assertIn("достижение", bt.news(self.f, self.t))

    def test_tip_about_leaves(self):
        self.f.leaves = self.f.home_leaves = 500
        self.assertIn("листьев", bt.tip(self.f, self.t, random.Random(0)))


if __name__ == "__main__":
    unittest.main()
