# 3.31: дерево дорожает — окно дерева без выбора, с выбранным улучшением и тост после покупки
f = A.farm
f.levels = [200, 50, 50, 25, 10, 0, 0, 0, 0]
f.tree = {"capital": 3, "farmers": 4, "rain_len": 2, "fertile": 1}
f.leaves = f.home_leaves = 400
A.open_modal("tree"); A.skip_anims(); frames(30); snap("tree_none")
A.tree_sel = "lucky"; frames(10); snap("tree_sel")
A.buy_tree("lucky"); frames(20); snap("tree_bought")
