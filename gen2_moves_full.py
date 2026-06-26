#!/usr/bin/env python3
"""
gen2_moves_full.py -- MOVE_MODE=full ("entire Gen2 battle system" path).

Where `simple` only ever maps Gen2 effects onto existing Gen1 effect constants,
`full` extends the Gen1 battle ENGINE so genuinely-new effects can run for real.
It is a tiered, always-shippable port:

  TIER gen1     -- the effect is already expressible in Gen1; `full` uses the
                   same const `simple` does, so it's full-fidelity with zero new
                   code (e.g. Crunch -> SPECIAL_DOWN_SIDE, Sacred Fire -> burn).
  TIER native   -- a real new handler is compiled into the battle engine: a new
                   EFFECT_GEN2_* constant, a MoveEffectPointerTable entry, a
                   handler routine, and (for status moves) a ResidualEffects1
                   listing. Implemented this pass: Heal Bell, Psych Up.
  TIER fallback -- the effect needs battle-loop machinery not ported yet
                   (weather, hazards, Protect, Perish Song, Future Sight's
                   delay, ...). It uses `simple`'s best-effort const so the
                   build is always complete and playable; upgrading it later is
                   a one-line move from NATIVE-pending to a real handler.

THE FRAMEWORK is the deliverable: adding a new native effect = add an entry to
NATIVE_EFFECTS below (const + handler asm + category) and it is wired into the
engine automatically by engine_edits(). Native handlers currently live IN the
Battle Core bank (it has ~1.1 KB free) so they can `call` battle subroutines
(PlayCurrentMoveAnimation, PrintText) directly. If the native set ever outgrows
that bank, switch the stubs to the vanilla `jpfar HandlerName_` pattern (see
HealEffect) and move the bodies into a dedicated ROMX section.
"""
import gen2_moves_simple as simple

# ---------------------------------------------------------------------------
# NATIVE effects: real handlers added to the engine this pass.
#   gen2_effect -> dict(const, ptr, category, asm)
#     const    : new EFFECT_GEN2_* constant (appended after DISABLE_EFFECT)
#     ptr       : its MoveEffectPointerTable label (== handler label)
#     category  : "residual1" (status move, skips damage/accuracy) | None
#     asm       : the handler routine, assembled into the Battle Core bank
# ---------------------------------------------------------------------------
NATIVE_EFFECTS = {
    # --- on-hit self stat boosts: damaging moves, effect runs AFTER damage
    #     (category None => not in any effect-category array). A SINGLE call to
    #     the engine's StatModifierUpEffect is safe; multiple calls would
    #     re-apply burn/paralysis penalties each time, so multi-stat moves
    #     (AncientPower-all, Curse) are intentionally left as fallback.
    "EFFECT_ATTACK_UP_HIT": dict(
        const="EFFECT_GEN2_ATTACK_UP_HIT", ptr="Gen2AttackUpHitEffect", category=None,
        asm="""Gen2AttackUpHitEffect:
; Metal Claw: after the hit lands, raise the user's Attack one stage by
; reusing StatModifierUpEffect with a temporarily-swapped move effect.
	ldh a, [hWhoseTurn]
	and a
	ld hl, wPlayerMoveEffect
	jr z, .got
	ld hl, wEnemyMoveEffect
.got
	ld a, [hl]
	push af
	push hl
	ld [hl], ATTACK_UP1_EFFECT
	call StatModifierUpEffect
	pop hl
	pop af
	ld [hl], a
	ret
"""),
    "EFFECT_DEFENSE_UP_HIT": dict(
        const="EFFECT_GEN2_DEFENSE_UP_HIT", ptr="Gen2DefenseUpHitEffect", category=None,
        asm="""Gen2DefenseUpHitEffect:
; Steel Wing: after the hit lands, raise the user's Defense one stage.
	ldh a, [hWhoseTurn]
	and a
	ld hl, wPlayerMoveEffect
	jr z, .got
	ld hl, wEnemyMoveEffect
.got
	ld a, [hl]
	push af
	push hl
	ld [hl], DEFENSE_UP1_EFFECT
	call StatModifierUpEffect
	pop hl
	pop af
	ld [hl], a
	ret
"""),
    "EFFECT_HEAL_BELL": dict(
        const="EFFECT_GEN2_HEAL_BELL", ptr="Gen2HealBellEffect", category="residual1",
        asm="""Gen2HealBellEffect:
; Heal Bell / Aromatherapy: cure the status of the user's whole party
; (and the active battle mon). hWhoseTurn selects which side's party.
	call PlayCurrentMoveAnimation
	ldh a, [hWhoseTurn]
	and a
	jr nz, .enemy
	xor a
	ld [wBattleMonStatus], a
	ld hl, wPartyMon1Status
	ld de, wPartyMon2 - wPartyMon1
	ld a, [wPartyCount]
	jr .clearParty
.enemy
	xor a
	ld [wEnemyMonStatus], a
	ld hl, wEnemyMon1Status
	ld de, wEnemyMon2 - wEnemyMon1
	ld a, [wEnemyPartyCount]
.clearParty
	and a
	ret z
	ld b, a
.loop
	ld [hl], 0
	add hl, de
	dec b
	jr nz, .loop
	ret
"""),
    "EFFECT_PAIN_SPLIT": dict(
        const="EFFECT_GEN2_PAIN_SPLIT", ptr="Gen2PainSplitEffect", category="residual1",
        asm="""Gen2PainSplitEffect:
; Pain Split: set both the user's and target's current HP to the average of the
; two (each capped at its own max HP). HP is a big-endian 2-byte field. Only the
; in-battle HP copies are touched; the engine writes wBattleMonHP back to the
; party on switch-out, so no manual party-copy sync is needed.
	call PlayCurrentMoveAnimation
	ld hl, wBattleMonHP
	ld a, [hli]
	ld b, a
	ld a, [hl]
	ld c, a              ; bc = player HP
	ld hl, wEnemyMonHP
	ld a, [hli]
	ld d, a
	ld a, [hl]
	ld e, a              ; de = enemy HP
	ld a, c
	add e
	ld c, a
	ld a, b
	adc d
	ld b, a              ; bc = sum (<= 1998, fits 16 bits)
	srl b
	rr c                 ; bc = average
	; player: store min(avg, wBattleMonMaxHP)
	ld hl, wBattleMonMaxHP
	ld a, [hli]
	ld d, a
	ld a, [hl]
	ld e, a              ; de = player max HP
	push bc
	ld a, e
	sub c
	ld a, d
	sbc b                ; carry set if maxHP < avg
	jr nc, .pStore
	ld b, d
	ld c, e              ; clamp to max
.pStore
	ld hl, wBattleMonHP
	ld a, b
	ld [hli], a
	ld a, c
	ld [hl], a
	pop bc
	; enemy: store min(avg, wEnemyMonMaxHP)
	ld hl, wEnemyMonMaxHP
	ld a, [hli]
	ld d, a
	ld a, [hl]
	ld e, a              ; de = enemy max HP
	ld a, e
	sub c
	ld a, d
	sbc b                ; carry set if maxHP < avg
	jr nc, .eStore
	ld b, d
	ld c, e
.eStore
	ld hl, wEnemyMonHP
	ld a, b
	ld [hli], a
	ld a, c
	ld [hl], a
	ret
"""),
    "EFFECT_PSYCH_UP": dict(
        const="EFFECT_GEN2_PSYCH_UP", ptr="Gen2PsychUpEffect", category="residual1",
        asm="""Gen2PsychUpEffect:
; Psych Up: copy the TARGET's stat-stage modifiers onto the USER.
	call PlayCurrentMoveAnimation
	ldh a, [hWhoseTurn]
	and a
	jr nz, .enemy
	ld hl, wEnemyMonStatMods
	ld de, wPlayerMonStatMods
	jr .copy
.enemy
	ld hl, wPlayerMonStatMods
	ld de, wEnemyMonStatMods
.copy
	ld bc, wPlayerMonStatModsEnd - wPlayerMonStatMods
.loop
	ld a, [hli]
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .loop
	ret
"""),
}

