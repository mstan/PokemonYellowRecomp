# Build dependencies (not vendored — clone alongside this repo)

This repo holds the *enhancement* (scripts, patch, docs), not the decompiled
sources or any ROM. To rebuild from scratch you need:

- **pret/pokeyellow** @ `d150f7f4f49e9dda08c52199159b30ae9b4f00e8`
  → clone to `./pokeyellow`
- **pret/pokecrystal** @ `06ec23ccee71ad25bfa0779d66270bd53f48ffce` (Gen 2 donor)
  → clone to `./pokecrystal`
- **RGBDS 1.0.1** → `./tools/rgbds/`
- **gb-recompiled** engine (mstan/gbrecompiled) → ../gb-recompiled
- A legally-obtained stock **Pokémon Yellow** ROM → `./roms/`

See README.md and TECHNICAL_NOTES.md for the build/inject/recompile flow.
