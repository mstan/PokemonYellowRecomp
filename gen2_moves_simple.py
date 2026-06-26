#!/usr/bin/env python3
"""
gen2_moves_simple.py -- MOVE_MODE=simple effect mapping ("just Gen2 moves +
best-effort mapping").

Every Gen2-only move is added to the ROM with its real power/type/accuracy/PP
(and real Dark/Steel typing), but its EFFECT is mapped to the NEAREST existing
Gen1 effect. NO battle-engine code is added or changed, so this mode cannot
break the battle loop -- the worst case for an inexpressible effect is a
plain-damage or do-nothing move.

Mapping policy:
  * Effects Gen1 already has exactly (burn/freeze/paralyze side, stat up/down,
    drain, heal, flinch, confuse, always-hit, ...) map 1:1 -- these are
    behaviourally identical to the real Gen2 move.
  * Effects Gen1 can approximate map to the closest cousin (Encore->Disable,
    Mirror Coat->Bide, Pain Split->Super Fang, Conversion2->Conversion,
    Sketch->Mimic, Baton Pass->Teleport, Swagger->Confuse).
  * Effects that need mechanics Gen1 simply lacks (weather, hazards, Protect,
    Perish Song, Future Sight's delay, trap-in-place, ...) become either plain
    damage (damaging moves) or Splash (status moves: succeeds, does nothing).

The companion `full` mode reuses this exact map for everything it does NOT
implement natively, so the two modes agree except where `full` adds real code.
"""

