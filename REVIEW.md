# wadlib Project Review

Review date: 2026-04-16

Repository state reviewed: v0.3.4-era code after ResourceResolver phase 1,
collision-complete lookup, Strife DIALOGUE parsing, unified PK3/WAD map assembly,
structured diagnostics, parser maturity work, README release-shape docs, examples,
and the latest BLOCKMAP empty-lump fix.

## Overall Score

**8.7 / 10**

`wadlib` has moved from "promising and broad" to a serious Doom-engine WAD
library. The earlier high-priority correctness issues are gone, the resolver is
now a real resource stack instead of a thin convenience wrapper, Strife data
support is materially better, and the project now has a useful diagnostics layer.

For classic Doom-engine WAD workflows - Doom, Doom II, Final Doom-style WADs,
Heretic, Hexen, and most Strife data reading - I would rate it around
**9.0 / 10**.

For modern source-port content - GZDoom WADs, PK3s, UDMF, DECORATE, ZMAPINFO,
resource overlays, and diagnostics - I would rate it around **8.0 / 10**.

The combined score stays below 9 because several new features are good but still
semantically young: resolver collision reports confuse map-local lumps with
global resources, PK3 namespace aliases are inconsistent, Strife's DIALOGUE
support is read-only and not exposed through a clean `WadFile` convenience API,
and the new diagnostics layer is useful but not yet authoritative for PK3/ZDoom
content.

## Verification Run

All checks below were run from the project `.venv`.

```bash
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
.venv/bin/pytest tests/test_blockmap.py tests/test_resolver.py tests/test_phase2_maps.py tests/test_phase3_analysis.py tests/test_strife_conversation.py --no-cov -q
.venv/bin/pytest -m 'not slow' --no-cov -q
```

Results:

- Ruff: passed.
- Mypy: passed, no issues in 112 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining messages are
  design/complexity warnings in parser/export/FUSE modules.
- Targeted resolver/map/analysis/Strife/BLOCKMAP tests: passed.
- Non-slow test suite: passed with coverage disabled.

I did not run slow tests in this pass. I also did not collect a fresh coverage
number because the review runs used `--no-cov` to measure the fast path.

Manual probes found the current review findings below:

- A two-map WAD reports `THINGS` and `LINEDEFS` as resource collisions.
- A PK3 entry under `sfx/` exposes namespace `sfx`, and
  `iter_resources(category="sounds")` misses it.
- `wad.get_lump("DIALOGUE")` returns `BaseLump`, not `ConversationLump`.
- A BLOCKMAP with a valid header but truncated offset table still leaks
  `struct.error`.

## What Improved

### Resource Stack

- `ResourceResolver.find_all()` is now collision-complete for WAD duplicate
  lumps and PK3 8-character lump-name collisions.
- `ResourceRef` now carries useful metadata: `size`, `kind`, `namespace`, and
  `load_order_index`.
- `shadowed(name)`, `collisions()`, and `iter_resources(category=None)` are now
  public APIs.
- `doom_load_order(base, *patches)` remains the right API for normal Doom
  load-order semantics.

This addresses the largest resolver concerns from the previous review.

### Map Assembly

- `WadFile.from_bytes()` enables embedded WAD maps inside PK3 archives.
- `Pk3Archive.maps` supports both embedded WAD maps and decomposed
  `maps/MAP01/*.lmp` layouts.
- `ResourceResolver.maps()` merges maps across WAD and PK3 sources with priority
  order and origin metadata.
- `attach_map_lumps()` now works over generic `LumpSource` objects, not only WAD
  directory entries.

This is the right architecture direction. It keeps `WadFile` as the classic WAD
facade while moving cross-source behavior into the resolver/PK3 layer.

### Strife

- Strife thing counts are now consistent at 262 in README/docs.
- `DIALOGUE` / CONVERSATION data has a real parser with `ConversationPage` and
  `ConversationChoice` dataclasses.
- The parser has a focused synthetic test suite and domain errors for malformed
  lump sizes.

This is enough to say Strife support is no longer just a thing catalog.

### Diagnostics

- `analyze()` gives callers a structured `ValidationReport`.
- It checks map references, missing textures/flats, PNAMES patch indices,
  resource collisions, and compatibility level.
- Reports are JSON-serializable and work on `WadFile`, `Pk3Archive`, and
  `ResourceResolver` inputs.

