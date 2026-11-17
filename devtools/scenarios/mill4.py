set_medieval(); f=A.farm
f.m_levels=[3,2]; f.m_workers=[2,1]; f.peasants=6
f.hopper=f.hopper_cap()*0.7; f.flour=A.mill_rate()*30; f.bread=A.bread_batch()*2; f.oven_load=1e8; f.oven_prog=8
A.view="barn"; A.toasts.clear()
for i in range(90): frames(1, 1/30)
A.toasts.clear(); frames(1); snap("mill_a")
print("miller", round(A.miller_x), A.miller_carry, "spin", round(A.mill_spin,2))
f.hopper=0
for i in range(60): A.update(1/30); A.t_real+=1/30
print("after stop", round(A.miller_x), A.miller_carry, round(A.mill_spin,2))
for i in range(120): A.update(1/30); A.t_real+=1/30
x=A.miller_x; print("idle", round(x), A.miller_carry, round(A.mill_spin,2))
f.hopper=f.hopper_cap()*0.3
A.update(1/30); A.update(1/30); print("resume from", round(A.miller_x), A.miller_carry)
for i in range(40): A.update(1/30); A.t_real+=1/30
print("moving", round(A.miller_x), A.miller_carry)
A.mill_angle=0.7; frames(1); snap("mill_b")
