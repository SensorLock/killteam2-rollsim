from collections import namedtuple
from itertools import product
import numpy as np
import pandas as pd
import plotly.express as px


Fighter = namedtuple("Fighter", "name a ws dmg dmg_crit wounds keyword")

fighters = [
    Fighter("Stealer 2RC", 5, 3, 4, 5, 9, {"relentless": None, "rending": None}),
    Fighter("Bayonet", 3, 4, 2, 3, 7, {}),
    Fighter("CSM AC PW", 5, 2, 4, 6, 13, {"lethal": 5}),
    Fighter("Nob Power Klaw", 4, 3, 5, 7, 13, {"brutal": None}),
    Fighter("Custodes B+SS", 5, 2, 4, 6, 18, {"lethal": 5, "storm_shield": None}),
    
]


MeleeState = namedtuple("MeleeState", "crits hits wounds_remaining dmg dmg_crit brutal storm_shield")


class Melee:
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender

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
        a_a = self.attacker.a
        d_a = self.defender.a

        if "lashwhip" in self.defender.keyword:
            a_a -= 1
        if "lashwhip" in self.attacker.keyword:
            d_a -= 1
        
        a_rolls = np.random.choice(6, (a_a,)) + 1
        a_rolls = self.do_rerolls(self.attacker, a_rolls)
        a_to_crit = self.attacker.keyword.get("lethal", 6)
        a_crits = (a_rolls >= a_to_crit).sum()
        a_hits = (a_rolls >= self.attacker.ws).sum() - a_crits

        d_rolls = np.random.choice(6, (d_a,)) + 1
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

        if "ltgb" in self.attacker.keyword and any(a_rolls == (a_to_crit - 1)):
            a_hits -= 1
            a_crits += 1

        if "ltgb" in self.defender.keyword and any(d_rolls == (d_to_crit - 1)):
            d_hits -= 1
            d_crits += 1

        a_state = MeleeState(a_crits, a_hits,
                             self.attacker.wounds, self.attacker.dmg, self.attacker.dmg_crit,
                             "brutal" in self.attacker.keyword, "storm_shield" in self.attacker.keyword)
        d_state = MeleeState(d_crits, d_hits,
                             self.defender.wounds, self.defender.dmg, self.defender.dmg_crit,
                             "brutal" in self.defender.keyword, "storm_shield" in self.defender.keyword)
        
        a_wr, d_wr, trace = self.minimax(a_state, d_state, True)
        # print(trace)
        return (a_wr, d_wr)

    @staticmethod
    def minimax(a_state: MeleeState, d_state: MeleeState, attacker_turn: bool, trace=""):
        if a_state.wounds_remaining <= 0 or d_state.wounds_remaining <= 0 or \
            (a_state.crits == 0 and a_state.hits == 0 and d_state.crits == 0 and d_state.hits == 0):
            return (a_state.wounds_remaining, d_state.wounds_remaining, trace)

        # Striker and target state tuples based on attacker_turn
        s_state = a_state if attacker_turn else d_state
        t_state = d_state if attacker_turn else a_state

        children = []
        
        # Let opponent finish assigning dice
        if s_state.crits == 0 and s_state.hits == 0:
            children.append((s_state, t_state, trace+" "))
        
        # Strike hit
        if s_state.hits > 0:
            s_child = s_state._replace(hits=s_state.hits-1)
            t_child = t_state._replace(wounds_remaining=max(t_state.wounds_remaining - s_state.dmg, 0))
            children.append((s_child, t_child, trace+"s"))
            
        # Strike crit
        if s_state.crits > 0:
            s_child = s_state._replace(crits=s_state.crits-1)
            t_child = t_state._replace(wounds_remaining=max(t_state.wounds_remaining - s_state.dmg_crit, 0))
            children.append((s_child, t_child, trace+"S"))

        # Parry hit
        if s_state.hits > 0 and t_state.hits > 0 and not t_state.brutal:
            s_child = s_state._replace(hits=s_state.hits-1)
            t_child = t_state._replace(hits=t_state.hits-1)
            children.append((s_child, t_child, trace+"p"))

        # Parry crit
        if s_state.crits > 0 and t_state.crits > 0:
            s_child = s_state._replace(crits=s_state.crits-1)
            if s_state.storm_shield and t_state.crits >= 2:
                t_child = t_state._replace(crits=t_state.crits-2)
            elif s_state.storm_shield and t_state.hits > 0:
                t_child = t_state._replace(crits=t_state.crits-1, hits=t_state.hits-1)
            else:
                t_child = t_state._replace(crits=t_state.crits-1)
            children.append((s_child, t_child, trace+"P"))

        # Parry hit with crit
        if s_state.crits > 0 and t_state.hits > 0:
            s_child = s_state._replace(crits=s_state.crits-1)
            if s_state.storm_shield and t_state.hits >= 2:
                t_child = t_state._replace(hits=t_state.hits-2)
            else:
                t_child = t_state._replace(hits=t_state.hits-1)
            children.append((s_child, t_child, trace+"R"))

        if attacker_turn:
            values = [Melee.minimax(a, d, not attacker_turn, t) for a, d, t in children]
            return max(values, key=lambda x: x[0])
        else:
            values = [Melee.minimax(a, d, not attacker_turn, t) for d, a, t in children]
            return min(values, key=lambda x: x[0])


if __name__ == "__main__":
    all_dfs = []
    for attacker, defender in product(fighters, fighters):
        melee = Melee(attacker, defender)
        damage = np.array([melee.simulate() for _ in range(1000)])
        data = pd.DataFrame(damage, columns=["A WR", "D WR"])
        data = data.groupby(["A WR", "D WR"]).size().reset_index(name="count")

        nbinsx = int(data["D WR"].max() - data["D WR"].min() + 1)
        nbinsy = int(data["A WR"].max() - data["A WR"].min() + 1)
        # TODO lock z scale to have consistent colors
        fig = px.density_heatmap(data, x="D WR", y="A WR", z="count",
                                 marginal_x="box", marginal_y="box",
                                 title=f"{attacker.name} attacking {defender.name}",
                                 nbinsx=nbinsx, nbinsy=nbinsy, histnorm="probability")
        fig.show()
