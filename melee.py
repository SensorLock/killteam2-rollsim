from collections import namedtuple
from itertools import product
import numpy as np

Fighter = namedtuple("Fighter", "name num to_hit to_crit dmg dmg_crit mws fnp wounds")

# TODO OPEN Q: are all hits resolved? or just until one model dies?
# TODO OPEN Q: how are opposing crits parried? can you use 2 hits to parry a crit?

def strategy_berzerker(attacker, defender, a_crits, a_hits, d_crits, d_hits):
    # BLOCK NOTHING!
    pass


def strategy_max_parry(attacker, defender, a_crits, a_hits, d_crits, d_hits):
    crit_parries = np.minimum(a_crits, d_crits)
    hit_parries = np.minimum(a_hits, d_hits)
    a_crits -= crit_parries
    d_crits -= crit_parries
    a_hits -= hit_parries
    d_hits -= hit_parries


def simulate_melee(attacker: Fighter, defender: Fighter, strategy_func, samples=100000):
    # Roll a bunch of dice in atk and def groups
    a_rolls = np.random.choice(6, (samples, attacker.num)) + 1
    d_rolls = np.random.choice(6, (samples, defender.num)) + 1
    
    a_crits = (a_rolls >= attacker.to_crit).sum(axis=1)
    a_mws = a_crits * attacker.mws
    a_hits = (a_rolls >= attacker.to_hit).sum(axis=1) - a_crits

    d_crits = (d_rolls >= defender.to_crit).sum(axis=1)
    d_mws = d_crits * defender.mws
    d_hits = (d_rolls >= defender.to_hit).sum(axis=1) - d_crits

    strategy_func(attacker, defender, a_crits, a_hits, d_crits, d_hits)
    
    d_wounds = (a_mws + a_crits * attacker.dmg_crit + a_hits * attacker.dmg)
    a_wounds = (d_mws + d_crits * defender.dmg_crit + d_hits * defender.dmg)

    print(f"{attacker.name} fighting {defender.name} using {strategy_func.__name__}")
    print(f"Attacker wounds distribution: {np.bincount(a_wounds)}")
    print(f"Attacker avg. wounds taken: {a_wounds.mean()}")
    print(f"Defender wounds distribution: {np.bincount(d_wounds)}")
    print(f"Defender avg. wounds taken: {d_wounds.mean()}")
    print()


fighters = [
    Fighter("Trooper Veteran (Power Weapon)", 4, 3, 5, 4, 6, 0, None, 7),
    Fighter("Trooper Veteran (Bayonet)", 3, 4, 6, 2, 3, 0, None, 7),
]

for attacker, defender, strategy in product(fighters, fighters, [strategy_berzerker, strategy_max_parry]):
    simulate_melee(attacker, defender, strategy)
