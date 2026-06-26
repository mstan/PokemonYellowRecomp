#!/usr/bin/env python3
"""
Generate GEN2_MOVE_ADAPTATION.md — the human-readable record of how every
Gen2-only move is grafted onto Pokemon Yellow's Gen1 battle engine.

Data-driven: move stats come from gen2_moves.build_move_table (parsing
pokecrystal), the Yellow effect mapping from gen2_moves_simple. The per-effect
"real Gen2 behaviour" prose and fidelity rating live in this file. Run against
a PRISTINE pokeyellow checkout (so the 61 Gen2-only moves are detected):

    git -C pokeyellow checkout -- . && git -C pokeyellow clean -fdq
    python gen_move_adaptation_doc.py
"""
import os
import gen2_moves as gm
import gen2_moves_simple as simple

ROOT = os.path.dirname(os.path.abspath(__file__))

# Fidelity tiers (best -> worst), with the icon used in the doc.
FID = {
    "faithful": ("🟢 Faithful", "Behaves as it does in Gen 2 — Gen 1 already had this exact effect."),
    "approx":   ("🟡 Approximated", "A related Gen 1 effect stands in and captures the gist."),
    "damage":   ("🟠 Damage-only", "A damaging move stripped of its gimmick — it still hits, just without the extra."),
    "inert":    ("⚪ Inert", "Gen 1 can't express this at all; the move animates but does nothing."),
}
FID_ORDER = ["faithful", "approx", "damage", "inert"]

# Gen2 effect const -> (real Gen2 behaviour, fidelity tier).
GEN2 = {
    "EFFECT_NORMAL_HIT":       ("Plain damage, no secondary effect.", "faithful"),
    "EFFECT_FLAME_WHEEL":      ("Fire damage, 10% burn; thaws a frozen user.", "faithful"),
    "EFFECT_SACRED_FIRE":      ("Fire damage, 50% burn; thaws user. (Yellow's burn chance is the lower Gen1 side-effect rate.)", "faithful"),
    "EFFECT_FREEZE_HIT":       ("Damage, 10% chance to freeze.", "faithful"),
    "EFFECT_PARALYZE_HIT":     ("Damage + paralyze chance (Spark 30%, Zap Cannon 100%; Yellow uses the Gen1 side-effect rate).", "faithful"),
    "EFFECT_SP_DEF_DOWN_HIT":  ("Damage, 20% to lower the target's Sp.Def. In Yellow there's one Special stat, so it lowers Special (Sp.Atk+Sp.Def together).", "faithful"),
    "EFFECT_LEECH_HIT":        ("Damage; user recovers half the damage dealt.", "faithful"),
    "EFFECT_SNORE":            ("Damage + 30% flinch — usable only while asleep. Yellow drops the asleep requirement.", "approx"),
    "EFFECT_TWISTER":          ("Damage, 20% flinch.", "faithful"),
    "EFFECT_ALWAYS_HIT":       ("Damage that never misses.", "faithful"),
    "EFFECT_SPEED_DOWN_2":     ("Lowers the target's Speed by 2 stages.", "faithful"),
    "EFFECT_ATTACK_DOWN_2":    ("Lowers the target's Attack by 2 stages.", "faithful"),
    "EFFECT_EVASION_DOWN":     ("Lowers the target's evasion by 1 stage.", "faithful"),
    "EFFECT_CONFUSE":          ("Confuses the target.", "faithful"),
    "EFFECT_HEAL":             ("Restores 50% of max HP.", "faithful"),
    "EFFECT_SYNTHESIS":        ("Restores HP — amount varies with weather. Yellow heals a flat 50%.", "approx"),
    "EFFECT_MORNING_SUN":      ("Restores HP — amount varies with weather. Yellow heals a flat 50%.", "approx"),
    "EFFECT_MOONLIGHT":        ("Restores HP — amount varies with weather. Yellow heals a flat 50%.", "approx"),
    "EFFECT_ENCORE":           ("Forces the target to repeat its last move for 2-6 turns.", "approx"),
    "EFFECT_SPITE":            ("Drains 2-5 PP from the target's last-used move.", "approx"),
    "EFFECT_MIRROR_COAT":      ("Returns double the special damage taken this turn.", "approx"),
    "EFFECT_PAIN_SPLIT":       ("Adds both mons' current HP and splits it evenly.", "approx"),
    "EFFECT_CONVERSION2":      ("Changes the user's type to resist the foe's last move.", "approx"),
    "EFFECT_SKETCH":           ("Permanently copies the target's last move.", "approx"),
    "EFFECT_BATON_PASS":       ("Switches out, handing stat changes to the replacement.", "approx"),
    "EFFECT_SWAGGER":          ("Raises the target's Attack by 2 but confuses it.", "approx"),
    "EFFECT_SAFEGUARD":        ("Shields the user's party from status for 5 turns.", "approx"),
    "EFFECT_CURSE":            ("Ghost types pay half their HP to curse the foe; others gain +Atk/+Def and lose Speed.", "approx"),
    "EFFECT_ROLLOUT":          ("Locks in for 5 turns, doubling in power each hit.", "approx"),
    "EFFECT_TRIPLE_KICK":      ("Hits up to 3 times with rising power.", "approx"),
    "EFFECT_REVERSAL":         ("Power rises as the user's HP falls.", "damage"),
    "EFFECT_HIDDEN_POWER":     ("Type and power are derived from the user's DVs.", "damage"),
    "EFFECT_PRESENT":          ("Random: damage at three power tiers, or it heals the target.", "damage"),
    "EFFECT_PURSUIT":          ("Doubles in power if it catches a switching foe.", "damage"),
    "EFFECT_FALSE_SWIPE":      ("Always leaves the target with at least 1 HP.", "damage"),
    "EFFECT_BEAT_UP":          ("One strike for each healthy party member.", "damage"),
    "EFFECT_FUTURE_SIGHT":     ("Strikes two turns after it's used.", "damage"),
    "EFFECT_RAPID_SPIN":       ("Damage, then clears Spikes/Leech Seed/trapping from the user.", "damage"),
    "EFFECT_ATTACK_UP_HIT":    ("Damage, ~10% to raise the user's Attack.", "damage"),
    "EFFECT_DEFENSE_UP_HIT":   ("Damage, ~10% to raise the user's Defense.", "damage"),
    "EFFECT_ALL_UP_HIT":       ("Damage, ~10% to raise ALL of the user's stats.", "damage"),
    "EFFECT_ACCURACY_DOWN_HIT":("Damage, 50% to lower the target's accuracy.", "damage"),
    "EFFECT_PROTECT":          ("Blocks every move aimed at the user this turn.", "inert"),
    "EFFECT_ENDURE":           ("Survives any hit with 1 HP this turn.", "inert"),
    "EFFECT_PERISH_SONG":      ("Every mon in play faints in 3 turns unless switched out.", "inert"),
    "EFFECT_DESTINY_BOND":     ("If the user faints, the attacker faints too.", "inert"),
    "EFFECT_SPIKES":           ("Lays a hazard that hurts foes as they switch in.", "inert"),
    "EFFECT_RAIN_DANCE":       ("Summons rain for 5 turns (boosts Water, weakens Fire).", "inert"),
    "EFFECT_SUNNY_DAY":        ("Summons harsh sunlight for 5 turns (boosts Fire, weakens Water).", "inert"),
    "EFFECT_SANDSTORM":        ("Summons a sandstorm that chips non-Rock/Ground/Steel each turn.", "inert"),
    "EFFECT_LOCK_ON":          ("Guarantees the user's next move lands.", "inert"),
    "EFFECT_FORESIGHT":        ("Lets Normal/Fighting hit Ghosts and ignores the target's evasion.", "inert"),
    "EFFECT_MEAN_LOOK":        ("Stops the target from fleeing or switching out.", "inert"),
    "EFFECT_PSYCH_UP":         ("Copies all of the target's stat-stage changes onto the user.", "inert"),
    "EFFECT_HEAL_BELL":        ("Cures the status of the user's entire party.", "inert"),
}