This is a strong foundation for CLI and library-side validation.

### Docs And Examples

- README now documents the resolver, unified map assembly, diagnostics, stability
  levels, and example scripts.
- Release-shape docs are much clearer: stable classic WAD workflows, beta modern
  source-port workflows, explicit no-go areas like ZScript execution.

## Current Major Findings

### 1. Resolver Collision Diagnostics Misclassify Map-Local Lumps

`ResourceResolver.collisions()` currently counts every repeated lump name in the
WAD directory. That is correct for global resources like `PLAYPAL`, but wrong for
map-local lumps. A normal multi-map WAD contains repeated `THINGS`, `LINEDEFS`,
`SIDEDEFS`, `VERTEXES`, and so on. Those are not collisions; they are scoped
under different map markers.

Manual probe result:

```text
['LINEDEFS', 'THINGS'] {'THINGS': 2, 'LINEDEFS': 2}
```

This means `analyze()` can warn about harmless map sub-lumps in normal multi-map
WADs, because it delegates collision checks to `resolver.collisions()`.

Recommended fix:

1. Teach `collisions()` to ignore map sub-lumps when they are inside map groups,
   or report them with map scope instead of global scope.
2. Keep true global duplicate detection for resources outside map groups.
3. Add tests with a two-map WAD that repeats `THINGS` and `LINEDEFS` without
   producing resource collision warnings.

Priority: **high**. This is the biggest current semantic bug because it affects
the new diagnostics layer and user trust in collision reports.

### 2. PK3 Namespace Aliases Are Not Canonical In Resolver Results

`Pk3Archive` has category aliases such as `sfx` -> `sounds` and `flat` ->
`flats`, but `ResourceResolver` exposes `pk3_entry.category` directly. That
property returns the raw top-level directory, not the canonical category.

Manual probe:

```text
namespace for sfx/DSPISTOL.lmp: sfx
iter_resources(category="sounds"): []
```

This contradicts the intent of the category API: `Pk3Archive.sounds` treats
`sfx/` as sounds, while `ResourceResolver.iter_resources(category="sounds")`
does not.

Recommended fix:

1. Centralize PK3 category normalization in one public or internal helper.
2. Use the canonical category for `ResourceRef.namespace`.
3. Make `iter_resources(category=...)` accept canonical names consistently.
4. Add tests for `sound/`, `sounds/`, `sfx/`, `flat/`, `flats/`, and similar
   aliases through both `Pk3Archive` and `ResourceResolver`.

Priority: **medium-high**.

### 3. `ResourceRef` Still Lacks Canonical Origin Identity ✓ done (v0.3.6)

`ResourceRef` now carries `origin_path: str | None` (full PK3 archive path)
and `directory_index: int | None` (WAD directory position), plus an `origin`
property that formats these as a human-readable string for diagnostics.
`_iter_source` populates both fields for every ref it yields.

### 4. Strife Is Close, But The "Full" Claim Is Slightly Ahead Of The API ✓ done (v0.3.5–v0.3.6)

`wad.dialogue` property added in v0.3.5.  Serialization completed in v0.3.6:
`ConversationChoice.to_bytes()`, `ConversationPage.to_bytes()`,
`conversation_to_bytes()`, and `ConversationLump.to_bytes()`.  DIALOGUE is
now a complete read/write format.  Real-IWAD coverage remains synthetic only.

### 5. BLOCKMAP Parsing Still Has A Truncation Edge

The empty/stub BLOCKMAP case was fixed, and the mypy issue was fixed. However a
BLOCKMAP with a valid 8-byte header and an incomplete offset table still leaks a
low-level `struct.error`.

Manual probe:

```text
struct.error: unpack requires a buffer of 8 bytes
```

Recommended fix:

1. Before unpacking offsets, check that `len(raw_all) >= hdr_size + num_blocks * 2`.
2. Raise `CorruptLumpError` for a truncated offset table.
3. Add a regression test and include BLOCKMAP in fuzz coverage.

Priority: **medium**. It is small and concrete.

### 6. `analyze()` Is Useful But Still Beta ✓ partially done (v0.3.6)

