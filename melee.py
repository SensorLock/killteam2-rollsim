from collections import namedtuple
from itertools import product
import numpy as np

Fighter = namedtuple("Fighter", "name num to_hit to_crit dmg dmg_crit mws fnp wounds")

# TODO OPEN Q: are all hits resolved? or just until one model dies?
# TODO OPEN Q: how are opposing crits parried? can you use 2 hits to parry a crit?

class StrategyBerzerker:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender

    def __call__(self, params):
        a_crits, a_hits, a_wounds_taken, d_crits, d_hits, d_wounds_taken = params

        while (a_crits + a_hits + d_crits + d_hits) > 0:
            if a_wounds_taken >= self.attacker.wounds:
                break

            # BLOCK NOTHING!
            if a_crits > 0:
                a_crits -= 1
                d_wounds_taken += self.attacker.dmg_crit
            elif a_hits > 0:
                a_hits -= 1
                d_wounds_taken += self.attacker.dmg
            
            if d_wounds_taken >= self.defender.wounds:
                break

            # BLOCK NOTHING!
            if d_crits > 0:
                d_crits -= 1
                a_wounds_taken += self.defender.dmg_crit
            elif d_hits > 0:
                d_hits -= 1
                a_wounds_taken += self.defender.dmg
        
        return a_wounds_taken, d_wounds_taken


class StrategyAttackerParry:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender

    def __call__(self, params):
        a_crits, a_hits, a_wounds_taken, d_crits, d_hits, d_wounds_taken = params

        while (a_crits + a_hits + d_crits + d_hits) > 0:
            if a_wounds_taken >= self.attacker.wounds:
                break

            # PARRY EVERYTHING! (unless there is a lethal riposte)!
            if a_crits > 0:
                a_crits -= 1
                if d_wounds_taken + self.attacker.dmg_crit >= self.defender.wounds:
                    d_wounds_taken += self.attacker.dmg_crit
                elif d_crits > 0:
                    d_crits -= 1
                elif d_hits > 0:
                    d_hits -= 1
                else:
                    d_wounds_taken += self.attacker.dmg_crit
            elif a_hits > 0:
                a_hits -= 1
                if d_wounds_taken + self.attacker.dmg >= self.defender.wounds:
                    d_wounds_taken += self.attacker.dmg
                elif d_hits > 0:
                    d_hits -= 1
                else:
                    d_wounds_taken += self.attacker.dmg
            
            if d_wounds_taken >= self.defender.wounds:
                break

            # BLOCK NOTHING!
            if d_crits > 0:
                d_crits -= 1
                a_wounds_taken += self.defender.dmg_crit
            elif d_hits > 0:
                d_hits -= 1
                a_wounds_taken += self.defender.dmg
        
        return a_wounds_taken, d_wounds_taken


class StrategyDefenderParry:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender

    def __call__(self, params):
        a_crits, a_hits, a_wounds_taken, d_crits, d_hits, d_wounds_taken = params

        while (a_crits + a_hits + d_crits + d_hits) > 0:
            if a_wounds_taken >= self.attacker.wounds:
                break

            # BLOCK NOTHING!
            if a_crits > 0:
                a_crits -= 1
                d_wounds_taken += self.attacker.dmg_crit
            elif a_hits > 0:
                a_hits -= 1
                d_wounds_taken += self.attacker.dmg
            
            if d_wounds_taken >= self.defender.wounds:
                break

            # PARRY EVERYTHING! (unless there is a lethal riposte)
            if d_crits > 0:
                d_crits -= 1
                if a_wounds_taken + self.defender.dmg_crit >= self.attacker.wounds:
                    a_wounds_taken += self.defender.dmg_crit
                elif a_crits > 0:
                    a_crits -= 1
                elif a_hits > 0:
                    a_hits -= 1
                else:
                    a_wounds_taken += self.defender.dmg_crit
            elif d_hits > 0:
                d_hits -= 1
                if a_wounds_taken + self.defender.dmg >= self.attacker.wounds:
                    a_wounds_taken += self.defender.dmg
                elif a_hits > 0:
                    a_hits -= 1
                else:
                    a_wounds_taken += self.defender.dmg
        
        return a_wounds_taken, d_wounds_taken