# What the Gen1 effect the move maps to actually does in Yellow.
YELLOW = {
    "NO_ADDITIONAL_EFFECT":      "plain damage",
    "SPLASH_EFFECT":             "nothing (plays the animation, then “nothing happened”)",
    "BURN_SIDE_EFFECT1":         "damage with a burn chance",
    "FREEZE_SIDE_EFFECT1":       "damage with a freeze chance",
    "PARALYZE_SIDE_EFFECT1":     "damage with a paralyze chance",
    "SPECIAL_DOWN_SIDE_EFFECT":  "damage, may lower the target's Special",
    "DRAIN_HP_EFFECT":           "damage, heals half of it",
    "FLINCH_SIDE_EFFECT1":       "damage with a flinch chance",
    "SWIFT_EFFECT":              "damage that never misses",
    "SPEED_DOWN2_EFFECT":        "lowers Speed 2 stages",
    "ATTACK_DOWN2_EFFECT":       "lowers Attack 2 stages",
    "EVASION_DOWN1_EFFECT":      "lowers evasion 1 stage",
    "DEFENSE_UP1_EFFECT":        "raises the user's Defense 1 stage",
    "CONFUSION_EFFECT":          "confuses the target",
    "HEAL_EFFECT":               "restores 50% HP",
    "DISABLE_EFFECT":            "disables one of the target's moves",
    "BIDE_EFFECT":               "stores damage and returns double",
    "SUPER_FANG_EFFECT":         "halves the target's current HP",
    "CONVERSION_EFFECT":         "changes the user's type to one of its moves",
    "MIMIC_EFFECT":              "copies one of the target's moves",
    "MIST_EFFECT":               "shields the user from stat drops",
    "SWITCH_AND_TELEPORT_EFFECT":"ends the battle / switches out",
    "THRASH_PETAL_DANCE_EFFECT": "locks in for 2-3 turns of damage",
    "TWO_TO_FIVE_ATTACKS_EFFECT":"hits 2-5 times",
}