# Gen2 move-effect const  ->  Gen1 move-effect const
EFFECT_MAP = {
    # --- exact Gen1 equivalents (full-fidelity even in simple mode) ---
    "EFFECT_NORMAL_HIT":       "NO_ADDITIONAL_EFFECT",   # Megahorn, Aeroblast
    "EFFECT_FLAME_WHEEL":      "BURN_SIDE_EFFECT1",      # burn chance
    "EFFECT_SACRED_FIRE":      "BURN_SIDE_EFFECT1",
    "EFFECT_FREEZE_HIT":       "FREEZE_SIDE_EFFECT1",    # Powder Snow
    "EFFECT_PARALYZE_HIT":     "PARALYZE_SIDE_EFFECT1",  # Spark, Zap Cannon
    "EFFECT_SP_DEF_DOWN_HIT":  "SPECIAL_DOWN_SIDE_EFFECT",  # Crunch (Special=SpDef in Gen1)
    "EFFECT_LEECH_HIT":        "DRAIN_HP_EFFECT",        # Giga Drain
    "EFFECT_SNORE":            "FLINCH_SIDE_EFFECT1",
    "EFFECT_TWISTER":          "FLINCH_SIDE_EFFECT1",
    "EFFECT_ALWAYS_HIT":       "SWIFT_EFFECT",           # Faint Attack
    "EFFECT_SPEED_DOWN_2":     "SPEED_DOWN2_EFFECT",     # Scary Face, Cotton Spore
    "EFFECT_ATTACK_DOWN_2":    "ATTACK_DOWN2_EFFECT",    # Charm
    "EFFECT_EVASION_DOWN":     "EVASION_DOWN1_EFFECT",   # Sweet Scent
    "EFFECT_CONFUSE":          "CONFUSION_EFFECT",       # Sweet Kiss
    "EFFECT_HEAL":             "HEAL_EFFECT",            # Milk Drink
    "EFFECT_SYNTHESIS":        "HEAL_EFFECT",
    "EFFECT_MORNING_SUN":      "HEAL_EFFECT",
    "EFFECT_MOONLIGHT":        "HEAL_EFFECT",

    # --- closest-cousin approximations ---
    "EFFECT_ENCORE":           "DISABLE_EFFECT",         # move-lock (inverse, but closest)
    "EFFECT_SPITE":            "DISABLE_EFFECT",         # PP denial
    "EFFECT_MIRROR_COAT":      "BIDE_EFFECT",            # store & return damage
    "EFFECT_PAIN_SPLIT":       "SUPER_FANG_EFFECT",      # HP manipulation
    "EFFECT_CONVERSION2":      "CONVERSION_EFFECT",      # type change
    "EFFECT_SKETCH":           "MIMIC_EFFECT",           # copy a move
    "EFFECT_BATON_PASS":       "SWITCH_AND_TELEPORT_EFFECT",  # switch out
    "EFFECT_SWAGGER":          "CONFUSION_EFFECT",       # (drops the +2 Atk)
    "EFFECT_SAFEGUARD":        "MIST_EFFECT",            # protective barrier

    # --- variable-power damage (power fixed in gen2_moves.POWER_OVERRIDE) ---
    "EFFECT_REVERSAL":         "NO_ADDITIONAL_EFFECT",   # Flail, Reversal
    "EFFECT_HIDDEN_POWER":     "NO_ADDITIONAL_EFFECT",
    "EFFECT_PRESENT":          "NO_ADDITIONAL_EFFECT",
    "EFFECT_PURSUIT":          "NO_ADDITIONAL_EFFECT",
    "EFFECT_FALSE_SWIPE":      "NO_ADDITIONAL_EFFECT",
    "EFFECT_BEAT_UP":          "NO_ADDITIONAL_EFFECT",
    "EFFECT_FUTURE_SIGHT":     "NO_ADDITIONAL_EFFECT",   # immediate instead of delayed
    "EFFECT_RAPID_SPIN":       "NO_ADDITIONAL_EFFECT",   # hazards don't exist in Gen1
    "EFFECT_ATTACK_UP_HIT":    "NO_ADDITIONAL_EFFECT",   # Metal Claw (no self-up-side in Gen1)
    "EFFECT_DEFENSE_UP_HIT":   "NO_ADDITIONAL_EFFECT",   # Steel Wing
    "EFFECT_ALL_UP_HIT":       "NO_ADDITIONAL_EFFECT",   # AncientPower
    "EFFECT_ACCURACY_DOWN_HIT":"NO_ADDITIONAL_EFFECT",   # Octazooka (no acc-down-side in Gen1)
    "EFFECT_ROLLOUT":          "THRASH_PETAL_DANCE_EFFECT",  # multi-turn lock
    "EFFECT_TRIPLE_KICK":      "TWO_TO_FIVE_ATTACKS_EFFECT", # multi-hit

    # --- mechanics Gen1 lacks entirely -> Splash (succeeds, no effect) ---
    "EFFECT_PROTECT":          "SPLASH_EFFECT",   # Protect, Detect
    "EFFECT_ENDURE":           "SPLASH_EFFECT",
    "EFFECT_PERISH_SONG":      "SPLASH_EFFECT",
    "EFFECT_DESTINY_BOND":     "SPLASH_EFFECT",
    "EFFECT_SPIKES":           "SPLASH_EFFECT",
    "EFFECT_RAIN_DANCE":       "SPLASH_EFFECT",
    "EFFECT_SUNNY_DAY":        "SPLASH_EFFECT",
    "EFFECT_SANDSTORM":        "SPLASH_EFFECT",
    "EFFECT_LOCK_ON":          "SPLASH_EFFECT",
    "EFFECT_FORESIGHT":        "SPLASH_EFFECT",
    "EFFECT_MEAN_LOOK":        "SPLASH_EFFECT",   # Spider Web, Mean Look
    "EFFECT_PSYCH_UP":         "SPLASH_EFFECT",
    "EFFECT_CURSE":            "SPLASH_EFFECT",
    "EFFECT_HEAL_BELL":        "SPLASH_EFFECT",
}

FALLBACK = "NO_ADDITIONAL_EFFECT"


def resolve(move):
    """Return the Gen1 effect const to write into moves.asm for this move."""
    return EFFECT_MAP.get(move["effect"], FALLBACK)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen2_moves as gm
    tbl = gm.build_move_table(list(range(152, 252)))
    missing = sorted({m["effect"] for m in tbl} - set(EFFECT_MAP))
    print(f"{len(tbl)} moves; {len(set(m['effect'] for m in tbl))} distinct effects; "
          f"unmapped (-> {FALLBACK}): {missing or 'none'}")
    for m in tbl:
        print(f"  {m['C']:14} {m['effect']:24} -> {resolve(m)}")
