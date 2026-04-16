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

### 1. Resolver Collision Diagnostics Misclassify Map-Local Lumps ✓ done (v0.3.5)

`_MAP_SUB_LUMPS` frozenset added to `ResourceResolver`; `collisions()` now
excludes `THINGS`, `LINEDEFS`, `SIDEDEFS`, `VERTEXES`, `SECTORS`, `SEGS`,
`SSECTORS`, `NODES`, `REJECT`, `BLOCKMAP`, `ZNODES`, `BEHAVIOR`, `TEXTMAP`,
`SCRIPTS`, and `ENDMAP` from global collision reports.  Regression tests added
for a two-map WAD confirming these names no longer appear as collisions.

### 2. PK3 Namespace Aliases Are Not Canonical In Resolver Results ✓ done (v0.3.5)

`Pk3Entry.category` now normalizes raw directory names through `_CATEGORY_ALIASES`
(`sfx/` → `sounds`, `sound/` → `sounds`, `flat/` → `flats`, `mus/` → `music`,
etc.).  `ResourceRef.namespace` and `iter_resources(category=...)` both use the
canonical name.  Tests cover `sfx`, `sound`, `sounds`, `flat`, `flats` aliases.

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

### 5. BLOCKMAP Parsing Still Has A Truncation Edge ✓ done (v0.3.5)

Before unpacking offsets, `BlockMap` now checks
`len(raw_all) >= hdr_size + num_blocks * 2` and raises `CorruptLumpError`
for a truncated offset table.  Regression test added.

### 6. `analyze()` Is Useful But Still Beta ✓ partially done (v0.3.6)

Bare exception swallows replaced with explicit diagnostics:
`MAP_ASSEMBLY_FAILED`, `TEXTURE_PARSE_FAILED`, `COLLISION_CHECK_FAILED`.
`UDMF_TEXTURE_CHECK_SKIPPED` emitted once per report listing all UDMF maps.
Texture collection expanded: PK3 `textures/`/`patches/` directories and
ZDoom `TEXTURES` text lump (best-effort).  `_wad_texture_names` now resilient
to parse errors.  UDMF semantic checks and full ZDoom texture resolution
remain out of scope.

### 7. TODO.md Is Now Stale ✓ done (v0.3.6)

- Resource stack section updated to include `origin_path`, `directory_index`,
  `origin` (v0.3.6) and the outdated "Remaining" bullet removed.
- DECORATE section updated to reflect include/replacements done in v0.3.3.
- Strife DIALOGUE real-IWAD note added: no freely redistributable Strife IWAD
  exists; **Animosity** (community libre replacement) is in progress but
  unreleased.  Slow-test pattern documented for user-provided fixture.

### 8. FUSE Should Not Be Bundled Into "Stable CLI" Yet ✓ done (v0.3.5)

README stability table already splits `wadcli` (Stable) and `wadmount` (Beta,
with OS/libfuse dependency note) into separate rows.

## Current Backlog

High / medium-high priority:

1. ✓ Fix collision semantics for map-local lumps (v0.3.5).
2. ✓ Canonicalize PK3 category aliases in resolver namespaces (v0.3.5).
3. ✓ Finish Strife DIALOGUE integration: `wad.dialogue`, serializer (v0.3.5–v0.3.6).
4. ✓ Add PK3 path and WAD directory identity to `ResourceRef` (v0.3.6).

Medium priority:

1. ✓ Harden BLOCKMAP offset-table parsing (v0.3.5).
2. ✓ Expand `analyze()` texture collection and add explicit failure diagnostics (v0.3.6).
3. Real-IWAD smoke coverage for Strife — blocked: no freely redistributable
   Strife IWAD exists.  Animosity project is in progress.  Add slow test gated
   on user-supplied `wads/strife1.wad` when available.
4. UDMF semantic checks incrementally.

Low / maintenance priority:

1. ✓ Update TODO.md to match v0.3.x reality (v0.3.6).
2. ✓ Reclassify FUSE separately from stable CLI (v0.3.5).
3. Refactor high-complexity parser/export functions when touching them for
   functional work.
4. Continue examples/docs polish for PyPI readiness.

## Recommended Order Of Operations

All original high/medium-priority items are now addressed (v0.3.5–v0.3.6).
Remaining work:

1. ✓ Fix diagnostic correctness (map sub-lumps) — v0.3.5.
2. ✓ Normalize PK3 namespaces — v0.3.5.
3. ✓ Complete Strife public API (dialogue property + serialization) — v0.3.5–v0.3.6.
4. ✓ Add exact-origin metadata to `ResourceRef` — v0.3.6.
5. ✓ BLOCKMAP hardening — v0.3.5.
6. ✓ Update TODO and release docs — v0.3.6.

**Next priorities:**
- Strife real-IWAD smoke test (user-supplied fixture; blocked on Animosity).
- UDMF namespace-specific semantic validation.
- PyPI release preparation (versioned docs, final API review).

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
