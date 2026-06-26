# Gen2 Move Port — Status (complete vs fallback)

Auto-generated from `gen2_moves.py` + `gen2_moves_simple.py` + `gen2_moves_full.py`. Regenerate after changing the registry; do not hand-edit.

**61 Gen2-only moves** injected (dex 152–251). `MOVE_MODE` selects how their effects are realised:

- **`off`** — moves not added (Gen1-only movesets).
- **`simple`** — moves added with real type/power/PP; every effect mapped to the nearest existing Gen1 effect. No engine changes.
- **`full`** — same, plus native engine handlers for ported effects. Tiered:

  | tier | count | meaning |
  |---|---|---|
  | **native** | 5 | real new engine code (full-fidelity Gen2 behaviour) |
  | **gen1-exact** | 21 | reuses a Gen1 effect that already matches — full-fidelity, no new code |
  | **fallback** | 35 | best-effort: plain damage, an approximation, or a no-op Splash |

> In `full`, **native + gen1-exact = fully working** (23 moves). **fallback** moves are the remaining port work — they're playable but lossy (see the Result column).

## ✅ Native (real new engine handlers) — 5

| Move | Type | Pow | Gen2 effect | `full` result | `simple` result |
|---|---|---:|---|---|---|
| PSYCH UP | NORMAL | 0 | `EFFECT_PSYCH_UP` | copy target's stat stages onto user (native) | no-op (animation only, “nothing happened”) |
| PAIN SPLIT | NORMAL | 0 | `EFFECT_PAIN_SPLIT` | EFFECT_GEN2_PAIN_SPLIT | halve target HP |
| METAL CLAW | STEEL | 50 | `EFFECT_ATTACK_UP_HIT` | EFFECT_GEN2_ATTACK_UP_HIT | plain damage |
| STEEL WING | STEEL | 70 | `EFFECT_DEFENSE_UP_HIT` | EFFECT_GEN2_DEFENSE_UP_HIT | plain damage |
| HEAL BELL | NORMAL | 0 | `EFFECT_HEAL_BELL` | cure entire party's status (native) | no-op (animation only, “nothing happened”) |

## ✅ Gen1-exact (full-fidelity via an existing Gen1 effect) — 21

| Move | Type | Pow | Gen2 effect | `full` result | `simple` result |
|---|---|---:|---|---|---|
| SYNTHESIS | GRASS | 0 | `EFFECT_SYNTHESIS` | heal 50% HP | heal 50% HP |
| FLAME WHEEL | FIRE | 60 | `EFFECT_FLAME_WHEEL` | damage + burn chance | damage + burn chance |
| SCARY FACE | NORMAL | 0 | `EFFECT_SPEED_DOWN_2` | lower target Speed 2 | lower target Speed 2 |
| SPARK | ELECTRIC | 65 | `EFFECT_PARALYZE_HIT` | damage + paralyze chance | damage + paralyze chance |
| CHARM | NORMAL | 0 | `EFFECT_ATTACK_DOWN_2` | lower target Attack 2 | lower target Attack 2 |
| SWEET KISS | NORMAL | 0 | `EFFECT_CONFUSE` | confuse target | confuse target |
| COTTON SPORE | GRASS | 0 | `EFFECT_SPEED_DOWN_2` | lower target Speed 2 | lower target Speed 2 |
| SWEET SCENT | NORMAL | 0 | `EFFECT_EVASION_DOWN` | lower target Evasion 1 | lower target Evasion 1 |
| FAINT ATTACK | DARK | 60 | `EFFECT_ALWAYS_HIT` | damage, never misses | damage, never misses |
| GIGA DRAIN | GRASS | 60 | `EFFECT_LEECH_HIT` | damage + heal half dealt | damage + heal half dealt |
| MORNING SUN | NORMAL | 0 | `EFFECT_MORNING_SUN` | heal 50% HP | heal 50% HP |
| MOONLIGHT | NORMAL | 0 | `EFFECT_MOONLIGHT` | heal 50% HP | heal 50% HP |
| CRUNCH | DARK | 80 | `EFFECT_SP_DEF_DOWN_HIT` | damage + may lower Special (= SpDef) | damage + may lower Special (= SpDef) |
| MEGAHORN | BUG | 120 | `EFFECT_NORMAL_HIT` | plain damage | plain damage |
| SNORE | NORMAL | 40 | `EFFECT_SNORE` | damage + flinch chance | damage + flinch chance |
| POWDER SNOW | ICE | 40 | `EFFECT_FREEZE_HIT` | damage + freeze chance | damage + freeze chance |
| TWISTER | DRAGON | 40 | `EFFECT_TWISTER` | damage + flinch chance | damage + flinch chance |
| ZAP CANNON | ELECTRIC | 100 | `EFFECT_PARALYZE_HIT` | damage + paralyze chance | damage + paralyze chance |
| MILK DRINK | NORMAL | 0 | `EFFECT_HEAL` | heal 50% HP | heal 50% HP |
| AEROBLAST | FLYING | 100 | `EFFECT_NORMAL_HIT` | plain damage | plain damage |
| SACRED FIRE | FIRE | 100 | `EFFECT_SACRED_FIRE` | damage + burn chance | damage + burn chance |

