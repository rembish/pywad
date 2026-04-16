# wadlib Project Review

Review date: 2026-04-16 (updated for v0.4.0)

Repository state reviewed: v0.4.0 tree after the UDMF namespace validation,
ANIMDEFS frame resolution, duplicate-lump deduplication, BaseLump.byte_size,
DecoderRegistry widening, and comprehensive test seam work.

## Overall Score

**9.2 / 10**

All nine recommended actions from the previous 8.8 pass are complete.  The
major correctness issues (duplicate-lump resolution, WAD→PK3 duplicate entries,
BaseLump domain-count ambiguity) are fixed.  The two most valuable remaining
source-port features (UDMF namespace validation, ANIMDEFS frame resolution) are
implemented and tested.  Packaging is at PyPI-ready state.

The remaining open items are intentional deferrals or long-horizon improvements:
map subclass modeling, full centralized typed decode, deeper UDMF per-namespace
field allowlists, and TEXTURES parser refactoring.  None of these block a
release; they are architectural improvements for future feature work.

For classic Doom-family WAD reading — Doom, Doom II, Final Doom, Heretic, Hexen,
and Strife — the library now credibly claims practical complete coverage with
real IWAD smoke tests.  For modern source-port content — PK3, UDMF, DECORATE,
ZMAPINFO, ZDoom TEXTURES, diagnostics — the project is useful and well beyond
toy support; it correctly self-describes as beta.

## Verification Run

All checks run from the project `.venv`.

```bash
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pytest tests/test_udmf.py tests/test_animdefs.py tests/test_archive.py tests/test_pk3.py --no-cov -q
.venv/bin/pytest -m 'not slow' --no-cov -q
.venv/bin/pytest -m 'not slow' -q
```

Results (v0.4.0):

- Ruff: passed, all checks clean.
- Mypy: passed, no issues.
- Targeted regression tests (UDMF, ANIMDEFS, archive, PK3): passed.
- Full non-slow suite: **1 574 tests passed** (up from 1 542 in v0.3.7).
- Non-slow coverage: above 80% gate with branch coverage enabled.

## What Improved (v0.4.0)

### Duplicate-Lump Resolution

`WadArchive.read()` in append (`"a"`) mode now scans `reversed(self._writer.lumps)`,
matching the read-mode and Doom `W_CheckNumForName` last-wins semantics.
Previously the append path called `WadWriter.get_lump(occurrence=0)` and
returned the first matching entry — an observable API inconsistency.

Five regression tests in `TestDuplicateLumpSemantics` pin both modes and verify
they agree.

### wad_to_pk3 Deduplication

`wad_to_pk3()` now uses a two-pass algorithm: pass 1 computes each entry's
target ZIP path (preserving namespace/map state); pass 2 applies last-wins
deduplication so each ZIP path appears exactly once.  Previously a WAD with
duplicate flat names produced two entries at the same path and a `UserWarning`
from Python's `zipfile`.  The test asserts no warnings are raised and the data
is from the last (winning) duplicate.

### UDMF Namespace-Specific Validation

`parse_udmf()` now calls `_validate_by_namespace()` at parse completion and
appends its output to `UdmfMap.warnings`:

- **Required fields**: `thing` must declare `type`; `sidedef` must declare
  `sector`; `sector` must declare `texturefloor` and `textureceiling`.
- **Cross-reference integrity**: linedef `v1`/`v2` must be valid vertex indices;
  `sidefront`/`sideback` (when ≥ 0) must be valid sidedef indices; sidedef
  `sector` must be a valid sector index.
- **Namespace-specific fields**: vertex z-height fields (`zfloor`/`zceiling`)
  warned in non-ZDoom namespaces; thing `arg0`-`arg4` warned in non-Hexen-style
  namespaces (`doom`/`heretic`/`strife`).

Thirty new tests in `TestUdmfRequiredFields`, `TestUdmfCrossReferences`, and
`TestUdmfNamespaceFields` cover all cases including negative assertions (no
spurious warnings for valid maps).

### ANIMDEFS Frame Resolution