Bare exception swallows replaced with explicit diagnostics:
`MAP_ASSEMBLY_FAILED`, `TEXTURE_PARSE_FAILED`, `COLLISION_CHECK_FAILED`.
`UDMF_TEXTURE_CHECK_SKIPPED` emitted once per report listing all UDMF maps.
Texture collection expanded: PK3 `textures/`/`patches/` directories and
ZDoom `TEXTURES` text lump (best-effort).  `_wad_texture_names` now resilient
to parse errors.  UDMF semantic checks and full ZDoom texture resolution
remain out of scope.

### 7. TODO.md Is Now Stale

Several TODO items are no longer accurate:

- Resource stack "remaining goals" still lists `iter_resources`,
  `shadowed`, `collisions`, full metadata, and `Pk3Archive.find_resources()` as
  not implemented.
- Unified map assembly is described as future work, but much of it landed in
  v0.3.1.
- DECORATE still says include handling is not covered, but includes and
  replacements are now implemented.
- Embedded PK3 WAD maps are still listed as open in the older PK3 section.

Recommended fix:

1. Move completed resolver/map items into a "done" subsection.
2. Keep only the remaining semantic issues: map-local collision scoping, PK3
   canonical origin/path metadata, richer diagnostics, and source-port edge
   cases.

Priority: **low-medium**.

### 8. FUSE Should Not Be Bundled Into "Stable CLI" Yet

README's stability table marks CLI as Stable and includes `wadmount` in that
row. The FUSE implementation has tests for the virtual tree and operations, but
not a real mount/unmount integration path in this review environment. It is also
OS/libfuse dependent.

Recommended fix:

1. Keep `wadcli` stable.
2. Mark `wadmount` / FUSE as Beta or Experimental unless CI runs real mount
   integration tests somewhere suitable.

Priority: **low-medium**.

## Current Backlog

High / medium-high priority:

1. ✓ Fix collision semantics for map-local lumps (v0.3.5).
2. ✓ Canonicalize PK3 category aliases in resolver namespaces (v0.3.5).
3. ✓ Finish Strife DIALOGUE integration: `wad.dialogue`, serializer (v0.3.5–v0.3.6).
4. ✓ Add PK3 path and WAD directory identity to `ResourceRef` (v0.3.6).

Medium priority:

1. ✓ Harden BLOCKMAP offset-table parsing (v0.3.5).
2. ✓ Expand `analyze()` texture collection and add explicit failure diagnostics (v0.3.6).
3. Add real-IWAD smoke coverage for Strife if fixtures are available.
4. UDMF semantic checks incrementally.

Low / maintenance priority:

1. Update TODO.md to match v0.3.x reality.
2. Reclassify FUSE separately from stable CLI unless real mount tests exist.
3. Refactor high-complexity parser/export functions when touching them for
   functional work.
4. Continue examples/docs polish for PyPI readiness.

## Recommended Order Of Operations

1. **Fix diagnostic correctness first.**
   Map sub-lumps should not appear as global resource collisions. This directly
   affects `collisions()` and `analyze()`.

2. **Normalize PK3 namespaces.**
   `sfx`, `sound`, and `sounds` need one canonical category path through both
   `Pk3Archive` and `ResourceResolver`.

3. **Complete Strife's public API story.**
   Add `wad.dialogue`, fix docs, and decide whether DIALOGUE needs serialization
   before claiming Strife Full under the README's read/write definition.

4. **Add exact-origin metadata to `ResourceRef`.**
   Diagnostics need paths and WAD entry identities, especially for collisions.

5. **Patch BLOCKMAP hardening.**
   It is a small fix with a clear regression test.

6. **Then update TODO and release docs.**
   Once the semantics are corrected, align TODO.md and the stability matrix with
   the actual v0.3.x state.

## Final Verdict

The project is now strong. Classic WAD reading/writing is near release quality,
and the modern-source-port side is no longer just partial stubs: resolver,
PK3 maps, diagnostics, UDMF, DECORATE, ZMAPINFO, and Strife DIALOGUE all have
substantial implementation and tests.

The remaining issues are mostly semantic precision and public API maturity. The
highest-risk one is collision reporting, because it can produce misleading
diagnostics on normal multi-map WADs. Fix that, canonicalize PK3 namespaces, and
tighten the Strife API/docs, and the project can credibly claim classic
Doom-engine WAD completeness while keeping PK3/GZDoom features correctly labeled
as beta.