class StrategyMaxParry:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender

    def __call__(self, params):
        a_crits, a_hits, a_wounds_taken, d_crits, d_hits, d_wounds_taken = params

        while (a_crits + a_hits + d_crits + d_hits) > 0:
            if a_wounds_taken >= self.attacker.wounds:
                break

            # PARRY EVERYTHING! (unless there is a lethal riposte)!
            if a_crits > 0:
                a_crits -= 1
                if d_wounds_taken + self.attacker.dmg_crit >= self.defender.wounds:
                    d_wounds_taken += self.attacker.dmg_crit
                elif d_crits > 0:
                    d_crits -= 1
                elif d_hits > 0:
                    d_hits -= 1
                else:
                    d_wounds_taken += self.attacker.dmg_crit
            elif a_hits > 0:
                a_hits -= 1
                if d_wounds_taken + self.attacker.dmg >= self.defender.wounds:
                    d_wounds_taken += self.attacker.dmg
                elif d_hits > 0:
                    d_hits -= 1
                else:
                    d_wounds_taken += self.attacker.dmg
            
            if d_wounds_taken >= self.defender.wounds:
                break

            # PARRY EVERYTHING! (unless there is a lethal riposte)
            if d_crits > 0:
                d_crits -= 1
                if a_wounds_taken + self.defender.dmg_crit >= self.attacker.wounds:
                    a_wounds_taken += self.defender.dmg_crit
                elif a_crits > 0:
                    a_crits -= 1
                elif a_hits > 0:
                    a_hits -= 1
                else:
                    a_wounds_taken += self.defender.dmg_crit
            elif d_hits > 0:
                d_hits -= 1
                if a_wounds_taken + self.defender.dmg >= self.attacker.wounds:
                    a_wounds_taken += self.defender.dmg
                elif a_hits > 0:
                    a_hits -= 1
                else:
                    a_wounds_taken += self.defender.dmg
        
        return a_wounds_taken, d_wounds_taken


def simulate_melee(attacker: Fighter, defender: Fighter, strategy, samples=100000):
    # Roll a bunch of dice in atk and def groups
    a_rolls = np.random.choice(6, (samples, attacker.num)) + 1
    d_rolls = np.random.choice(6, (samples, defender.num)) + 1
    
    a_crits = (a_rolls >= attacker.to_crit).sum(axis=1)
    a_hits = (a_rolls >= attacker.to_hit).sum(axis=1) - a_crits

    d_crits = (d_rolls >= defender.to_crit).sum(axis=1)
    d_hits = (d_rolls >= defender.to_hit).sum(axis=1) - d_crits

    results = np.stack((a_crits, a_hits, d_crits * defender.mws,
                        d_crits, d_hits, a_crits * attacker.mws))
    wounds_taken = np.apply_along_axis(strategy, 0, results)

    a_wounds = wounds_taken[0]
    a_killed = (a_wounds >= attacker.wounds).sum()

    d_wounds = wounds_taken[1]
    d_killed = (d_wounds >= defender.wounds).sum()

    print(f"{attacker.name} fighting {defender.name} using {strategy.__class__.__name__}")
    print(f"Attacker wounds taken distribution: {np.bincount(a_wounds)}")
    print(f"Attacker avg. wounds taken: {a_wounds.mean()}")
    print(f"Attacker killed: {a_killed/samples * 100}%")
    print(f"Defender wounds taken distribution: {np.bincount(d_wounds)}")
    print(f"Defender avg. wounds taken: {d_wounds.mean()}")
    print(f"Defender killed: {d_killed/samples * 100}%")
    print()


fighters = [
    Fighter("Trooper Veteran (Power Weapon)", 4, 3, 5, 4, 6, 0, None, 7),
    Fighter("Trooper Veteran (Bayonet)", 3, 4, 6, 2, 3, 0, None, 7),
]

strategies = [StrategyBerzerker, StrategyAttackerParry, StrategyDefenderParry, StrategyMaxParry]
for attacker, defender, strategy in product(fighters, fighters, strategies):
    s = strategy(attacker, defender)
    simulate_melee(attacker, defender, s)
