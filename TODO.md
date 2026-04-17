# TODO / Future ideas

Remaining work after v0.4.1.  Roughly ordered by value vs effort.

---

## Parser / decoder improvements

### Full DEHACKED state machine simulation

The parser covers all block types.  Simulating the resulting actor state
machine (sprite/frame sequence reconstruction, action function resolution)
would enable richer analysis tools.

---

## Renderer improvements

### Texture-mapped walls

The floor renderer fills each BSP subsector polygon with the sector's floor
flat.  An analogous pass could fill wall segs with their upper/lower/middle
textures, making the overhead render feel more isometric.

---

## API quality

### Centralized typed decode path

`DecoderRegistry` accepts `LumpSource` as of v0.4.0, but `WadFile.get_lump()`
still returns `BaseLump` without going through the registry.  A single
`decode(lump_source)` helper dispatching through `LUMP_REGISTRY` would unify
the fragmented decode paths.

### Map subclass modeling

`Doom1MapEntry` / `Doom2MapEntry` encode name/number shape only; Hexen,
UDMF, and source-port details are optional attributes and dispatch flags.
Introduce a `map_format` / `geometry_format` discriminator when optional-
attribute branching becomes painful.

### TEXTURES parser refactor

The hand-rolled parser handles all known edge cases and is Hypothesis-fuzzed.
Refactor to a grammar-based approach if parsing pressure grows.

---

## CLI / tooling

### Synthetic fast-gate fixtures for slow CLI paths

Several CLI commands (`export obj`, IWAD smoke tests) are covered only by
real-IWAD tests behind `pytest -m slow`.  If public CI needs those branches
without proprietary data, small synthetic WAD fixtures could serve as fast-
running gates.  Low priority until the CI bottleneck is felt.

---

## Bigger ideas

### Web / interactive map viewer

A Flask/FastAPI server that serves map renders and lets you pan/zoom,
click things to see their type, hover sectors to see their properties.

### Multi-version documentation

The MkDocs site currently deploys a single version (latest master).  The
`mike` plugin would let us host v0.4.x and future v0.5.x side by side at
`rembish.github.io/wadlib/`.

### Packaging

- Multi-version docs (see above)
- Trusted Publisher (GitHub OIDC) for `make upload` without API tokens
