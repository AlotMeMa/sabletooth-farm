# -*- coding: utf-8 -*-
"""Обучение на первой ферме (3.9): бармен из «Хмельного колоса» коротко показывает, как играть. Без графики.

Как в хороших играх (Hay Day, Clash of Clans, Stardew Valley): учит делом, а не текстом — один шаг, одно
действие, стрелка показывает, куда нажать; шагов мало; пропустить можно в любой момент; пока открыто окно
или игрок ушёл с поля, обучение ждёт. Картинка — в tutorial_ui.py.

Шаг закрывается событием (то, что игрок сделал) или кнопкой «Дальше» у шагов-рассказов.
"""

STEPS = [
    dict(id="hello", wait=None),          # приветствие — кнопка «Поехали!»
    dict(id="collect", wait="collect"),   # собрать урожай
    dict(id="plant", wait="plant"),       # посадить новую грядку
    dict(id="upgrade", wait="buy_level"),  # прокачать грядку (режим «Прокачка»)
    dict(id="shop", wait="shop"),         # заглянуть в магазин
    dict(id="bye", wait=None),            # прощание — кнопка «Удачи!»
]
SKIP_AFTER = 12.0      # у шага с действием через столько секунд появляется «Дальше» (вдруг не хватает денег)


class Tutorial:
    def __init__(self, done=False):
        self.step = 0
        self.done = done
        self.t = 0.0           # сколько секунд идёт текущий шаг

    @property
    def current(self):
        return None if self.done else STEPS[self.step]

    def tick(self, dt):
        if not self.done:
            self.t += dt

    def on(self, event):
        """Игрок что-то сделал. True — шаг выполнен (обучение пошло дальше)."""
        cur = self.current
        if cur is None or cur["wait"] != event:
            return False
        self.next()
        return True

    def next(self):
        if self.done:
            return
        self.step += 1
        self.t = 0.0
        if self.step >= len(STEPS):
            self.finish()

    def finish(self):
        self.done = True
        self.step = len(STEPS) - 1

    def restart(self):
        self.done = False
        self.step = 0
        self.t = 0.0

    def can_skip_step(self):
        cur = self.current
        return cur is not None and (cur["wait"] is None or self.t >= SKIP_AFTER)

    # ---------- сохранение ----------
    def to_dict(self):
        return dict(step=self.step, done=self.done)

    @classmethod
    def from_save(cls, d):
        """Нет записи в сохранении — значит игрок со старой версией: учить его не надо."""
        if not isinstance(d, dict):
            return cls(done=True)
        t = cls(done=bool(d.get("done", True)))
        step = d.get("step", 0)
        if isinstance(step, int) and not isinstance(step, bool) and 0 <= step < len(STEPS):
            t.step = step
        return t
