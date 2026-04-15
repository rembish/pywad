# wadlib Project Review

Review date: 2026-04-15

Repository state reviewed: v0.1.9-era code after the latest hardening,
architecture, PK3, registry, and test-suite updates.

## Overall Score

**8.2 / 10**

`wadlib` is now a strong Doom WAD toolkit. It is no longer just a broad parser
with a few risky edges: it has real validation, a large test suite, typed APIs,
coverage enforcement, fuzz/property tests for several binary parsers, better
architecture seams, PK3 resource helpers, and a usable CLI.

For classic Doom / Doom II / Heretic / Hexen WAD reading, inspection, export,
and round-tripping, I would rate it around **8.6 / 10**.

For arbitrary modern source-port content (GZDoom WADs, PK3s, UDMF, DECORATE,
ZScript-adjacent syntax, source-port overlay rules), I would rate it around
**7.2 / 10**.

The combined score is held at 8.2 because the project still has a few concrete
correctness leftovers, some documentation overclaiming, and a modern-content
architecture that is improving but not fully settled.

## Verification Run

All checks below were run from the project `.venv`.

```bash
.venv/bin/pytest
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
```

Results:

- Pytest: **1037 passed, 84 skipped, 18 deselected** in **179.08s**.
- Coverage: **81.75%**, above the configured 80% gate.
- Ruff: passed.
- Mypy: passed, no issues in 110 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining findings are
  mostly design/complexity warnings in parser, renderer, FUSE, and conversion
  modules.

I did not run the slow tests. The default pytest config deselects slow tests
with `-m 'not slow'`, and that is the suite measured above.

I also ran two manual adversarial probes:

- Malformed Doom picture data with a valid column offset but a post that writes
  past the image height still raises `IndexError` instead of `CorruptLumpError`.
- `WadArchive.getinfo("DUP")` returns metadata for the first duplicate lump,
  while `WadArchive.read("DUP")` reads the last duplicate lump. The read behavior
  is now Doom-like, but the metadata behavior is still inconsistent.

## What Improved

The latest round of changes materially improved the project.

### Architecture

- `LumpSource` and `MemoryLumpSource` decouple typed lumps from WAD directory
  entries and raw file handles.
- `DirectoryEntry` now behaves like a lump source via `read_bytes()`.
- `DecoderRegistry`, `scan_map_groups`, `attach_map_lumps`, and `assemble_maps`
  moved map assembly and decoder dispatch out of `wad.py`.
- `ResourceResolver` provides a first pass at unified lookup across WAD and PK3
  sources.
- `WadFile.maps_in_order` avoids losing map ordering when callers need stable
  original order.

This is the right direction. `WadFile` is still large, but it is no longer the
only place where every concept accumulates.

### Robustness

- Header and directory hardening is much better than in the original review.
- Non-ASCII WAD magic and non-ASCII directory names now become domain errors
  instead of incidental `UnicodeDecodeError`.
- Duplicate-lump lookup in `WadFile.find_lump()` and `WadArchive.read()` now
  follows last-entry-wins behavior.
- `BaseLump.__bool__` and `BaseLump.__len__` are safer for non-row lumps.
- Several binary parsers now raise `CorruptLumpError` for short/truncated input.

### Tests

- The non-slow test suite is large and now completes in about three minutes on
  this machine.
- Coverage is above the configured 80% threshold with branch coverage enabled.
- Fuzz/property tests exist for ACS BEHAVIOR, PNAMES, TEXTURE1, MUS, and DMX
  sound parsing.
- Many earlier fragile fixture dependencies have been replaced with synthetic
  WADs where appropriate.

### PK3

- `Pk3Archive` now has category APIs for sounds, music, sprites, flats, patches,
  graphics, and textures.
- It can decode PNG/JPEG/TGA-style image resources through Pillow via
  `flat_images`, `sprite_images`, `patch_images`, and `texture_images`.
- `find_resource()` / `read_resource()` give callers a simple lump-name lookup
  across PK3 entries.

This is useful and a clear step beyond "ZIP wrapper".

