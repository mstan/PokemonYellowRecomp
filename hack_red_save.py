#!/usr/bin/env python3
"""
Take a STOCK Pokemon Red .sav, migrate it to the EXTENDED (251-dex) layout, and
inject the Gen2 demo party. Migration = grow wPokedexOwned/Seen 19->32 bytes
each and shift the rest of main data +26, then recompute the checksum (same
mechanism as the Yellow migrate_save.py). Party stats/types/moves are resolved
from the injected pokered via synth_red_demo_save's builders.
"""
import sys, os
sys.path.insert(0, r"F:\Projects\gbcrecomp\PokemonYellowDecomp")
import synth_red_demo_save as srd

SRC = r"E:\Downloads\Pokemon Red (U) [S][BF].sav"
DST = srd.OUT_SAV   # the extended Red exe's save path

# stock Red (151-dex) file offsets
STOCK_OWNED, STOCK_SEEN, STOCK_REST, STOCK_CHK = 0x25A3, 0x25B6, 0x25C9, 0x3523
STOCK_PLAYERID = 0x2605
# extended Red (251-dex) file offsets (== Yellow extended; verified vs pokered.sym)
EXT_OWNED, EXT_SEEN, EXT_REST = 0x25A3, 0x25C3, 0x25E3
EXT_PARTY, EXT_CHK = 0x2F46, 0x353D
PLAYERNAME = CHK_START = 0x2598


def dexnums():
    s = open(os.path.join(srd.PY, "constants/pokedex_constants.asm"), encoding="utf-8").read()
    out, n = {}, 0
    for line in s.splitlines():
        t = line.split(";")[0].strip()
        if t.startswith("const DEX_"):
            n += 1; out[t.split()[1][4:]] = n
    return out


def main():
    stock = bytearray(open(SRC, "rb").read()[:32768])
    assert (~sum(stock[CHK_START:STOCK_CHK])) & 0xFF == stock[STOCK_CHK], "stock save checksum invalid"

    ext = bytearray(stock)  # banks 0/2/3 (incl. PC boxes) carried as-is
    # migrate: owned/seen 19 -> 32 bytes (zero-pad), shift the rest of main data +26
    ext[EXT_OWNED:EXT_OWNED + 32] = bytes(32)
    ext[EXT_OWNED:EXT_OWNED + 19] = stock[STOCK_OWNED:STOCK_OWNED + 19]
    ext[EXT_SEEN:EXT_SEEN + 32] = bytes(32)
    ext[EXT_SEEN:EXT_SEEN + 19] = stock[STOCK_SEEN:STOCK_SEEN + 19]
    ext[EXT_REST:EXT_CHK] = stock[STOCK_REST:STOCK_CHK]

    # build + inject the demo party (resolved from injected pokered)
    sp, moves, types = srd.species_index(), srd.move_table(), srd.type_values()
    otid = bytes(stock[STOCK_PLAYERID:STOCK_PLAYERID + 2])
    otname = bytes(stock[PLAYERNAME:PLAYERNAME + 11])
    structs, nicks, species = [], [], []
    for const, mv, nick in srd.PARTY_DEF:
        species.append(sp[const])
        structs.append(srd.build_mon(const, mv, sp[const], moves, types, otid))
        nicks.append(srd.encode_name(nick))
    party = bytearray([len(srd.PARTY_DEF)]) + bytes((species + [0xFF] + [0] * 6)[:7])
    for i in range(6): party += structs[i] if i < len(structs) else bytes(44)
    for i in range(6): party += otname if i < len(structs) else bytes(11)
    for i in range(6): party += nicks[i] if i < len(nicks) else bytes(11)
    assert len(party) == 404
    ext[EXT_PARTY:EXT_PARTY + 404] = party

    # dex: SEEN for all injected mon (152-251) so the Pokedex extends; OWNED for the party
    dn = dexnums()
    def setbit(base, d): ext[base + (d - 1) // 8] |= 1 << ((d - 1) % 8)
    for d in range(152, 252): setbit(EXT_SEEN, d)
    for const, _, _ in srd.PARTY_DEF: setbit(EXT_OWNED, dn[const])

    ext[EXT_CHK] = (~sum(ext[CHK_START:EXT_CHK])) & 0xFF
    open(DST, "wb").write(ext)
    print(f"wrote {DST}  checksum=0x{ext[EXT_CHK]:02X}")
    print(f"OT id=0x{otid.hex()}  party @0x{EXT_PARTY:04X} count={ext[EXT_PARTY]} "
          f"species={[hex(b) for b in species]}")
    print("(migrated stock Red save -> 251-dex layout; party = Gen2 demo team)")


if __name__ == "__main__":
    main()