## 🟡 Fallback (best-effort — remaining port work) — 35

| Move | Type | Pow | Gen2 effect | `full` result | `simple` result |
|---|---|---:|---|---|---|
| SAFEGUARD | NORMAL | 0 | `EFFECT_SAFEGUARD` | block stat drops | block stat drops |
| FORESIGHT | NORMAL | 0 | `EFFECT_FORESIGHT` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| BATON PASS | NORMAL | 0 | `EFFECT_BATON_PASS` | flee / switch out | flee / switch out |
| SPIDER WEB | BUG | 0 | `EFFECT_MEAN_LOOK` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| MEAN LOOK | NORMAL | 0 | `EFFECT_MEAN_LOOK` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| FLAIL | NORMAL | 80 | `EFFECT_REVERSAL` | plain damage | plain damage |
| ENCORE | NORMAL | 0 | `EFFECT_ENCORE` | disable a move | disable a move |
| FUTURE SIGHT | PSYCHIC | 80 | `EFFECT_FUTURE_SIGHT` | plain damage | plain damage |
| ROLLOUT | ROCK | 30 | `EFFECT_ROLLOUT` | lock-in multi-turn damage | lock-in multi-turn damage |
| RAIN DANCE | WATER | 0 | `EFFECT_RAIN_DANCE` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| PERISH SONG | NORMAL | 0 | `EFFECT_PERISH_SONG` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| SWAGGER | NORMAL | 0 | `EFFECT_SWAGGER` | confuse target | confuse target |
| SUNNY DAY | FIRE | 0 | `EFFECT_SUNNY_DAY` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| DETECT | FIGHTING | 0 | `EFFECT_PROTECT` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| PURSUIT | DARK | 40 | `EFFECT_PURSUIT` | plain damage | plain damage |
| CURSE | GHOST | 0 | `EFFECT_CURSE` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| SPITE | GHOST | 0 | `EFFECT_SPITE` | disable a move | disable a move |
| HIDDEN POWER | NORMAL | 50 | `EFFECT_HIDDEN_POWER` | plain damage | plain damage |
| MIRROR COAT | PSYCHIC | 1 | `EFFECT_MIRROR_COAT` | store & return 2x damage | store & return 2x damage |
| DESTINY BOND | GHOST | 0 | `EFFECT_DESTINY_BOND` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| PROTECT | NORMAL | 0 | `EFFECT_PROTECT` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| RAPID SPIN | NORMAL | 20 | `EFFECT_RAPID_SPIN` | plain damage | plain damage |
| SPIKES | GROUND | 0 | `EFFECT_SPIKES` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| SANDSTORM | ROCK | 0 | `EFFECT_SANDSTORM` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| FALSE SWIPE | NORMAL | 40 | `EFFECT_FALSE_SWIPE` | plain damage | plain damage |
| ENDURE | NORMAL | 0 | `EFFECT_ENDURE` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| REVERSAL | FIGHTING | 80 | `EFFECT_REVERSAL` | plain damage | plain damage |
| BEAT UP | DARK | 30 | `EFFECT_BEAT_UP` | plain damage | plain damage |
| ANCIENTPOWER | ROCK | 60 | `EFFECT_ALL_UP_HIT` | plain damage | plain damage |
| LOCK-ON | NORMAL | 0 | `EFFECT_LOCK_ON` | no-op (animation only, “nothing happened”) | no-op (animation only, “nothing happened”) |
| OCTAZOOKA | WATER | 65 | `EFFECT_ACCURACY_DOWN_HIT` | plain damage | plain damage |
| PRESENT | NORMAL | 40 | `EFFECT_PRESENT` | plain damage | plain damage |
| CONVERSION2 | NORMAL | 0 | `EFFECT_CONVERSION2` | copy a type | copy a type |
| SKETCH | NORMAL | 0 | `EFFECT_SKETCH` | copy a move | copy a move |
| TRIPLE KICK | FIGHTING | 20 | `EFFECT_TRIPLE_KICK` | multi-hit damage | multi-hit damage |

## Known gaps / caveats

- **Psych Up** (native) copies the target's stat-STAGE bytes but does not recompute the stored modified stats (`wBattleMonAttack` …), so the stages transfer but won't fully affect damage until the next stat change. Partial — needs a stat recompute pass.
- All `no-op (Splash)` fallbacks (weather, hazards, Protect, Perish Song, Destiny Bond, Curse, Foresight, Lock-On, Mean Look, Safeguard, Psych-Up-in-`simple`) need battle-loop hooks to work for real — these are the next native tranche.
- Variable-power moves (Flail, Reversal, Hidden Power, Present, Pursuit, Rollout, False Swipe, Beat Up, Triple Kick) use a fixed power from `gen2_moves.POWER_OVERRIDE`.
