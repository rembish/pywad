# wadlib Project Review

Review date: 2026-04-16

Repository state reviewed: current v0.3.7-era tree after the latest resolver,
Strife, TEXTURES, Hexen smoke-test, and mypy cleanup work.

## Overall Score

**8.8 / 10**

This is now in a much better place. The previous high-priority review findings
are addressed, and the important part is that they are addressed in code, tests,
and real fixture coverage rather than only in documentation.

The score is slightly below 9 after a stricter architecture pass. The behavioral
test suite is green, but there are still API-flow inconsistencies and a few
places where similar concepts are modeled through different paths.

For classic Doom-family WAD reading - Doom, Doom II, Final Doom, Heretic, Hexen,
and Strife - the library can now credibly claim practical classic coverage. The
provided commercial IWAD smoke tests pass, including Strife conversation data
stored as `SCRIPTxx` lumps.

For modern source-port content - PK3, UDMF, DECORATE, ZMAPINFO, ZDoom
`TEXTURES`, diagnostics, and compatibility analysis - the project is useful and
well beyond toy support, but it should still be called beta. The missing parts
are mostly semantic validation and source-port behavior, not basic parsing.

## Verification Run

All checks below were run from the project `.venv`.

```bash
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
.venv/bin/pytest tests/test_blockmap.py tests/test_resolver.py tests/test_phase2_maps.py tests/test_phase3_analysis.py tests/test_strife_conversation.py tests/test_phase4_parsers.py tests/test_texturex.py tests/test_hexen.py --no-cov -q
.venv/bin/pytest -m 'not slow' --no-cov -q
.venv/bin/pytest -m slow --no-cov -q
.venv/bin/pytest -m 'not slow' -q
```

Results:

- Ruff: passed.
- Mypy: passed, no issues in 112 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining messages are
  complexity/design warnings, mostly in parser/export/FUSE modules.
- Targeted resolver/map/analysis/Strife/TEXTURES/Hexen regression tests: passed.
- Full non-slow suite: passed.
- Full slow suite: passed against the local WAD fixtures.
- Non-slow coverage run: passed, **85.73%** total coverage with branch coverage
  enabled. Coverage gate is 80%.
- Manual architecture probe: `WadArchive.read()` resolves duplicate lumps
  differently in read mode and append mode (details below).

The test suite is large: current inventory contains roughly **1,685 test
functions** across unit, property/fuzz, CLI, real-WAD smoke, and functional
round-trip tests.

## What Improved

### Resolver

- `collisions()` no longer misreports normal map-local lumps as global resource
  collisions.
- PK3 category aliases are canonical (`sfx/` -> `sounds`, `flat/` -> `flats`,
  etc.).
- `find_all()` is collision-complete for WAD duplicates and PK3 8-character
  lump-name collisions.
- `ResourceRef` origin identity is now consistent across `find_all()` and
  `iter_resources()`: WAD refs carry `directory_index`, PK3 refs carry
  `origin_path`.
- The resolver now looks like a real resource stack API, not a convenience
  wrapper around `find_lump`.

### Strife

- Retail Strife conversation data is now handled correctly as `SCRIPTxx` lumps.
- `wad.dialogue` falls back to `SCRIPT00` after checking `DIALOGUE` /
  `CONVERSATION`.
- `wad.strife_scripts` exposes all conversation lumps as a sorted mapping.
- Synthetic parser round-trips pass.
- Slow real-IWAD smoke tests pass against the provided `STRIFE1.WAD` and
  `VOICES.WAD` fixtures.

This was the last major blocker for a "classic Doom-family complete" claim.
The wording should still be precise: complete for file-format reading and
metadata extraction, not complete game-engine behavior emulation.

### TEXTURES

- The inline patch block bug is fixed:

```text
Patch "P1", 0, 0 { FlipX }
```

- Regression tests now cover inline flags, rotation, alpha, mixed properties,
  and the important "do not consume the next patch/texture" cases.

This removes a real silent metadata-corruption issue in the ZDoom `TEXTURES`
parser.

### Hexen / Real-WAD Smoke