## Current Major Findings

### 1. Picture Decoder Still Leaks A Low-Level Exception

`wadlib/lumps/picture.py` checks short headers, truncated column offset tables,
out-of-range column offsets, missing terminators, and truncated post data. That
is good.

One corrupt-but-plausible case remains: a post can have `topdelta + row` greater
than or equal to the image height. `_draw_column()` then writes directly to
`pixels[col_x, topdelta + row]`, which raises `IndexError`.

This matters because the public docstring promises `CorruptLumpError` for
malformed picture payloads. It is also exactly the kind of edge case fuzzing
should catch once picture fuzz tests are added.

Recommended fix:

- Before writing a pixel, check `topdelta + row < height`.
- If the post exceeds image bounds, raise `CorruptLumpError`.
- Pass `height` into `_draw_column()` or validate post bounds before the loop.
- Add a regression test with a 1x1 picture whose post starts at row 1.

Priority: **high** because it is a small, concrete correctness bug.

### 2. `WadArchive.getinfo()` And `read()` Disagree On Duplicate Lumps

`WadArchive.read()` scans the WAD directory in reverse, so the last duplicate
lump wins. That matches Doom lookup behavior and `WadFile.find_lump()`.

`WadArchive.getinfo()` still iterates `infolist()` forward and returns the first
matching duplicate. A user can therefore get size/index metadata for one lump
and bytes for another.

Recommended fix:

- Make `getinfo()` use the same precedence as `read()`.
- Or add an explicit `getinfos(name)` / `allinfo(name)` API and document
  `getinfo()` as last-wins.
- Add a regression test where the first and last duplicate have different sizes.

Priority: **high** because this is a public API consistency issue.

### 3. `ResourceResolver` Priority Order Is Easy To Misuse

`ResourceResolver` searches sources in constructor order and first hit wins.
That is documented in `resolver.py`, but it differs from the mental model of:

```python
WadFile.open(base, *pwads)
```

where later PWADs override earlier/base WADs.

This is not inherently wrong, but the example in the module docstring uses
`ResourceResolver(wad, pk3)`, which makes the base WAD win over the PK3 for
same-name resources. For a Doom-style "mod overrides base" workflow, callers
probably need to pass higher-priority sources first.

Recommended fix:

- Add a named constructor such as `ResourceResolver.load_order(base, *patches)`
  that reverses or normalizes Doom load order.
- Document examples for both "priority order" and "Doom load order".
- Consider exposing `find_all(name)` so callers can inspect shadowed resources.

Priority: **medium-high** because it is likely to cause subtle user mistakes.

### 4. PK3 Resource Semantics Are Useful But Not Source-Port Complete

`Pk3Archive` is now much better, but it is still a convenience API, not full
GZDoom resource resolution.

Known limitations:

- Category dicts are keyed by 8-character WAD-style lump names, so entries that
  collide after uppercasing/truncation silently overwrite each other.
- `find_resource()` returns the first matching lump-name entry by ZIP order.
- There is no full support for source-port filter directories, skins, language
  overlays, or source-port-specific load order rules.
- Embedded WAD-format maps such as `maps/MAP01.wad` are listed in the module
  docstring and TODO, but not integrated into the map model.

Recommended fix:

- Preserve path-level APIs as the canonical PK3 representation.
- Make lump-name dict APIs explicitly lossy, or return lists/multimaps for
  collisions.
- Add `find_resources(name)` for all matches.
- Decide whether `maps/MAP01.wad` support belongs in `Pk3Archive`,
  `ResourceResolver`, or a future map assembler over generic lump sources.

Priority: **medium**.

### 5. README Support Matrix — Revised Assessment

After closer analysis, the three "Full" labels fall into distinct categories:

**`Boom / MBF / MBF21 | Full` — label was correct, revert.**
Engine behavior (codepointers, state machines) does not affect how the binary
format is read. Generalized linedefs are a fixed bit-encoding, sector specials
are a name table, MBF21 flags are bits. All are fully decoded. "Full" is the
right label for a library — runtime engine semantics are explicitly out of scope
for all entries and need no special disclaimer here.

