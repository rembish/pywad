# wadlib Project Review

Review date: 2026-04-16

Repository state reviewed: current v0.3.7-era tree after the latest resolver,
Strife, TEXTURES, Hexen smoke-test, and mypy cleanup work.

## Overall Score

**9.0 / 10**

This is now in a much better place. The previous high-priority review findings
are addressed, and the important part is that they are addressed in code, tests,
and real fixture coverage rather than only in documentation.

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
```

Results:

- Ruff: passed.
- Mypy: passed, no issues in 112 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining messages are
  complexity/design warnings, mostly in parser/export/FUSE modules.
- Targeted resolver/map/analysis/Strife/TEXTURES/Hexen regression tests: passed.
- Full non-slow suite: passed.
- Full slow suite: passed against the local WAD fixtures.

I did not collect a fresh coverage number in this review pass because the runs
used `--no-cov` to measure behavior and avoid spending extra time on coverage
instrumentation.

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

## Current Findings

### 1. Source-Port Semantics Are Still Beta

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

### 2. `TEXTURES` Parser Is Better, But Still Hand-Rolled And Complex

Priority: **medium**

The inline-block regression is fixed, but `wadlib/lumps/texturex.py` remains a
large hand-rolled parser with Pylint complexity warnings. It is covered well
for current behavior, but it is likely to keep accumulating edge cases as more
ZDoom syntax is added.

I would not refactor it immediately. The pragmatic next step is more fixture
coverage and fuzzing around real-world `TEXTURES` lumps. Refactor once the
grammar pressure is clearer.

### 3. Release Claim Needs Careful Wording

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

### 4. Complexity Is Real, But Not Architectural Rot Yet

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
- ANIMDEFS integration with texture/flat lookup or compositing.
- DMX format-0 PC speaker sound synthesis.
- PyPI packaging and versioned docs.
- Parser/module complexity cleanup when touching those modules for functional
  work, especially `texturex.py`, `pk3.py`, `compat.py`, and future
  source-port diagnostics.

## Recommended Order Of Operations

1. Tighten README wording around "classic Doom-family complete" so it is
   accurate and not overclaiming engine behavior.
2. Add more real-world/fuzz coverage around ZDoom `TEXTURES` before refactoring
   that parser.
3. Keep new feature logic out of `WadFile` / `Pk3Archive` unless those methods
   delegate to focused modules. If the next feature touches PK3 maps/resources,
   split `pk3.py` as part of that work.
4. Start UDMF semantic validation by namespace, because that is the highest
   value remaining source-port feature.
5. Connect ANIMDEFS to texture/flat lookup or compositing.
6. Prepare packaging/versioned docs once the public API wording is settled.

## Final Verdict

The review was addressed. The major correctness problems from the last pass are
gone, and the full fast and slow test suites are green in this environment.

The project is now strong enough to describe as a serious classic Doom-family
WAD library with broad modern-source-port support. The main remaining discipline
is language: call classic WAD support mature, call modern source-port semantics
beta, and avoid implying that parsing metadata is the same as emulating a source
port.