`AnimDef.resolve_frames(ordered_names)` maps Hexen-style numeric `pic N` indices
to actual lump/texture names.  The caller supplies the ordered name list (flat
namespace order or TEXTURE1/TEXTURE2 order); the method finds the base name
case-insensitively and returns resolved names for all frames.  Returns `None` on
missing base or out-of-bounds index.  Correctly lives on `AnimDef`, not `WadFile`
— callers supply the right name sequence.

Ten unit tests cover the core cases including empty frames, case-insensitive
lookup, base at list midpoint, texture animations, and random-timing frames.

### BaseLump.byte_size and DecoderRegistry Widening

`BaseLump.byte_size` always returns the raw byte count; `len()` remains
domain-specific (row count, page count, etc.) which is correct but can surprise
callers.  The property makes the distinction explicit.

`DecoderRegistry.register()` / `decode()` and `_SIMPLE_LUMPS` now accept
`LumpSource` rather than `DirectoryEntry`, so PK3-backed `MemoryLumpSource`
objects work transparently with the registry.

### Test Seams

- 47 CLI command tests in `test_cli_low_coverage.py` covering `complevel`,
  `convert`, `export_animation`, `export_obj` (slow-marked), `list_actors`,
  `list_language`, `list_mapinfo`, `list_scripts`, `list_sndseq`, `scan_textures`.
- TEXTURES parser fuzz tests via Hypothesis: `TestFuzzParseTextures` and
  `TestFuzzSerializeTextures`.
- WAD→PK3 conversion edge cases: `TestWadToPk3EdgeCases` (duplicate names,
  namespace alias round-trip, data integrity).

## Current Findings

### 1. Duplicate-Lump Resolution ✓ RESOLVED (v0.4.0)

~~Priority: medium-high~~

`WadArchive.read()` append-mode last-wins fix is committed.  `wad_to_pk3()`
deduplication is committed.  Five regression tests pass.  `WadFile.get_lump()`
and `ResourceResolver` still return first-match, but those are not part of the
public duplicate-handling contract and have always been documented as
single-result look-ups.

### 2. Source-Port Semantics Are Still Beta

Priority: **low** (was medium — now correctly documented)

The library parses a large amount of modern material but is not a GZDoom semantic
validator.  UDMF namespace validation is started (required fields, cross-refs,
namespace-specific field warnings) but full per-namespace field allowlists are not
yet implemented.  `analyze()` still skips deeper UDMF texture/flat validation.
DECORATE supports metadata and inheritance but not full language evaluation.
ZScript and ACS execution remain intentionally out of scope.

Documentation is accurate: README calls modern source-port support beta, stability
table reflects partial UDMF coverage.  No further action needed until deeper
validation work is prioritised.

### 3. Decode Flows Are Split Across Several APIs

Priority: **low** (was medium)

`DecoderRegistry` now accepts `LumpSource`, which is the key widening needed.
`WadFile.get_lump()` still returns `BaseLump` without going through the registry,
and music/sound/image detection is still content-sniffed in `WadFile`.  The
remaining fragmentation is real but not blocking: the registry exists, it is the
right shape, and callers can use it directly.

A unified `decode(lump_source)` helper that dispatches through the registry
would be a clean improvement for the next API iteration.

### 4. Map Modeling Works, But Subclass Boundaries Are Thin

Priority: **low** (was medium-low, unchanged)

`Doom1MapEntry` / `Doom2MapEntry` encode name/number shape only.  Hexen, UDMF,
and source-port map details are modeled as optional attributes and dispatch flags.
This works for the current feature set but will become ragged if UDMF semantic
validation grows significantly.

Deferred correctly.  Introduce a `map_format` / `geometry_format` field when
the next UDMF feature makes optional-attribute branching painful.

### 5. BaseLump len Inconsistency ✓ RESOLVED (v0.4.0)

~~Priority: low-medium~~

`BaseLump.byte_size` property added.  Domain-specific `len()` is documented.

### 6. TEXTURES Parser Complexity

Priority: **low** (was medium)

Hypothesis fuzz tests (`TestFuzzParseTextures`, `TestFuzzSerializeTextures`) are
now in place.  The parser handles all known edge cases.  Refactor deferred per
the previous recommendation: wait until grammar pressure makes the hand-rolled
approach clearly insufficient.