**`UDMF maps | Full` — Partial is justified, but for format reasons, not engine reasons.**
The regex tokenizer has two concrete gaps that affect real mods:
- Integer assignments do not parse hex literals (`0x1A`), which appear in
  GZDoom UDMF maps.
- Quoted string regex `"([^"]*)"` does not handle escaped quotes inside strings.
These are tokenizer bugs, not engine-semantics gaps. Fix: replace the regex
integer branch with a hex-aware parser and handle `\"` in quoted strings.
After the fix, "Full" is appropriate — unknown/extension fields are already
stored in `props` so namespace-specific fields are preserved correctly.

**`DECORATE | Full` — Partial is honest, but close to fixable.**
This is the one case where engine flow genuinely affects data correctness.
`DecorateActor.health` returns `None` for an actor that inherits `health = 60`
from a parent — the inherited value is invisible without walking the actor list.
The `parent` string is stored, so all data needed for resolution is present.
Adding a `resolve_inheritance(actors)` helper that fills inherited properties
into child actors would make the label "Full" without requiring a scripting engine.

Recommended fix (revised):

- Revert `Boom / MBF / MBF21` to "Full" — the original label was correct.
- Fix the UDMF tokenizer (hex integers, escaped quotes), then revert to "Full".
- Add `resolve_inheritance()` to `decorate.py`, then revert to "Full".
- Add a one-line legend to the table: "Full = complete read/write API for the
  format's data; engine runtime behavior is out of scope for all entries."

Priority: **high** — format completeness is a stated project goal.

### 6. TODO.md Has Stale Items

`TODO.md` still lists "PNG/TGA/JPG image decoding for flats, sprites, textures"
as open, but `Pk3Archive` now has Pillow-backed image APIs for those categories.

There are also items marked "done" where the implementation is useful but not
complete in the full source-port sense, especially DECORATE/ZScript and UDMF.
The nuance is present in some text, but the headings and README matrix are more
confident than the code warrants.

Recommended fix:

- Mark PK3 image decoding as done in TODO.
- Split "DECORATE metadata parser done" from "full DECORATE/ZScript engine not
  planned / future".
- Split "UDMF common block parser done" from "full grammar/semantic validation".

Priority: **medium**.

### 7. Fuzz Coverage Is Good But Still Narrow

The new Hypothesis tests are a strong improvement. They currently cover:

- ACS BEHAVIOR parser
- PNAMES
- TEXTURE1
- MUS to MIDI
- DMX sound to WAV

Important parsers still not fuzzed:

- Doom picture decode
- BLOCKMAP
- ZNODES
- UDMF text parsing
- ZMAPINFO / TEXTURES / DECORATE text parsing
- PK3 name/resource collision behavior

Recommended fix:

- Add fuzz tests for `Picture.decode()` next because there is already a proven
  low-level exception leak.
- Add size/count limits to parsers that trust file-provided counts before
  allocating format strings or lists.
- Add fuzz tests for text parsers that assert "no crash" and "no catastrophic
  regex behavior" on bounded random text.

Priority: **medium**.

### 8. `WadFile` Is Better, But Still A Broad Facade

The new registry and map assembly helpers are meaningful progress. Still,
`WadFile` remains the main facade for:

- file lifecycle
- directory access
- PWAD overlay
- resource catalogs
- map access
- typed lump construction
- cache invalidation

That is acceptable for the current project size, but the next feature wave
(deeper PK3 integration, generic resource lookup, embedded maps, source-port
filters) should avoid pushing more responsibilities back into `WadFile`.

Recommended direction:

- Keep `WadFile` as the classic WAD convenience facade.
- Move generic "resource stack" behavior into `ResourceResolver`.
- Make decoder registry constructors accept generic `LumpSource` rather than
  `DirectoryEntry` only.
- Let map assembly operate over generic ordered lump sources, so WAD directories
  and embedded/virtual PK3 map sources can share the same path.

Priority: **medium-low**, but important for keeping the project maintainable.

