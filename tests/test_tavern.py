# -*- coding: utf-8 -*-
"""Таверна: смена дня и недели, незабранные награды, чтение из сохранения."""
import datetime
import json
import unittest

from tests import helpers  # noqa: F401  (добавляет папку игры в путь)
from farmgame import config as cfg
from farmgame import tavern as tv

MEDIEVAL = cfg.FARMS[1]
SAT = datetime.datetime(2026, 11, 14, 23, 59)        # суббота
SUN = datetime.datetime(2026, 11, 15, 0, 0, 5)       # воскресенье, та же неделя
MON = datetime.datetime(2026, 11, 16, 0, 0, 5)       # понедельник, новая неделя


def fresh(now=SAT):
    t = tv.Tavern()
    t.unlocked = True
    t.refresh(MEDIEVAL, now=now)
    return t


def finish(q):
    q["progress"] = q["target"]


class Midnight(unittest.TestCase):
    def test_finished_rewards_are_not_lost(self):
        """Выполнил, но не забрал до полуночи — награда выдаётся сама (до 2.8 она сгорала)."""
        t = fresh()
        for q in t.daily:
            finish(q)
        want_tokens = sum(t.reward_of(q)[1] for q in t.daily)
        want_minutes = sum(t.reward_of(q)[0] for q in t.daily)
        self.assertTrue(t.refresh(MEDIEVAL, now=SUN))
        owed = t.take_owed()
        self.assertEqual(len(owed), tv.DAILY_COUNT)
        self.assertEqual(t.tokens, want_tokens)
        self.assertEqual(sum(o["minutes"] for o in owed), want_minutes)
        self.assertEqual(t.daily_done_total, tv.DAILY_COUNT)
        self.assertEqual(t.take_owed(), [])                       # второй раз не выдаётся
        self.assertTrue(all(q["progress"] == 0 and not q["claimed"] for q in t.daily))

    def test_unfinished_and_claimed_give_nothing(self):
        t = fresh()
        t.daily[0]["progress"] = t.daily[0]["target"] - 1 if t.daily[0]["target"] > 1 else 0
        finish(t.daily[1])
        t.claim(t.daily[1])
        tokens = t.tokens
        t.refresh(MEDIEVAL, now=SUN)
        self.assertEqual(t.take_owed(), [])
        self.assertEqual(t.tokens, tokens)

    def test_same_day_changes_nothing(self):
        t = fresh()
        before = json.dumps(t.to_dict())
        self.assertFalse(t.refresh(MEDIEVAL, now=SAT))
        self.assertEqual(json.dumps(t.to_dict()), before)

    def test_weekly_reward_is_kept_on_monday(self):
        t = fresh()
        finish(t.weekly)
        t.refresh(MEDIEVAL, now=MON)
        owed = t.take_owed()
        self.assertEqual([o["weekly"] for o in owed], [True])
        r = tv.WEEKLY_REWARD
        self.assertEqual((owed[0]["minutes"], owed[0]["prestige"], owed[0]["boost"]),
                         (r["minutes"], r["prestige"], r["boost_minutes"]))
        self.assertEqual(t.tokens, r["tokens"])
        self.assertEqual(t.weekly["progress"], 0)

    def test_auto_claimed_dailies_count_for_weekly(self):
        """Дневные, выданные автоматически, идут в зачёт «Завсегдатаю» — и он тоже не сгорает в понедельник."""
        t = fresh()
        t.weekly = dict(id="w_daily", title="Завсегдатай", text="", event="daily_done", need=None,
                        target=tv.DAILY_COUNT, progress=0, claimed=False)
        for q in t.daily:
            finish(q)
        t.refresh(MEDIEVAL, now=MON)
        owed = t.take_owed()
        self.assertEqual(len(owed), tv.DAILY_COUNT + 1)
        self.assertTrue(owed[-1]["weekly"])


class Saving(unittest.TestCase):
    def test_roundtrip_keeps_owed(self):
        t = fresh()
        finish(t.daily[0])
        t.refresh(MEDIEVAL, now=SUN)
        u = tv.Tavern()
        u.from_dict(json.loads(json.dumps(t.to_dict())))
        self.assertEqual(u.to_dict(), t.to_dict())
        self.assertEqual(len(u.owed), 1)

    def test_old_save_without_owed(self):
        t = fresh()
        d = t.to_dict()
        del d["owed"]
        u = tv.Tavern()
        u.from_dict(json.loads(json.dumps(d)))
        self.assertEqual(u.owed, [])
        self.assertEqual(u.daily, t.daily)

    def test_garbage_does_not_crash(self):
        good = fresh().to_dict()
        bad_values = [None, "abc", 5, [], {}, [None, 3, "x", {}], [{"id": 1}], float("nan"), True,
                      {"id": "x", "title": [], "text": {}, "event": None, "target": "many", "diff": [1]}]
        for key in list(good) + ["extra"]:
            for bad in bad_values:
                d = dict(good)
                d[key] = bad
                t = tv.Tavern()
                t.from_dict(d)                                  # не должно бросать
                t.refresh(MEDIEVAL, now=SUN)
                t.on("collect", 5)
                for q in t.claimable():
                    t.claim(q)
                for q in t.daily + [t.weekly]:
                    t.reward_of(q)
                json.dumps(t.to_dict())
                self.assertEqual(len(t.daily), tv.DAILY_COUNT)
        for bad in (None, [], "x", 7):
            tv.Tavern().from_dict(bad)

    def test_bad_difficulty_becomes_easy(self):
        t = fresh()
        d = t.to_dict()
        d["daily"][0]["diff"] = 99
        u = tv.Tavern()
        u.from_dict(d)
        self.assertEqual(u.daily[0]["diff"], 1)


class Texts(unittest.TestCase):
    def test_plural(self):
        self.assertEqual([tv.plural(n, "белку", "белки", "белок") for n in (1, 2, 5, 11, 21, 104)],
                         ["белку", "белки", "белок", "белок", "белку", "белки"])

    def test_every_quest_text_builds(self):
        t = tv.Tavern()
        for fm in cfg.FARMS:
            for q in tv.QUESTS:
                for lo, hi in q["targets"].values():
                    self.assertNotIn("{", t._quest_text(q, hi, fm))
            for q in tv.WEEKLY:
                self.assertNotIn("{", t._quest_text(q, q["n"][1], fm))


if __name__ == "__main__":
    unittest.main()
