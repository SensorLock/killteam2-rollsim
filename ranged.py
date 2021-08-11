from collections import namedtuple
from itertools import product
import numpy as np
import pandas as pd
import plotly.express as px

Attacker = namedtuple("Attacker", "name a bs dmg dmg_crit keyword")

weapons = [
    #Attacker("G Frag", 4, 4, 2, 4, {}),
    #Attacker("G Krak", 4, 4, 4, 5, {"ap": 1}),
    Attacker("Las", 4, 4, 2, 3, {}),
    Attacker("Long-Las", 4, 2, 3, 3, {"mw": 3}),
    #Attacker("Flamer", 5, 2, 2, 2, {"torrent": None}),
    Attacker("Webber", 4, 3, 2, 2, {"lethal": 5, "stun": None}),
    #Attacker("Slugga", 4, 4, 3, 4, {}),
    #Attacker("Dakka Shoota", 5, 4, 3, 4, {}), # Re-roll within 6"
    #Attacker("Scoped Big Shoota", 6, 3, 2, 2, {"mw": 2}),
    #Attacker("G Melta", 4, 4, 6, 3, {"ap": 2, "mw": 4}),
    #Attacker("G Plasma (Std)", 4, 4, 5, 6, {"ap": 1}),
    #Attacker("G Plasma (Over)", 4, 4, 5, 6, {"ap": 2, "hot": None}),
    Attacker("CSM Bolter", 4, 3, 3, 4, {}),
    Attacker("CSM Melta", 4, 3, 6, 3, {"ap": 2, "mw": 4}),
    #Attacker("CSM Plasma (Std)", 4, 3, 5, 6, {"ap": 1}),
    #Attacker("CSM Plasma (Over)", 4, 3, 5, 6, {"ap": 2, "hot": None}),
    #Attacker("Blight Launcher", 4, 3, 4, 6, {"ap": 1}),
    #Attacker("Plague Spewer", 6, 2, 2, 3, {}),
    #Attacker("Shuriken Pistol", 4, 3, 3, 4, {"rending": None}),
    Attacker("Shuriken Catapult", 4, 3, 3, 4, {"balanced": None, "rending": None}),
    Attacker("Guardian Spear", 4, 2, 3, 5, {"p": 1}),
    #Attacker("Sentinel Blade", 4, 2, 3, 4, {"p": 1}),
]

Defender = namedtuple("Defender", "name df save wounds keyword")

targets = [
    Defender("Trooper Veteran", 3, 5, 7, {}),
    Defender("Trooper Veteran (Hardened by War)", 3, 5, 7, {"fnp": 5}),
    Defender("Kommando Nob", 3, 4, 13, {}),
    Defender("Kommando Dakka Boy", 3, 5, 10, {}),
    Defender("Poxwalker", 3, 6, 7, {"fnp": 5}),
    Defender("Player", 3, 6, 8, {"invuln": 4}),
    Defender("Dire Avenger", 3, 4, 8, {}),
    Defender("Chaos Space Marine", 3, 3, 12, {}),
    Defender("Rubric Marine", 3, 3, 12, {"invuln": 5, "all_is_dust": None}),
    Defender("Plague Marine", 3, 3, 12, {"fnp": 5}),
    Defender("Custodian Guard", 3, 2, 18, {}),
    Defender("Custodian Guard (S)", 3, 2, 18, {"invuln": 4}),
]


def simulate_ranged(attacker: Attacker, defender: Defender, cover: bool) -> np.int:
    a_rolls = np.random.choice(6, (attacker.a,)) + 1

    rerolls = 0
    if "relentless" in attacker.keyword:
        rerolls = (a_rolls < attacker.bs).sum()
    elif "balanced" in attacker.keyword:
        if any(a_rolls < attacker.bs):
            rerolls = 1
    elif "ceaseless" in attacker.keyword:
        if any(a_rolls == 1):
            rerolls = 1

    if rerolls:
        a_rolls = np.concatenate((a_rolls, np.random.choice(6, (rerolls,)) + 1))
    
    to_crit = attacker.keyword.get("lethal", 6)
    
    crits = (a_rolls >= to_crit).sum()
    mws = crits * attacker.keyword.get("mw", 0) + crits * attacker.keyword.get("splash", 0)
    hits = (a_rolls >= attacker.bs).sum() - crits
    
    if "rending" in attacker.keyword and crits > 0 and hits > 0:
        hits -= 1
        crits += 1

    df = defender.df
    save = defender.save

    if "all_is_dust" in defender.keyword and attacker.dmg <= 3:
        save = 2

    ap = attacker.keyword.get("ap", 0)
    if crits:
        ap += attacker.keyword.get("p", 0)

    if "invuln" in defender.keyword:
        if ap > 0:
            # TODO cases where you don't want to take the invuln?
            save = defender.keyword["invuln"]
        else:
            save = min(save, defender.keyword["invuln"])
    else:
        df -= ap

    cover_saved = 0
    if cover and "no_cover" not in attacker.keyword:
        # TODO camo gives second retained die, and there are edge cases where you roll anyways
        # TODO camo can't take 2 dice in case of AP2
        cover_saved = 1
        df -= 1

    d_rolls = np.random.choice(6, (df,)) + 1
    crits_saved = (d_rolls >= 6).sum()
    hits_saved = cover_saved + (d_rolls >= save).sum() - crits_saved

    crits -= crits_saved

    # Carry extra crit saves down as regular saves
    if crits < 0:
        hits += crits
        crits = 0

    saves_to_consume = 0
    # TODO handle melta-like cases - regular hits are more damage than crits!
    if attacker.dmg_crit < attacker.dmg * 2:
        # prioritize saving hits, then use spare saves to save crits, allowing up to 1 regular hit to go through to save another crit
        if hits_saved >= 2 and hits_saved > hits and crits > 0:
            saves_to_consume = min(hits_saved - hits + 1, hits_saved)
    else:
        # prioritize saving crits over hits
        if hits_saved >= 2 and crits > 0:
            saves_to_consume = hits_saved
    converted_critsaves = min(saves_to_consume // 2, crits)
    crits -= converted_critsaves
    hits_saved -= converted_critsaves * 2

    # Save remaining regular hits
    hits -= hits_saved
    if hits < 0:
        hits = 0

    damage = (mws + crits * attacker.dmg_crit + hits * attacker.dmg)

    if "fnp" in defender.keyword:
        fnp_rolls = np.random.choice(6, (damage,)) + 1
        damage -= (fnp_rolls >= defender.keyword["fnp"]).sum()

    return np.int(damage)


if __name__ == "__main__":
    all_dfs = []
    kill_probs = []
    for weapon, target in product(weapons, targets):
        print(f"{weapon.name} -> {target.name}")
        damage = np.array([simulate_ranged(weapon, target, False) for _ in range(10000)])
        data = pd.DataFrame(damage, columns=["Damage"])
        data["W"] = weapon.name
        data["T"] = target.name
        all_dfs.append(data)
        
        kill_probs.append((len(weapons) - weapons.index(weapon),
                           targets.index(target)+1,
                           target.wounds,
                           (damage >= target.wounds).sum() / damage.shape[0]))


    df = pd.concat(all_dfs)
    fig = px.histogram(df, x="Damage", histnorm="probability", facet_row="W", facet_col="T")
    for row, col, x, y in kill_probs:
        fig.add_vline(x=x-0.5, row=row, col=col, line_color="red", line_dash="dash")
        fig.add_hrect(y0=0, y1=y, row=row, col=col, fillcolor="red", opacity=0.2, layer="below")
    fig.show()
    