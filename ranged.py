from collections import namedtuple
import numpy as np

Attacker = namedtuple("Attacker", "name num to_hit to_crit dmg dmg_crit mws")
Defender = namedtuple("Defender", "name num to_save to_critsave fnp wounds")


def simulate_ranged(attacker: Attacker, defender: Defender, samples=100000):
    # Roll a bunch of dice in atk and def groups
    a_rolls = np.random.choice(6, (samples, attacker.num)) + 1
    d_rolls = np.random.choice(6, (samples, defender.num)) + 1
    
    crits = (a_rolls >= attacker.to_crit).sum(axis=1)
    # TODO OPEN Q: if MWs don't carry on as crits and just do flat damage then subtract the mws from the crits
    mws = crits * attacker.mws
    hits = (a_rolls >= attacker.to_hit).sum(axis=1) - crits

    critsaves = (d_rolls >= defender.to_critsave).sum(axis=1)
    saves = (d_rolls >= defender.to_save).sum(axis=1) - critsaves

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

    wounds = (mws + crits * attacker.dmg_crit + hits * attacker.dmg)
    
    if defender.fnp is not None:
        # Get rolls for feel-no-pains equal up max possible wounds, will take prefix of this based on actual wounds
        fnp_rolls = np.random.choice(6, (samples, wounds.max())) + 1
        fnp_rolls = fnp_rolls >= defender.fnp

        for i in range(samples):
            # Set rolls that were on wounds beyond what should be checked to False
            fnp_rolls[i][wounds[i]:] = False
        
        fnp = fnp_rolls.sum(axis=1)
        wounds -= fnp

    kills = (wounds >= defender.wounds).sum()

    print(f"{attacker.name} shooting at {defender.name}")
    print(f"Wounds distribution: {np.bincount(wounds)}")
    print(f"Avg. wounds taken: {wounds.mean()}")
    print(f"Kill: {kills/samples * 100}%")
    print()


lasgun = Attacker("Lasgun", 4, 4, 6, 2, 3, 0)
longlas = Attacker("Long-Las", 4, 2, 6, 3, 3, 3)
trooper_veteran = Defender("Trooper Veteran", 3, 5, 6, None, 7)
trooper_veteran_hard = Defender("Trooper Veteran (Hardened by War)", 3, 5, 6, 5, 7)

simulate_ranged(lasgun, trooper_veteran)
simulate_ranged(longlas, trooper_veteran)
simulate_ranged(lasgun, trooper_veteran_hard)
simulate_ranged(longlas, trooper_veteran_hard)
