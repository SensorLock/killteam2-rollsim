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


MeleeState = namedtuple("MeleeState", "atk_crits atk_hits atk_wounds_taken def_crits def_hits def_wounds_taken")


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

        state = MeleeState(a_crits, a_hits, 0, d_crits, d_hits, 0)
        wounds_remaining = self.minimax(state, True)
        return wounds_remaining


    def minimax(self, state: MeleeState, attacker_turn: bool):
        if state.atk_wounds_taken >= self.attacker.wounds or state.def_wounds_taken >= self.defender.wounds or \
            (state.atk_crits == 0 and state.atk_hits == 0 and state.def_crits == 0 and state.def_hits == 0):
            return (max(self.attacker.wounds - state.atk_wounds_taken, 0),
                    max(self.defender.wounds - state.def_wounds_taken, 0))

        if attacker_turn:
            value = []
            
            # Let opponent finish assigning dice
            if state.atk_crits == 0 and state.atk_hits == 0:
                value.append(self.minimax(state._replace(), not attacker_turn))
            
            # Strike hit
            if state.atk_hits > 0:
                child = state._replace(atk_hits=state.atk_hits-1,
                                       def_wounds_taken=state.def_wounds_taken+self.attacker.dmg)
                value.append(self.minimax(child, not attacker_turn))
        
            # Strike crit
            if state.atk_crits > 0:
                child = state._replace(atk_crits=state.atk_crits-1,
                                       def_wounds_taken=state.def_wounds_taken+self.attacker.dmg_crit)
                value.append(self.minimax(child, not attacker_turn))

            # Parry hit
            if state.atk_hits > 0 and state.def_hits > 0 and "brutal" not in self.defender.keyword:
                child = state._replace(atk_hits=state.atk_hits-1,
                                       def_hits=state.def_hits-1)
                value.append(self.minimax(child, not attacker_turn))

            # Parry crit
            if state.atk_crits > 0 and state.def_crits > 0:
                if "storm_shield" in self.attacker.keyword and state.def_crits >= 2:
                    child = state._replace(atk_crits=state.atk_crits-1,
                                           def_crits=state.def_crits-2)
                elif "storm_shield" in self.attacker.keyword and state.def_hits > 0:
                    child = state._replace(atk_crits=state.atk_crits-1,
                                           def_crits=state.def_crits-1,
                                           def_hits=state.def_hits-1)
                else:
                    child = state._replace(atk_crits=state.atk_crits-1,
                                           def_crits=state.def_crits-1)
                value.append(self.minimax(child, not attacker_turn))

            # Parry hit with crit
            if state.atk_crits > 0 and state.def_hits > 0:
                if "storm_shield" in self.attacker.keyword and state.def_hits >= 2:
                    child = state._replace(atk_crits=state.atk_crits-1,
                                           def_hits=state.def_hits-2)
                else:
                    child = state._replace(atk_crits=state.atk_crits-1,
                                           def_hits=state.def_hits-1)
                value.append(self.minimax(child, not attacker_turn))
        
            return max(value, key=lambda x: x[0])
        else:
            value = []

            # Let opponent finish assigning dice
            if state.def_crits == 0 and state.def_hits == 0:
                value.append(self.minimax(state._replace(), not attacker_turn))

            # Strike hit
            if state.def_hits > 0:
                child = state._replace(def_hits=state.def_hits-1,
                                       atk_wounds_taken=state.atk_wounds_taken + self.defender.dmg)
                value.append(self.minimax(child, not attacker_turn))
        
            # Strike crit
            if state.def_crits > 0:
                child = state._replace(def_crits=state.def_crits-1,
                                       atk_wounds_taken=state.atk_wounds_taken + self.defender.dmg_crit)
                value.append(self.minimax(child, not attacker_turn))

            # Parry hit
            if state.def_hits > 0 and state.atk_hits > 0 and "brutal" not in self.attacker.keyword:
                child = state._replace(def_hits=state.def_hits-1,
                                       atk_hits=state.atk_hits-1)
                value.append(self.minimax(child, not attacker_turn))

            # Parry crit
            if state.def_crits > 0 and state.atk_crits > 0:
                if "storm_shield" in self.defender.keyword and state.atk_crits >= 2:
                    child = state._replace(def_crits=state.def_crits-1,
                                           atk_crits=state.atk_crits-2)
                elif "storm_shield" in self.defender.keyword and state.atk_hits > 0:
                    child = state._replace(def_crits=state.def_crits-1,
                                           atk_crits=state.atk_crits-1,
                                           atk_hits=state.atk_hits-1)
                else:
                    child = state._replace(def_crits=state.def_crits-1,
                                           atk_crits=state.atk_crits-1)
                value.append(self.minimax(child, not attacker_turn))

            # Parry hit with crit
            if state.def_crits > 0 and state.atk_hits > 0:
                if "storm_shield" in self.defender.keyword and state.atk_hits >= 2:
                    child = state._replace(def_crits=state.def_crits-1,
                                           atk_hits=state.atk_hits-2)
                else:
                    child = state._replace(def_crits=state.def_crits-1,
                                           atk_hits=state.atk_hits-1)
                value.append(self.minimax(child, not attacker_turn))

            return min(value, key=lambda x: x[0])

if __name__ == "__main__":
    all_dfs = []
    for attacker, defender in product(fighters, fighters):
        melee = Melee(attacker, defender)
        damage = np.array([melee.simulate() for _ in range(1000)])
        data = pd.DataFrame(damage, columns=["A WR", "D WR"])
        data = data.groupby(["A WR", "D WR"]).size().reset_index(name="count")
        data["A"] = f"{attacker.name}"
        data["D"] = f"{defender.name}"
        all_dfs.append(data)

    df = pd.concat(all_dfs)
    fig = px.density_heatmap(df, x="D WR", y="A WR", z="count", facet_row="A", facet_col="D")
    fig.show()
