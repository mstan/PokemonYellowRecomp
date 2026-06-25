# Known Issues

Tracked issues for the extended Pokémon Yellow build. Newest first.

---

## #1 — Back sprites of back-ported Gen 2 Pokémon look blurry

**Status:** Open (deferred — acceptable workaround in place)
**Severity:** Cosmetic
**Affects:** The 9 injected Johto-line mon (Chikorita…Feraligatr) in **battle** (the
player-facing back sprite). Front sprites (party/Pokédex/status) are crisp and
unaffected.

### Symptom
In battle, a back-ported mon's back sprite is soft/blurry compared to the crisp
front sprite and to vanilla Gen 1 back sprites.

### Root cause — a *double* resolution loss
The back sprite gets degraded twice:

1. **Author-time downscale.** Gen 2 (pokecrystal) back sprites are **48×48
   (6×6 tiles)**; Gen 1 stores backs at **32×32 (4×4)**. `inject_gen2.py`
   (`to_gray4`) downscales 48→32 with LANCZOS + 4-shade quantize — already lossy.
2. **Run-time 2× upscale.** Gen 1 then *hardware-doubles* the 32×32 back at
   battle load: `engine/battle/init_battle.asm` → `LoadMonBackPic` →
   `predef ScaleSpriteByTwo` (see `engine/battle/scale_sprites.asm`, "scales both
   uncompressed sprite chunks by two in every dimension"). A 4×4 → 8×8 nearest
   upscale.

So a detailed 48×48 source becomes 32×32, then is nearest-doubled back up —
soft input, blocky output. Fronts avoid this entirely: they're a plain crop
(no resize) and aren't 2×-scaled.

### Current workaround
Use the LANCZOS 48→32 conversion (coherent and recognizable, just soft). The
front-sprite path is already correct. No engine change.

### Proposed solution — native 48×48 back sprites ("support both 32×32 and 48×48")
Port Gen 2's back-sprite handling so back-ported mon keep full detail while
vanilla mon are untouched:

1. **Conditionally skip the 2× scale.** `ScaleSpriteByTwo` is applied
   unconditionally to backs. Read the pic's stored dimension byte (the same
   `w<<4 | h` nibble pair fronts already use via `INCBIN "...pic", 0, 1`) and:
   - vanilla 4×4 backs → keep `ScaleSpriteByTwo` (→ 64×64 as today);
   - new 6×6 (48×48) backs → render at 1× (skip the scale).
   The pic decode already centers into the 7×7-tile buffer in
   `home/pics.asm` (`LoadUncompressedSpriteData`), so a 6×6 fits without a new
   buffer.
2. **Adjust the battle back-sprite placement.** The on-screen back-sprite region
   is sized/positioned for the doubled-4×4 result; verify a 48×48 (un-doubled)
   lands correctly in the bottom-left without overlapping the player HP box, and
   tweak the blit origin if needed.
3. **Author 6×6 backs.** In `inject_gen2.py`, stop downscaling backs — emit the
   Crystal 48×48 directly (still recolor to 4 shades), with a 6×6 dimension
   byte.

This is a real but bounded engine change (it touches battle layout for the back
sprite), and it's squarely the kind of "decomp-level enhancement" this project
is about. It would eliminate the blur entirely (no downscale, no re-upscale).

**Alternative (lower effort, lower ceiling):** drop in hand-pixeled Gen-1-style
32×32 back sprites for the 9 mon (community Gen2-in-Gen1 hacks have these). Crisp
and on-model, but still 32×32 detail and requires sourcing/drawing the art.

### References
- `inject_gen2.py` → `to_gray4()` (the 48→32 downscale)
- `engine/battle/init_battle.asm` `LoadMonBackPic` / `predef ScaleSpriteByTwo`
- `engine/battle/scale_sprites.asm` `ScaleSpriteByTwo`
- `home/pics.asm` `UncompressMonSprite` / `LoadUncompressedSpriteData`
- TECHNICAL_NOTES.md §2.5 (Gen 2 back-port sprite conversion)
