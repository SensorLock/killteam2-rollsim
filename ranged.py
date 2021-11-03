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
    Attacker("Burst Cannon", 6, 4, 3, 4, {"ceaseless": None}),
    Attacker("Fusion Blaster", 4, 4, 6, 3, {"ap": 2, "mw": 4}),
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
    Defender("Ranger", 3, 5, 8, {"camo_cloak": None}),
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
        rerolls = (a_rolls == 1).sum()

    if rerolls:
        a_rolls = np.concatenate((a_rolls, np.random.choice(6, (rerolls,)) + 1))


    if "grav" in attacker.keyword and defender.save <= 3:
        to_crit = 4
    else:
        to_crit = attacker.keyword.get("lethal", 6)

    crits = (a_rolls >= to_crit).sum()
    hits = (a_rolls >= attacker.bs).sum() - crits

    if "ltgb" in attacker.keyword and any(a_rolls == (to_crit - 1)):
        hits -= 1
        crits += 1

    if "rending" in attacker.keyword and crits > 0 and hits > 0:
        hits -= 1
        crits += 1

    if "dakka" in attacker.keyword and crits > 0 and attacker.a - crits - hits > 0:
        crits += 1

    mws = crits * attacker.keyword.get("mw", 0) + crits * attacker.keyword.get("splash", 0)

    df = defender.df
    save = defender.save

    if "all_is_dust" in defender.keyword and attacker.dmg <= 3:
        save = 2

    ap = attacker.keyword.get("ap", 0)
    if crits and "p" in attacker.keyword:
        ap = max(ap, attacker.keyword["p"])

    if "invuln" in defender.keyword:
        if ap > 0:
            # TODO cases where you don't want to take the invuln?
            save = defender.keyword["invuln"]
        else:
            save = min(save, defender.keyword["invuln"])
    else:
        df -= ap

    cover_retained = 0
    if cover and "no_cover" not in attacker.keyword:
        cover_retained = 2 if "camo_cloak" in defender.keyword else 1

    # Cover is limited by df, since AP & P is applied first
    # No point in retaining more dice than there were hits, fish for crit saves with the rest
    # TODO This could do more to factor in relative dmg of crits vs hits
    cover_retained = min(df, cover_retained, hits)
    df -= cover_retained

    d_rolls = np.random.choice(6, (df,)) + 1
    crits_saved = (d_rolls >= 6).sum()
    hits_saved = cover_retained + (d_rolls >= save).sum() - crits_saved

    saves_to_upgrade = 0
    saves_to_downgrade = 0
    if attacker.dmg_crit > attacker.dmg * 2:
        # prioritize saving crits over hits
        saves_to_upgrade = hits_saved
    elif attacker.dmg < attacker.dmg_crit <= attacker.dmg * 2:
        # prioritize saving hits, then use spare saves to save crits, allowing up to 1 regular hit to go through to save another crit
        saves_to_upgrade = max(hits_saved - hits, 0)
        if saves_to_upgrade < hits_saved:
            saves_to_upgrade += 1
    elif attacker.dmg_crit < attacker.dmg:
        # melta-like weapons where regular hits are more damage than crits apart from the MW
        saves_to_downgrade = min(crits_saved, max(0, hits - hits_saved))

    crits_saved -= saves_to_downgrade
    hits_saved += saves_to_downgrade

    crits -= crits_saved

    # Carry extra crit saves down as regular saves
    if crits < 0:
        hits += crits
        crits = 0

    converted_critsaves = min(saves_to_upgrade // 2, crits)
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
        shoot = weapon.keyword.get("shoot", 1)
        runs = 10000
        damage = np.array([simulate_ranged(weapon, target, cover=False) for _ in range(runs * shoot)])
        damage = damage.reshape((shoot, runs)).sum(axis=0)
        data = pd.DataFrame(damage, columns=["Damage"])
        data["W"] = weapon.name
        data["T"] = target.name
        all_dfs.append(data)

        expected_dmg = 0
        # Maximum dmg is when all attacks crit
        for i in range((weapon.dmg_crit + weapon.keyword.get("mw", 0) )* weapon.a + 1):
            expected_dmg += (damage == i).sum() / damage.shape[0] * i

        kill_probs.append((len(weapons) - weapons.index(weapon),
                           targets.index(target)+1,
                           target.wounds,
                           (damage >= (target.wounds // 2)).sum() / damage.shape[0],
                           (damage >= target.wounds).sum() / damage.shape[0]))
        print(f"{weapon.name} -> {target.name}: {kill_probs[-1][-2:]} Expected Damage: {expected_dmg}")

    df = pd.concat(all_dfs)
    fig = px.histogram(df, x="Damage", histnorm="probability", facet_row="W", facet_col="T")
    for row, col, x, y_i, y_k in kill_probs:
        fig.add_vline(x=x, row=row, col=col, line_color="red", line_dash="dash")
        fig.add_hrect(y0=0, y1=y_i, row=row, col=col, fillcolor="yellow", opacity=0.2, layer="below")
        fig.add_hrect(y0=0, y1=y_k, row=row, col=col, fillcolor="red", opacity=0.2, layer="below")
    fig.show()