### 9. Pylint Complexity Warnings Are Mostly Real Design Smells

Pylint passes the threshold, but it still points at modules worth revisiting:

- `export3d.py`: nested control flow.
- `compat.py`: many branches.
- `fuse.py`: many locals and very low test coverage.
- `blockmap.py`, `texturex.py`, `decorate.py`, `mid2mus.py`, `colormap.py`:
  parser/conversion functions doing a lot in one pass.

These are not urgent failures. For parser-heavy code, some complexity is
expected. But the warnings are useful smoke signals: when a bug appears in one
of these modules, prefer extracting named parsing stages instead of adding one
more nested condition.

Priority: **low**.

## Current Low-Priority / Medium-Priority Backlog

Medium priority:

1. Fix `Picture.decode()` bounds handling and add regression plus fuzz tests.
2. Make `WadArchive.getinfo()` duplicate precedence match `read()`.
3. Clarify `ResourceResolver` source-order semantics and add a Doom-load-order
   helper or examples.
4. Correct README/TODO support claims for UDMF, DECORATE, Boom/MBF21, and PK3
   image decoding.
5. Add `Pk3Archive` collision-safe APIs (`find_resources`, path-preserving
   resource maps, or multimaps).
6. Add embedded PK3 WAD map support or explicitly document it as unsupported.
7. Expand fuzz tests to pictures, BLOCKMAP, ZNODES, UDMF, ZMAPINFO, TEXTURES,
   and DECORATE.
8. Add more direct tests for the low-coverage CLI commands that are part of the
   public tool surface.

Low priority:

1. Refactor high-complexity parser/export functions when touching them for
   functional work.
2. Reduce `fuse.py` risk if FUSE is meant to be a supported public feature;
   otherwise document it as experimental.
3. Consider lazy/larger-lump strategies. `BaseLump` still eagerly buffers every
   lump, which is simple and safe but not ideal for huge resources.
4. Add stricter semantic validation modes for maps: sidedef/sector references,
   texture references, PNAMES patch indices, and UDMF required fields.
5. Decide whether release docs should describe the project as "Beta" for all
   content or "stable for classic WAD, beta for source-port formats".

## Recommended Order Of Operations

1. **Fix the two concrete correctness bugs first.**
   Address `Picture.decode()` out-of-bounds posts and `WadArchive.getinfo()`
   duplicate precedence. These are small, testable, and user-visible.

2. **Patch documentation truthfulness next.**
   Update README and TODO so support claims match the actual implementation.
   This avoids promising full source-port semantics before they exist.

3. **Add targeted regression tests.**
   Add tests for the exact picture and duplicate-metadata cases found in this
   review. These should be fast non-slow tests.

4. **Expand fuzzing where it will catch real bugs.**
   Start with `Picture.decode()`, then BLOCKMAP and text parsers. Keep max input
   sizes bounded so the default suite stays around the current runtime.

5. **Clarify resolver/load-order APIs.**
   Decide whether `ResourceResolver` is a priority-order object, a Doom-load-order
   object, or supports both via named constructors. Document this before people
   build on it.

6. **Make PK3 APIs collision-aware.**
   Keep convenient lump-name dicts if useful, but add path-preserving or
   multi-match APIs so data loss is not silent.

7. **Only then continue larger architecture extraction.**
   Move decoder registry and map assembly toward generic `LumpSource` inputs, and
   keep `WadFile` as a facade rather than the place where every new format lands.

## Final Verdict

The project is in good shape. The last updates addressed the biggest earlier
concerns: the test suite is healthy, non-slow tests finish in a reasonable time,
coverage is above the enforced threshold, static checks pass, and the architecture
is moving away from a monolithic `WadFile`.

The remaining issues are not signs that the project is bad. They are the next
layer of maturity work: precise public semantics, conservative documentation,
collision-aware PK3 handling, parser fuzzing beyond the initial set, and a few
small correctness fixes.

My current recommendation: treat `wadlib` as **approaching release quality for
classic WAD workflows**, and still **beta for modern GZDoom/UDMF/PK3 workflows**.