- The previous HEXEN count failures are gone.
- Tests now match the provided retail `HEXEN.WAD` fixture expectations.
- The full slow suite gives much better confidence than synthetic-only tests.

### TODO / Release Notes

- The stale Strife real-IWAD TODO has been updated to reflect current
  `SCRIPTxx` support and slow smoke coverage.

### Testing

- Core non-slow coverage is healthy at 85.73%.
- The suite includes property-based parser fuzzing via Hypothesis.
- Licensed IWAD smoke tests are gated behind `pytest -m slow` and pass locally.
- Freely redistributable WAD smoke tests cover CI-friendly real assets.
- The remaining test gaps are narrow seam tests and CLI/functional workflows,
  not a broad unit-test shortage.

## Current Findings

### 1. Duplicate-Lump Resolution Breaks Between Read And Append Mode

Priority: **medium-high**

This is the clearest architecture/API flow bug found in this pass.

`WadArchive.getinfo()` documents last-entry-wins semantics, and read mode
implements that by scanning the WAD directory in reverse. Append mode, however,
stores data in `WadWriter` and delegates `read()` to `WadWriter.get_lump()`,
whose default `occurrence=0` returns the first matching entry.

Manual probe:

- create a WAD with `DUP = b"first"` followed by `DUP = b"second"`;
- open with `WadArchive(path, "r")`: `read("DUP") == b"second"`;
- open with `WadArchive(path, "a")`: `read("DUP") == b"first"`.

That means the same public API changes semantics depending on mode. It should
be fixed before release because duplicate lump handling is central to Doom WAD
behavior.

Fix direction:

- make `WadWriter.get_lump()` / `find_lump()` support last-wins lookup, or add
  explicit `last=True` behavior;
- make `WadArchive.read()` use the same duplicate semantics in every mode;
- add a regression test covering duplicate reads in `"r"` and `"a"` modes.

### 2. Source-Port Semantics Are Still Beta

Priority: **medium**

The library parses a large amount of modern material, but it is not a GZDoom
semantic validator:

- UDMF validation is still basic and not namespace-specific.
- `analyze()` still skips deeper UDMF texture/flat validation.
- DECORATE support extracts metadata and inheritance, but does not evaluate the
  full language or runtime actor behavior.
- ZScript and ACS execution remain intentionally out of scope.

This is reasonable. Keep the docs explicit: modern source-port support is
metadata extraction plus best-effort diagnostics.

### 3. Decode Flows Are Split Across Several APIs

Priority: **medium**

The project now has good building blocks, but typed decoding is not centralized:

- `WadFile` convenience properties manually construct typed lumps.
- `WadFile.get_lump()` always returns `BaseLump`, bypassing `LUMP_REGISTRY`.
- `LUMP_REGISTRY` exists, but it is not the default path for generic decoding.
- music/sound/image detection is content-sniffed directly in `WadFile`.
- PK3 category APIs return raw `bytes` / Pillow images, while WAD APIs often
  return typed lump objects.
- `ResourceResolver` returns `ResourceRef`, which is the best cross-archive
  abstraction, but many higher-level paths still bypass it.

This is not broken, but it creates "which API should I use?" friction and makes
new features easy to wire into the wrong layer.

Fix direction:

- make the registry constructor type accept the generic `LumpSource`, not just
  `DirectoryEntry`;
- add a generic decode helper that works on `ResourceRef` / `LumpSource`;
- consider `WadFile.get_lump(name, typed=True)` or a separate
  `decode_lump(name)` API rather than expanding manual properties forever;
- keep PK3 raw-byte APIs, but make the resolver path the documented typed
  cross-archive route.

### 4. Map Modeling Works, But Subclass Boundaries Are Thin

Priority: **medium-low**

`Doom1MapEntry` and `Doom2MapEntry` are real subclasses, but they only encode
name/number shape. Hexen, UDMF, ZNODES, Strife-adjacent behavior, and source-port
map details are modeled by optional attributes and dispatch flags rather than
by map-format-specific types.

That works today, but it makes consumers branch on optional attributes:

- `map.things` may be Doom-format or Hexen-format;
- `map.lines` may be Doom-format or Hexen-format;
- UDMF maps carry `map.udmf` and skip binary geometry checks;
- ZNODES replaces several geometry attributes after attachment;
- `BaseMapEntry.attach()` is a no-op, so unknown map data can be silently
  swallowed by the fallback path.

This is not urgent, because it keeps the public API simple. But if UDMF
semantics, Strife map-specific behavior, or more source-port map formats grow,
the optional-attribute model will get ragged.

Fix direction:

- introduce an explicit `map_format` / `geometry_format` field;
- consider small protocols or component objects for binary-map versus UDMF-map
  behavior;
- make unknown map-lump attachment observable, at least through diagnostics,
  instead of a silent `pass`.

### 5. `BaseLump` Subclasses Do Not All Mean The Same Thing

Priority: **low-medium**

`BaseLump` supports fixed-row binary lumps well, but many subclasses have domain
semantics that do not match the base sequence model:

- row lumps use `len(lump)` as row count;
- text lumps without `_row_format` inherit byte-count `len()`;
- `ConversationLump.__len__()` returns page count;
- `PNames.__len__()` returns name count;
- `TextureList.__len__()` returns texture count;
- `PlayPal` overrides iteration/counting around palettes.

This is normal for file-format libraries, but it should be explicit. Code that
treats all lumps as sequence-like can easily get byte counts from one subclass
and domain counts from another.

Fix direction:

- add a `byte_size` or `raw_size` property to `BaseLump`;
- document that `len()` is domain-specific for typed lumps;
- avoid using `len()` generically unless the caller knows the lump type.

### 6. `TEXTURES` Parser Is Better, But Still Hand-Rolled And Complex

Priority: **medium**

The inline-block regression is fixed, but `wadlib/lumps/texturex.py` remains a
large hand-rolled parser with Pylint complexity warnings. It is covered well
for current behavior, but it is likely to keep accumulating edge cases as more
ZDoom syntax is added.

I would not refactor it immediately. The pragmatic next step is more fixture
coverage and fuzzing around real-world `TEXTURES` lumps. Refactor once the
grammar pressure is clearer.

### 7. Real Test Gaps Are Mostly Seam And Workflow Gaps

Priority: **medium**

The project does not have a general "missing tests" problem anymore. It has a
few specific places where tests do not yet pin important flows:

- Duplicate-lump semantics in `WadArchive` append mode are not covered. Existing
  hardening tests cover `WadFile` and `WadArchive` read mode, but not `"a"` mode.
- Typed decode consistency is not covered as an end-to-end contract because
  there is no single decode path yet. Tests cover many individual properties and
  the registry, but not a unified `ResourceRef` / `LumpSource` typed decode
  workflow.
- WAD <-> PK3 conversion tests use useful synthetic fixtures, but they do not
  yet stress complex real-world cases: duplicate names, colliding truncated PK3
  names, embedded WAD maps plus decomposed maps, source-port text lumps, and
  namespace alias preservation through round trips.
- UDMF analysis tests correctly assert that deep texture validation is skipped,
  but there are no functional tests for namespace-specific UDMF semantics yet
  because that feature does not exist.
- Several CLI commands have low coverage in the non-slow coverage report
  (`complevel`, `convert`, `export_animation`, `export_obj`, `list_actors`,
  `list_language`, `list_mapinfo`, `list_scripts`, `list_sndseq`,
  `scan_textures`). This matters only if CLI release quality is a goal.
- FUSE coverage depends on local system support and should remain beta unless
  CI grows a stable FUSE environment.
- Commercial IWAD smoke tests pass locally but are not reproducible in public CI
  unless users provide licensed fixtures.

Fix direction:

- add regression tests for every architecture seam before refactoring it;
- add functional WAD/PK3 conversion tests around duplicate/collision/namespace
  cases;
- add real-source-port fixture tests for UDMF/TEXTURES once suitable
  redistributable fixtures are available;
- either raise CLI command coverage or keep lesser-used commands clearly
  secondary to the library API.

### 8. Release Claim Needs Careful Wording

Priority: **low**

"Classic Doom complete" is now defensible if it means:

- classic IWAD/PWAD file-format reading;
- map/lump/resource parsing;
- major classic game family coverage;
- real fixture smoke tests.

It should not imply:

- full renderer parity;
- complete game simulation;
- ACS/ZScript execution;
- GZDoom-compatible semantic validation.

### 9. Complexity Is Real, But Not Architectural Rot Yet

Priority: **medium-low**

There are no emergency god modules, but there are clear complexity hotspots.
The main risk is not current breakage; it is future feature work choosing the
easy path and adding more logic to already broad modules.

Current watch list:

- `wadlib/wad.py` (~606 LOC): acceptable as the public facade, but should stay
  a delegator. New parsing/resource logic should not be added here.
- `wadlib/pk3.py` (~582 LOC): the most god-module-like file. It mixes ZIP I/O,
  namespace/resource lookup, image decoding, map assembly, and writing. It is
  still manageable, but future PK3 work should split indexing/map assembly out.
- `wadlib/compat.py` (~650 LOC): branch-heavy policy logic. This is more
  rule-table complexity than god-module design, but it would benefit from more
  declarative feature/conversion registries over time.
- `wadlib/analysis.py` (~553 LOC): acceptable for now, but should split by
  diagnostic domain if UDMF/source-port analysis grows.
- `wadlib/lumps/texturex.py` (~368 LOC): the most parser-fragile hotspot.
  It is covered, but should not absorb much more grammar without a cleaner
  tokenizer/parser/emitter structure.
- `wadlib/fuse.py` and `wadlib/export3d.py`: isolated adapter/exporter
  complexity. Leave alone unless those surfaces become actively developed.

The practical rule: keep `WadFile` and `Pk3Archive` as facades/adapters, and
put new behavior into focused resolver, parser, analysis, or helper modules.

## Remaining Backlog

- UDMF namespace-specific semantic checks.
- Deeper `analyze()` checks for UDMF maps and source-port resource lookup.
- Consistent duplicate-lump resolution across `WadArchive`, `WadWriter`,
  `WadFile`, and `ResourceResolver`.
- Centralized typed decoding for `LumpSource` / `ResourceRef` flows.
- More explicit map-format modeling if UDMF/source-port map behavior grows.
- Clearer `BaseLump` conventions around raw byte size versus domain counts.
- Functional tests for WAD/PK3 conversion and CLI commands that currently have
  low coverage.
- ANIMDEFS integration with texture/flat lookup or compositing.
- DMX format-0 PC speaker sound synthesis.
- PyPI packaging and versioned docs.
- Parser/module complexity cleanup when touching those modules for functional
  work, especially `texturex.py`, `pk3.py`, `compat.py`, and future
  source-port diagnostics.

## Recommended Order Of Operations

1. Fix duplicate-lump resolution in `WadArchive` append mode and add a
   regression test comparing `"r"` and `"a"` mode behavior.
2. Add seam tests for typed decoding, WAD/PK3 conversion edge cases, and the
   lower-covered CLI commands that are intended to be release-quality.
3. Tighten README wording around "classic Doom-family complete" so it is
   accurate and not overclaiming engine behavior.
4. Add more real-world/fuzz coverage around ZDoom `TEXTURES` before refactoring
   that parser.
5. Keep new feature logic out of `WadFile` / `Pk3Archive` unless those methods
   delegate to focused modules. If the next feature touches PK3 maps/resources,
   split `pk3.py` as part of that work.
6. Start consolidating typed decode flows around `LumpSource` / `ResourceRef`
   before adding many more typed convenience properties.
7. Start UDMF semantic validation by namespace, because that is the highest
   value remaining source-port feature.
8. Connect ANIMDEFS to texture/flat lookup or compositing.
9. Prepare packaging/versioned docs once the public API wording is settled.

## Final Verdict

The review was addressed. The major correctness problems from the last pass are
gone, and the full fast and slow test suites are green in this environment.

The project is now strong enough to describe as a serious classic Doom-family
WAD library with broad modern-source-port support. The main remaining discipline
is language: call classic WAD support mature, call modern source-port semantics
beta, and avoid implying that parsing metadata is the same as emulating a source
port.
