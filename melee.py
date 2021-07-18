from ast import Str
from collections import namedtuple
from itertools import product
import numpy as np

Fighter = namedtuple("Fighter", "name num to_hit to_crit dmg dmg_crit mws fnp wounds")


class Strategy:
    def __init__(self, attacker, defender, strategy_attacker, strategy_defender):
        self.attacker = attacker
        self.defender = defender
        self.strategy_attacker = strategy_attacker
        self.strategy_defender = strategy_defender

    def __str__(self):
        return f"[Strategy: {self.strategy_attacker.__name__} into {self.strategy_defender.__name__}]"

    def __call__(self, params):
        a_crits, a_hits, a_wounds_taken, d_crits, d_hits, d_wounds_taken = params

        # TODO OPEN Q: are all hits resolved? or just until one model dies?
        # TODO OPEN Q: how are opposing crits parried? can you use 2 hits to parry a crit?
        while (a_crits + a_hits + d_crits + d_hits) > 0:
            if a_wounds_taken >= self.attacker.wounds:
                break
            
            a_crits, a_hits, d_crits, d_hits, d_wounds_taken = self.strategy_attacker(attacker, defender,
                                                                                      a_crits, a_hits, d_crits, d_hits, d_wounds_taken)
            
            if d_wounds_taken >= self.defender.wounds:
                break

            d_crits, d_hits, a_crits, a_hits, a_wounds_taken = self.strategy_defender(defender, attacker,
                                                                                      d_crits, d_hits, a_crits, a_hits, a_wounds_taken)
        
        return a_wounds_taken, d_wounds_taken


    @staticmethod
    def berzerker(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # BLOCK NOTHING!
        if my_crits > 0:
            my_crits -= 1
            opp_wounds_taken += me.dmg
        elif my_hits > 0:
            my_hits -= 1
            opp_wounds_taken += me.dmg_crit
            
        return my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken


    @staticmethod
    def parry_riposte(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # PARRY EVERYTHING! (unless there is a lethal riposte)!
        if my_crits > 0:
            my_crits -= 1
            if opp_wounds_taken + me.dmg_crit >= opp.wounds:
                opp_wounds_taken += me.dmg_crit
            elif opp_crits > 0:
                opp_crits -= 1
            elif opp_hits > 0:
                # TODO OPEN Q: crit conversion for melee
                opp_hits -= 1
            else:
                opp_wounds_taken += me.dmg_crit
        elif my_hits > 0:
            my_hits -= 1
            if opp_wounds_taken + me.dmg >= opp.wounds:
                opp_wounds_taken += me.dmg
            elif opp_hits > 0:
                opp_hits -= 1
            else:
                opp_wounds_taken += me.dmg

        return my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken


    @staticmethod
    def aggressive(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # Go for the kill, but fall back to parrying if you don't have enough damage left to kill
        # This doesn't consider ahead of time the number of available parries the opponent may take
        if my_crits * me.dmg_crit + my_hits * me.dmg + opp_wounds_taken > opp.wounds:
            return Strategy.berzerker(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)
        else:
            return Strategy.parry_riposte(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)

    @staticmethod
    def overpower(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # If you have enough crits+hits to push through all their parries to kill then go on the attack
        usable_crits = max(my_crits - opp_crits, 0)
        # TODO OPEN Q: crit conversion for melee
        carryover = max(opp_crits - my_hits, 0)
        usable_hits = max(my_hits - opp_hits - carryover, 0)
        
        if usable_crits * me.dmg_crit + usable_hits * me.dmg + opp_wounds_taken > opp.wounds:
            return Strategy.berzerker(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)
        else:
            return Strategy.parry_riposte(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)


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

    print(f"{attacker.name} fighting {defender.name} using {str(strategy)}")
    print(f"Attacker wounds taken distribution: {np.bincount(a_wounds)}")
    print(f"Attacker avg. wounds taken: {a_wounds.mean()}")
    print(f"Attacker killed: {a_killed/samples * 100}%")
    print(f"Defender wounds taken distribution: {np.bincount(d_wounds)}")
    print(f"Defender avg. wounds taken: {d_wounds.mean()}")
    print(f"Defender killed: {d_killed/samples * 100}%")
    print()


fighters = [
    Fighter("Trooper Veteran (Power Weapon)", 4, 3, 5, 4, 6, 0, None, 7),
    # Fighter("Trooper Veteran (Bayonet)", 3, 4, 6, 2, 3, 0, None, 7),
]

strategies = [Strategy.berzerker, Strategy.aggressive, Strategy.parry_riposte, Strategy.overpower]
for attacker, defender, a_strategy, d_strategy in product(fighters, fighters, strategies, strategies):
    s = Strategy(attacker, defender, a_strategy, d_strategy)
    simulate_melee(attacker, defender, s)
