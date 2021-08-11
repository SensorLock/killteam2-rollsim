from ast import Str
from collections import namedtuple
from itertools import product
import numpy as np
import pandas as pd
import plotly.express as px


Fighter = namedtuple("Fighter", "name a ws dmg dmg_crit wounds keyword")

fighters = [
    Fighter("T Power", 4, 3, 4, 6, 7, {"lethal": 5}),
    Fighter("T Bayonet", 3, 4, 2, 3, 7, {}),
    Fighter("H Blade", 5, 3, 4, 5, 8, {"balanced": None}),
    Fighter("H Caress", 5, 4, 5, 6, 8, {}),
    Fighter("H Embrace", 5, 3, 4, 5, 8, {"brutal": None}),
    Fighter("H Kiss", 5, 3, 3, 7, 8, {}),
    Fighter("KN Big Choppa", 4, 2, 5, 6, 13, {}),
    Fighter("KN Power Klaw", 4, 3, 5, 7, 13, {"brutal": None}),
    Fighter("C Guardian Spear", 5, 2, 5, 7, 18, {"lethal": 5}),
    Fighter("C Sentinel Blade", 5, 2, 4, 6, 18, {"lethal": 5, "storm_shield": None}),
]

class Melee:
    def __init__(self, attacker, defender, strategy_attacker, strategy_defender):
        self.attacker = attacker
        self.defender = defender
        self.strategy_attacker = strategy_attacker
        self.strategy_defender = strategy_defender

    @staticmethod
    def do_rerolls(datacard, rolls):
        rerolls = 0
        if "relentless" in datacard.keyword:
            rerolls = (rolls < datacard.ws).sum()
        elif "balanced" in datacard.keyword:
            if any(rolls < datacard.ws):
                rerolls = 1
        elif "ceaseless" in datacard.keyword:
            if any(rolls == 1):
                rerolls = 1

        if rerolls:
            rolls = np.concatenate((rolls, np.random.choice(6, (rerolls,)) + 1))
        
        return rolls

    def simulate(self):
        # TODO assists from nearby allies
        a_rolls = np.random.choice(6, (self.attacker.a,)) + 1
        a_rolls = self.do_rerolls(self.attacker, a_rolls)
        a_to_crit = self.attacker.keyword.get("lethal", 6)
        a_crits = (a_rolls >= a_to_crit).sum()
        a_hits = (a_rolls >= self.attacker.ws).sum() - a_crits

        d_rolls = np.random.choice(6, (self.defender.a,)) + 1
        d_rolls = self.do_rerolls(self.defender, d_rolls)
        d_to_crit = self.defender.keyword.get("lethal", 6)
        d_crits = (d_rolls >= d_to_crit).sum()
        d_hits = (d_rolls >= self.defender.ws).sum() - d_crits
        
        if "rending" in self.attacker.keyword and a_crits > 0 and a_hits > 0:
            a_hits -= 1
            a_crits += 1

        if "rending" in self.defender.keyword and d_crits > 0 and d_hits > 0:
            d_hits -= 1
            d_crits += 1

        a_wounds_taken = 0
        d_wounds_taken = 0

        while (a_crits + a_hits + d_crits + d_hits) > 0:
            a_crits, a_hits, d_crits, d_hits, d_wounds_taken = self.strategy_attacker(self.attacker, self.defender,
                                                                                      a_crits, a_hits, d_crits, d_hits, d_wounds_taken)
            if d_wounds_taken >= self.defender.wounds:
                d_wounds_taken = self.defender.wounds
                break

            d_crits, d_hits, a_crits, a_hits, a_wounds_taken = self.strategy_defender(self.defender, self.attacker,
                                                                                      d_crits, d_hits, a_crits, a_hits, a_wounds_taken)
            if a_wounds_taken >= self.attacker.wounds:
                a_wounds_taken = self.attacker.wounds
                break

        return (a_wounds_taken, d_wounds_taken)


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
        # TODO does the storm shield actually work like this for crits and converted crits?
        shield_mult = 2 if "storm_shield" in me.keyword else 1
        if my_crits > 0:
            my_crits -= 1
            if opp_wounds_taken + me.dmg_crit >= opp.wounds:
                opp_wounds_taken += me.dmg_crit
            elif opp_crits > 0:
                opp_crits -= min(1 * shield_mult, opp_crits)
            elif opp_hits > 0:
                opp_hits -= min(1 * shield_mult, opp_hits)
            else:
                opp_wounds_taken += me.dmg_crit
        elif my_hits > 0:
            my_hits -= 1
            if ("brutal" in opp.keyword) or (opp_wounds_taken + me.dmg >= opp.wounds):
                opp_wounds_taken += me.dmg
            elif opp_crits > 0 and my_hits > 0:
                # Subtract 1 more of my hits to block a crit (may be better approaches based on dmg_crit vs dmg)
                opp_crits -= min(1 * shield_mult, opp_crits)
                my_hits -= 1
            elif opp_hits > 0:
                opp_hits -= min(1 * shield_mult, opp_hits)
            else:
                opp_wounds_taken += me.dmg

        return my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken


    @staticmethod
    def aggressive(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # Go for the kill, but fall back to parrying if you don't have enough damage left to kill
        # This doesn't consider ahead of time the number of available parries the opponent may take
        if my_crits * me.dmg_crit + my_hits * me.dmg + opp_wounds_taken > opp.wounds:
            return Melee.berzerker(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)
        else:
            return Melee.parry_riposte(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)

    @staticmethod
    def overpower(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken):
        # If you have enough crits+hits to push through all their parries to kill then go on the attack
        usable_crits = max(my_crits - opp_crits, 0)
        # TODO OPEN Q: crit conversion for melee
        carryover = max(opp_crits - my_hits, 0)
        usable_hits = max(my_hits - opp_hits - carryover, 0)
        
        if usable_crits * me.dmg_crit + usable_hits * me.dmg + opp_wounds_taken > opp.wounds:
            return Melee.berzerker(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)
        else:
            return Melee.parry_riposte(me, opp, my_crits, my_hits, opp_crits, opp_hits, opp_wounds_taken)

    # TODO another strategy consideration: if I know opp will kill me and have no way to stop it, then go max dmg
    #   also, examining if opponent has enough dmg to kill me in overpower scenario

if __name__ == "__main__":
    strategies = [Melee.berzerker, Melee.parry_riposte]

    all_dfs = []
    kill_probs = []
    for attacker, defender, a_strategy, d_strategy in product(fighters[6:8], fighters[8:], strategies, strategies):
        melee = Melee(attacker, defender, a_strategy, d_strategy)
        damage = np.array([melee.simulate() for _ in range(1000)])
        data = pd.DataFrame(damage, columns=["A dmg", "D dmg"])
        data = data.groupby(["A dmg", "D dmg"]).size().reset_index(name="count")
        data["A"] = f"{attacker.name}:{a_strategy.__name__}"
        data["D"] = f"{defender.name}:{d_strategy.__name__}"
        all_dfs.append(data)

    df = pd.concat(all_dfs)
    fig = px.scatter(df, x="D dmg", y="A dmg", facet_row="A", facet_col="D", size="count")
    fig.show()
