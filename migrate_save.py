#!/usr/bin/env python3
"""
Migrate a STOCK Pokemon Yellow .sav -> the EXTENDED (160-mon) save layout and
inject a party of Pikachu + the 3 Johto starters.

Why migration: the extended ROM grew wPokedexOwned/Seen 19->20 bytes each
(NUM_POKEMON 151->160), shifting everything after the dex by +2 and enlarging
the checksum range. See TECHNICAL_NOTES.md sec 3. Offsets below are from
pokeyellow.sym (this build).
"""
import sys

SRC = r"C:\Users\Matthew\Desktop\Pokemon - Yellow Version - Special Pikachu Edition (USA, Europe) (CGB+SGB Enhanced).sav"
DST = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\recomp\build\Pokemon_Yellow_Extended.sav"

# --- file offsets (bank1 = file 0x2000; addr-0xA000 + 0x2000) ---
PLAYERNAME = 0x2598                 # 11 bytes, charmap
STOCK_OWNED, STOCK_SEEN = 0x25A3, 0x25B6   # 19 bytes each (stock)
STOCK_REST = 0x25C9                 # after stock dex
STOCK_CHK  = 0x3523                 # stock checksum byte (end of stock data)
EXT_OWNED, EXT_SEEN = 0x25A3, 0x25B7       # 20 bytes each (extended)
EXT_REST   = 0x25CB
EXT_PARTY  = 0x2F2E                 # sPartyData (extended)
EXT_CHK    = 0x3525                 # sMainDataCheckSum (extended)
CHK_START  = 0x2598                 # sGameData
STOCK_PLAYERID = 0x2605            # wPlayerID in stock layout (2 bytes)

def be16(v): return bytes([(v >> 8) & 0xFF, v & 0xFF])
def be24(v): return bytes([(v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])

def name(s):  # Gen1 charmap, 11 bytes, 0x50-terminated/padded
    out = bytearray()
    for c in s:
        if 'A' <= c <= 'Z': out.append(0x80 + ord(c) - ord('A'))
        elif 'a' <= c <= 'z': out.append(0xA0 + ord(c) - ord('a'))
        elif '0' <= c <= '9': out.append(0xF6 + ord(c) - ord('0'))
        elif c == ' ': out.append(0x7F)
        else: out.append(0x50)
    out.append(0x50)
    while len(out) < 11: out.append(0x50)
    return bytes(out[:11])

EXP_L50 = 117360  # medium-slow exp at level 50

def mon(species, t1, t2, moves, pp, hp, atk, df, spd, spc, otid):
    s = bytearray()
    s += bytes([species])
    s += be16(hp)              # current HP (= max)
    s += bytes([50])           # BoxLevel
    s += bytes([0])            # status
    s += bytes([t1, t2])       # types
    s += bytes([0])            # catch rate / held item
    m = (moves + [0, 0, 0, 0])[:4]; s += bytes(m)
    s += otid                  # OT id (2 bytes, raw from save)
    s += be24(EXP_L50)         # exp
    s += be16(0) * 5           # stat exp (HP/Atk/Def/Spd/Spc)
    s += be16(0xFFFF)          # DVs (max)
    p = (pp + [0, 0, 0, 0])[:4]; s += bytes(p)  # PP
    s += bytes([50])           # Level
    s += be16(hp) + be16(atk) + be16(df) + be16(spd) + be16(spc)  # stats
    assert len(s) == 44, len(s)
    return bytes(s)

def main():
    with open(SRC, "rb") as f: stock = f.read()
    if len(stock) != 32768:
        print(f"error: expected 32768-byte SRAM, got {len(stock)}"); sys.exit(1)

    ext = bytearray(stock)  # baseline copy (boxes in banks 2/3 untouched)

    # 1) migrate dex arrays 19->20 (+ trailing zero) and shift the rest +2
    ext[EXT_OWNED:EXT_OWNED+19] = stock[STOCK_OWNED:STOCK_OWNED+19]; ext[EXT_OWNED+19] = 0
    ext[EXT_SEEN:EXT_SEEN+19]   = stock[STOCK_SEEN:STOCK_SEEN+19];   ext[EXT_SEEN+19] = 0
    ext[EXT_REST:EXT_CHK]       = stock[STOCK_REST:STOCK_CHK]        # rest shifted +2

    # 2) build + inject party (Pikachu + Chikorita + Cyndaquil + Totodile)
    otid = bytes(stock[STOCK_PLAYERID:STOCK_PLAYERID+2])
    otname = bytes(stock[PLAYERNAME:PLAYERNAME+11])
    structs = [
        mon(0x54, 0x17,0x17, [0x54,0x2d,0x62,0x55], [30,40,30,15], 110,75,50,110,70, otid),  # Pikachu
        mon(0xBF, 0x16,0x16, [0x21,0x2d,0x4b,0x16], [35,40,25,10], 120,69,85,65,69, otid),   # Chikorita
        mon(0xC2, 0x14,0x14, [0x21,0x2b,0x34,0x62], [35,30,25,30], 114,72,63,85,80, otid),   # Cyndaquil
        mon(0xC5, 0x15,0x15, [0x0a,0x2b,0x37,0x2c], [35,30,25,25], 125,85,84,63,64, otid),   # Totodile
    ]
    nicks = [name("PIKACHU"), name("CHIKORITA"), name("CYNDAQUIL"), name("TOTODILE")]

    party = bytearray()
    party += bytes([4])                                   # count
    party += bytes([0x54,0xBF,0xC2,0xC5,0xFF,0x00,0x00])  # species list + terminator
    for i in range(6): party += structs[i] if i < 4 else bytes(44)
    for i in range(6): party += otname if i < 4 else bytes(11)
    for i in range(6): party += nicks[i] if i < 4 else bytes(11)
    assert len(party) == 404, len(party)
    ext[EXT_PARTY:EXT_PARTY+404] = party

    # 2b) Pokedex flags for the new mon. wDexMaxSeenMon isn't saved (it's at
    # $CD3D, outside the saved block) -> the game recomputes it from
    # wPokedexSeen on load, so setting SEEN bits is what makes the dex extend
    # to #160. Mark all 9 Johto-line entries SEEN, and the 3 party mon OWNED.
    def setbit(base, dexnum):
        ext[base + (dexnum - 1) // 8] |= 1 << ((dexnum - 1) % 8)
    for d in range(152, 161):        # 152..160 seen -> dex shows up to #160
        setbit(EXT_SEEN, d)
    for d in (152, 155, 158):        # Chikorita / Cyndaquil / Totodile owned
        setbit(EXT_OWNED, d)

    # 3) recompute main-data checksum (sum bytes, complement)
    chk = (~sum(ext[CHK_START:EXT_CHK])) & 0xFF
    ext[EXT_CHK] = chk

    with open(DST, "wb") as f: f.write(ext)
    print(f"wrote {DST} ({len(ext)} bytes); checksum=0x{chk:02X}")
    print(f"party @0x{EXT_PARTY:04X}: count=4 species={[hex(b) for b in ext[EXT_PARTY+1:EXT_PARTY+6]]}")

if __name__ == "__main__":
    main()