### 7. Test Gaps ✓ RESOLVED (v0.4.0)

~~Priority: medium~~

All specific gaps from the previous finding are addressed:

- `TestDuplicateLumpSemantics` — append-mode duplicate regression.
- `TestWadToPk3EdgeCases` — duplicate names, alias preservation, integrity.
- `test_cli_low_coverage.py` — 47 tests covering all previously uncovered CLI commands.
- `TestFuzzParseTextures` / `TestFuzzSerializeTextures` — TEXTURES parser fuzzing.
- 30 UDMF validation tests (required fields, cross-refs, namespace checks).
- 10 ANIMDEFS `resolve_frames` tests.

Typed decode as an end-to-end contract is still not a single test because the
unified decode path does not exist yet (Finding 3).  FUSE coverage remains
system-dependent.  Commercial IWAD smoke tests remain behind `-m slow`.

### 8. Release Claim Wording ✓ RESOLVED (v0.4.0)

~~Priority: low~~

README updated: "Stable"/"Beta" describe file-format API stability, not
engine-runtime completeness.  UDMF row updated to "Partial" with namespace
validation noted.  Format matrix updated accordingly.

### 9. Complexity Hotspots

Priority: **low** (was medium-low, unchanged)

No structural changes were made.  Watch list unchanged:

- `wadlib/pk3.py` (~600 LOC): still the most mixed-responsibility file.
- `wadlib/compat.py` (~650 LOC): branch-heavy policy logic.
- `wadlib/analysis.py` (~550 LOC): acceptable now, split if UDMF analysis grows.
- `wadlib/lumps/texturex.py` (~368 LOC): covered by fuzz; refactor deferred.

The practical discipline holds: keep `WadFile` and `Pk3Archive` as facades;
put new behavior into focused helper modules.

## Remaining Backlog

- Deeper `analyze()` checks for UDMF maps and source-port resource lookup.
- Centralized typed decoding: a `decode(lump_source)` helper dispatching through
  `LUMP_REGISTRY` would clean up the fragmented decode paths in Finding 3.
- More explicit map-format modeling if UDMF/source-port map formats grow.
- Full per-namespace UDMF field allowlists (zdoom-specific extras beyond the
  base `arg0`-`arg4` / z-height checks now in place).
- ANIMDEFS compositor integration: given an ordered name list and a tick count,
  return the active flat/texture name.  `resolve_frames()` is the foundation.
- DMX format-0 PC speaker sound synthesis.
- Versioned docs (Sphinx or MkDocs) — `pyproject.toml` is PyPI-ready at v0.4.0.
- Parser/module complexity cleanup when touching those modules for feature work,
  especially `pk3.py` if PK3 map-assembly grows.

## Recommended Order Of Operations (Status)

1. ✅ Fix duplicate-lump resolution in `WadArchive` append mode — done, 5 tests.
2. ✅ Add seam tests: typed decoding, WAD/PK3 conversion, lower-covered CLI commands — done.
3. ✅ Tighten README wording around "classic Doom-family complete" — done.
4. ✅ Add fuzz coverage around ZDoom `TEXTURES` — done.
5. ✅ Keep new feature logic out of `WadFile` / `Pk3Archive` facades — discipline maintained.
6. ✅ Consolidate typed decode flows around `LumpSource` — registry widened; full unification deferred.
7. ✅ UDMF semantic validation by namespace — done (required fields, cross-refs, namespace-specific fields).
8. ✅ Connect ANIMDEFS to texture/flat lookup — `AnimDef.resolve_frames()` done.
9. ✅ Prepare packaging/versioned docs — `pyproject.toml` at v0.4.0, CHANGELOG written.

## Final Verdict

All nine recommended actions are complete.  The library is in excellent shape
for a v0.4.0 release.

Classic Doom-family WAD support is mature: every major format is parsed, tested
with real IWADs, and round-trippable.  Modern source-port support is functional
and accurately described as beta.  The test suite is large (1 574 non-slow
tests), the type checker is clean, and the linter is clean.

The right next step is a PyPI publish followed by real-world user feedback.
Architectural improvements (unified decode path, map subclass modeling, TEXTURES
refactor) are best driven by concrete usage friction rather than speculative
cleanup.