# Effects that are full-fidelity through an existing Gen1 const (TIER gen1).
# Used only for the human-readable tier report; resolve() routes them via
# simple's map automatically (which already picks these exact consts).
GEN1_EXACT = {
    "EFFECT_NORMAL_HIT", "EFFECT_FLAME_WHEEL", "EFFECT_SACRED_FIRE",
    "EFFECT_FREEZE_HIT", "EFFECT_PARALYZE_HIT", "EFFECT_SP_DEF_DOWN_HIT",
    "EFFECT_LEECH_HIT", "EFFECT_SNORE", "EFFECT_TWISTER", "EFFECT_ALWAYS_HIT",
    "EFFECT_SPEED_DOWN_2", "EFFECT_ATTACK_DOWN_2", "EFFECT_EVASION_DOWN",
    "EFFECT_CONFUSE", "EFFECT_HEAL", "EFFECT_SYNTHESIS", "EFFECT_MORNING_SUN",
    "EFFECT_MOONLIGHT",
}


def resolve(move):
    """Effect const to write into moves.asm. Native effects use their new
    EFFECT_GEN2_* const; everything else defers to simple's best-effort map
    (which is full-fidelity for the gen1-exact tier)."""
    e = move["effect"]
    if e in NATIVE_EFFECTS:
        return NATIVE_EFFECTS[e]["const"]
    return simple.resolve(move)


def tier(effect):
    if effect in NATIVE_EFFECTS:
        return "native"
    if effect in GEN1_EXACT:
        return "gen1"
    return "fallback"


def engine_edits():
    """Return the ASM fragments inject_gen2.py splices into the engine to wire
    up the native handlers. Empty lists if no native effects are defined."""
    consts = "".join(f"\tconst {d['const']}\n" for d in NATIVE_EFFECTS.values())
    pointers = "".join(f"\tdw {d['ptr']}\n" for d in NATIVE_EFFECTS.values())
    handlers = "\n".join(d["asm"] for d in NATIVE_EFFECTS.values())
    residual1 = "".join(
        f"\tdb {d['const']}\n" for d in NATIVE_EFFECTS.values()
        if d["category"] == "residual1")
    return dict(consts=consts, pointers=pointers, handlers=handlers,
                residual1=residual1)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen2_moves as gm
    tbl = gm.build_move_table(list(range(152, 252)))
    from collections import Counter
    c = Counter(tier(m["effect"]) for m in tbl)
    print(f"{len(tbl)} moves -- tiers: {dict(c)}")
    for t in ("native", "gen1", "fallback"):
        print(f"\n=== {t} ===")
        for m in tbl:
            if tier(m["effect"]) == t:
                print(f"  {m['C']:14} {m['effect']:24} -> {resolve(m)}")
