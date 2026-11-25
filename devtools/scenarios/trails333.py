# 3.33: шлейфы «Листопад» и «Мыльные пузыри», рубашка карт в блэкджеке
import math
from farmgame import blackjack as bjl
A.tavern.tokens = 5000
for pid in ("leaf_trail", "bubble_trail"):
    A.tavern.buy_prize(A.farm, pid)
    A.trail = [(300 + i * 12, 300 + 40 * math.sin(i * 0.4), A.t_real - 0.45 + i * 0.012) for i in range(38)]
    A.draw(); snap("tr_" + pid, crop=(250, 220, 800, 400))