def yellow_desc(const):
    return YELLOW.get(const, const)


def main():
    tbl = gm.build_move_table(list(range(152, 252)))
    by_fid = {k: [] for k in FID_ORDER}
    for m in tbl:
        eff = m["effect"]
        real, fid = GEN2.get(eff, ("(undocumented)", "damage"))
        by_fid[fid].append((m, real))

    L = []
    w = L.append
    w("# Gen 2 → Pokémon Yellow — Move Adaptation\n")
    w("> Auto-generated by `gen_move_adaptation_doc.py`. Do not hand-edit.\n")
    w("This project keeps **Yellow's original Gen 1 battle engine untouched** and grafts on "
      "as much of Gen 2 as the data layer allows: all of Johto (dex 152–251), the **Dark** and "
      "**Steel** types, and every Gen 2-only **move** below — added with its real type, power, "
      "accuracy and PP.\n")
    w("The deliberate concession is **move *effects***. Gen 1's engine only knows the effects "
      "Gen 1 moves had, so each Gen 2 effect is mapped to the closest thing the engine can already "
      "do. Where there's an exact match it's indistinguishable from Gen 2; where there isn't, the "
      "move either keeps its damage (losing a gimmick) or — for mechanics Gen 1 simply doesn't have "
      "(weather, hazards, Protect, …) — animates and does nothing.\n")

    w("## New types\n")
    w("Gen 1's physical/special split is **by type**. The two new types slot into that scheme:\n")
    w("| Type | Slot | Class | Notes |")
    w("|---|---|---|---|")
    w("| **Steel** | `$09` | Physical | Filled an unused type id below the special range. |")
    w("| **Dark** | `$1b` | Special | Appended after Dragon. |")
    w("\nThe full Gen 2 effectiveness chart for both is wired into the engine's type table "
      "(Steel resists a swath of types and is weak to Fire/Fighting/Ground; Dark is strong vs "
      "Psychic/Ghost and immune to Psychic, etc.).\n")

    w("## Fidelity legend\n")
    for k in FID_ORDER:
        label, desc = FID[k]
        w(f"- **{label}** — {desc}")
    w("")

    counts = {k: len(by_fid[k]) for k in FID_ORDER}
    total = sum(counts.values())
    w(f"## Summary — {total} Gen 2 moves\n")
    w("| Fidelity | Count |")
    w("|---|---:|")
    for k in FID_ORDER:
        w(f"| {FID[k][0]} | {counts[k]} |")
    w("")

    for k in FID_ORDER:
        rows = by_fid[k]
        if not rows:
            continue
        w(f"## {FID[k][0]} — {len(rows)}\n")
        w("| Move | Type | Pow | Acc | PP | Real Gen 2 effect | In Yellow |")
        w("|---|---|---:|---:|---:|---|---|")
        for m, real in sorted(rows, key=lambda r: r[0]["name"]):
            y = yellow_desc(simple.resolve(m))
            typ = m["type"].replace("_TYPE", "")
            w(f"| {m['name']} | {typ} | {m['power']} | {m['acc']} | {m['pp']} | {real} | {y} |")
        w("")

    w("## Why the Inert moves can't work (engine limits)\n")
    w("Each of these needs battle machinery that Gen 1 never had, so there's no honest place to "
      "map them without rebuilding the engine:\n")
    w("- **Weather** (Rain Dance, Sunny Day, Sandstorm) — no weather state, per-turn residual "
      "damage, or damage modifiers exist.")
    w("- **Hazards** (Spikes) / **Rapid Spin** — no concept of entry hazards.")
    w("- **Turn-delayed / multi-turn bookkeeping** (Future Sight, Perish Song) — no scheduled-action slots.")
    w("- **This-turn protection** (Protect, Detect, Endure) — no move-priority / protect flag in the turn loop.")
    w("- **Faint/switch reactions** (Destiny Bond, Pursuit, Mean Look, Baton Pass) — no hooks on those events.")
    w("- **Copy/aim utilities** (Psych Up, Lock-On, Foresight) — no state to read or set.")
    w("- **Party-wide status** (Heal Bell, Safeguard) — Safeguard is approximated by Mist; Heal Bell has no Gen 1 analogue.\n")

    w("## A note on the shelved “full” engine port\n")
    w("An experimental `MOVE_MODE=full` once compiled a handful of these effects as real handlers "
      "*inside* Yellow's battle engine (Heal Bell, Pain Split, Psych Up, on-hit stat boosts). It is "
      "**disabled** (`ENABLE_NATIVE = False` in `gen2_moves_full.py`): one of the handlers destabilised "
      "the battle loop, and per-effect engine surgery is out of scope for a faithful-Yellow base. The "
      "code remains in git history; re-enabling should be done one effect at a time behind an in-battle "
      "test loop. The shipped build is `MOVE_MODE=simple`, documented above.\n")

    out = os.path.join(ROOT, "GEN2_MOVE_ADAPTATION.md")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"wrote {out}")
    print("fidelity:", counts)


if __name__ == "__main__":
    main()
