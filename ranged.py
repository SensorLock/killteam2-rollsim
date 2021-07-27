from collections import namedtuple
from itertools import product
import numpy as np
import pandas as pd
import plotly.express as px

Attacker = namedtuple("Attacker", "name num to_hit to_crit dmg dmg_crit ap mws")

weapons = [
    # Attacker("Frag", 4, 4, 6, 2, 4, 0, 0),
    # Attacker("Krak", 4, 4, 6, 4, 5, 1, 0),
    Attacker("Las", 4, 4, 6, 2, 3, 0, 0),
    Attacker("Long-Las", 4, 2, 6, 3, 3, 0, 3),
    Attacker("Flamer", 5, 2, 6, 2, 2, 0, 0),
    Attacker("M Bolt", 4, 3, 6, 3, 4, 0, 0),
    Attacker("CSM Melta", 4, 3, 6, 6, 3, 2, 4),
    Attacker("CSM Plasma (Std)", 4, 3, 6, 5, 6, 1, 0),
    Attacker("CSM Plasma (Over)", 4, 3, 6, 5, 6, 2, 0), # Hot
    Attacker("Shuriken Catapult", 4, 3, 6, 3, 4, 0, 0),  # SR Balanced? ! Rending?
    Attacker("Guardian Spear", 4, 2, 6, 3, 5, 0, 0),  # P1
    Attacker("Sentinel Blade", 4, 2, 6, 3, 4, 0, 0),  # P1
]

Defender = namedtuple("Defender", "name num to_save to_critsave invuln fnp dust wounds")

targets = [
    Defender("Trooper Veteran", 3, 5, 6, None, None, False, 7),
    Defender("Trooper Veteran (Hardened by War)", 3, 5, 6, None, 5, False, 7),
    Defender("Poxwalker", 3, 6, 6, None, 5, False, 7),
    Defender("Dire Avenger", 3, 4, 6, None, None, False, 8),
    Defender("Chaos Space Marine", 3, 3, 6, None, None, False, 12),
    Defender("Rubric Marine", 3, 3, 6, 5, None, True, 12),
    Defender("Custodian Guard", 3, 2, 6, None, None, False, 18),
    Defender("Custodian guard (S)", 3, 2, 6, 4, None, False, 18),
]


def simulate_ranged(attacker: Attacker, defender: Defender, samples=10000):
    # Roll a bunch of dice in atk and def groups
    a_rolls = np.random.choice(6, (samples, attacker.num)) + 1
    d_rolls = np.random.choice(6, (samples, defender.num)) + 1
    
    crits = (a_rolls >= attacker.to_crit).sum(axis=1)
    mws = crits * attacker.mws
    hits = (a_rolls >= attacker.to_hit).sum(axis=1) - crits

    if defender.dust and attacker.dmg <= 3:
        save_needed = 2
    else:
        save_needed = defender.to_save
    
    save_needed += attacker.ap
    if defender.invuln is not None:
        save_needed = min(save_needed, defender.invuln)

    # TODO OPEN Q: How do critical saves interact with AP?
    critsaves = (d_rolls >= defender.to_critsave).sum(axis=1)
    saves = (d_rolls >= save_needed).sum(axis=1) - critsaves

    crits -= critsaves

    # Carry extra critsaves down as regular saves
    idx_extra_critsaves = crits < 0
    # TODO OPEN Q: if it turns out save conversion 2:1 ratio is bidirectional then we need to multiply by 2 here
    hits[idx_extra_critsaves] += crits[idx_extra_critsaves]
    crits[idx_extra_critsaves] = 0

    if attacker.dmg_crit < attacker.dmg * 2:
        # prioritize saving hits, then use spare saves to save crits, allowing up to 1 regular hit to go through to save another crit
        idx_conversions = np.logical_and(saves >= 2, saves > hits, crits > 0)
        saves_to_consume = np.minimum(saves[idx_conversions] - hits[idx_conversions] + 1, saves[idx_conversions])
    else:
        # prioritize saving crits over hits
        idx_conversions = np.logical_and(saves >= 2, crits > 0)
        saves_to_consume = saves[idx_conversions]
    converted_critsaves = np.minimum(saves_to_consume // 2, crits[idx_conversions])
    crits[idx_conversions] -= converted_critsaves
    saves[idx_conversions] -= converted_critsaves * 2

    # Save remaining regular hits
    hits -= saves
    hits[hits < 0] = 0

    damage = (mws + crits * attacker.dmg_crit + hits * attacker.dmg)
    
    if defender.fnp is not None:
        # We need a variable number of rolls for each sample so just loop across the damamge array
        for i in range(samples):
            fnp_rolls = np.random.choice(6, damage[i]) + 1
            damage[i] -= (fnp_rolls >= defender.fnp).sum()

    return damage


if __name__ == "__main__":
    all_dfs = []
    kill_probs = []
    for weapon, target in product(weapons, targets):
        damage = simulate_ranged(weapon, target)
        
        df = pd.DataFrame(damage, columns=["Damage"])
        df["Weapon"] = weapon.name
        df["Target"] = target.name
        all_dfs.append(df)
        
        kill_probs.append((len(weapons) - weapons.index(weapon),
                           targets.index(target)+1,
                           target.wounds,
                           (damage >= target.wounds).sum() / damage.shape[0]))


    df = pd.concat(all_dfs)
    fig = px.histogram(df, x="Damage", histnorm="probability", facet_row="Weapon", facet_col="Target")
    for row, col, x, y in kill_probs:
        fig.add_vline(x=x-0.5, row=row, col=col, line_color="red", line_dash="dash")
        fig.add_hrect(y0=0, y1=y, row=row, col=col, fillcolor="red", opacity=0.2, layer="below")
    fig.show()
    