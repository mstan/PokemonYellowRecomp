/*
 * extras.c — Pokemon Yellow (Extended / Gen2-injected) game-specific hooks.
 *
 * The runtime (gbrt) provides a strong default for every game_* hook as its
 * own translation unit, so this partial override links cleanly. We set only
 * the launcher title; the platform stays the "gbc" default (Yellow is a Game
 * Boy Color-enhanced cart) and ROM identity is verified by the SHA-256 the
 * recompiler embeds from this exact ROM (no CRC gate — see the recomp toml).
 */
#include "game_extras.h"

/* Launcher title (defaults to "GB Recompiled" otherwise). */
const char *game_get_name(void) { return "Pok\xC3\xA9mon Yellow"; }
