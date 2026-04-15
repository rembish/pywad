# wadlib Project Review

Review date: 2026-04-15

Repository state reviewed: v0.2.4-era code after the latest hardening,
duplicate-lump fixes, UDMF/DECORATE fixes, fuzz expansion, and
`ResourceResolver` v2 work.

## Overall Score

**8.6 / 10**

`wadlib` is now a credible Doom WAD library, not just an enthusiastic parser
collection. The recent fixes addressed the previous high-priority correctness
bugs, the default non-slow tests are now reasonably quick, and the architecture
has a clearer resource-stack direction.

For classic Doom / Doom II / Heretic / Hexen WAD reading, inspection, export,
and round-tripping, I would rate it around **8.9 / 10**.

For arbitrary modern source-port content (GZDoom PK3s, UDMF, DECORATE,
source-port resource overlays, embedded maps, and compatibility diagnostics), I
would rate it around **7.6 / 10**.

The combined score is held below 9 because modern resource resolution is still
not collision-complete, `ResourceRef` metadata is still too thin for serious
diagnostics, and generic map/resource assembly over WAD plus PK3 sources is not
finished.

## Verification Run

All checks below were run from the project `.venv`.

```bash
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
.venv/bin/pytest tests/test_resolver.py --no-cov -q
.venv/bin/pytest -m 'not slow' --no-cov -q
```

Results:

- Ruff: passed.
- Mypy: passed, no issues in 110 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining messages are
  existing complexity/design warnings, not resolver failures.
- Resolver tests: **33 passed**.
- Non-slow test suite with coverage disabled: passed in about **45 seconds**.

I did not run the slow tests in this pass. I also did not collect a fresh
coverage number in this pass because the speed check intentionally used
`--no-cov`.

## What Improved

The last rounds fixed the earlier real blockers.

### Correctness

- `Picture.decode()` now handles malformed post bounds as `CorruptLumpError`
  instead of leaking `IndexError`.
- `WadArchive.getinfo()` now matches `read()` duplicate-lump precedence: the
  last duplicate wins, matching Doom-style lookup.
- The UDMF tokenizer and DECORATE inheritance work moved the source-port text
  parsers closer to honest "data-complete" behavior.
- `BaseLump.read()` and picture decoding are now better hardened against
  low-level EOF/truncation leaks.

### Resolver

- `ResourceResolver.doom_load_order(base, *patches)` removes the old load-order
  foot-gun. The constructor remains explicit priority order, while the named
  constructor matches `doom -iwad base -file p1 p2` semantics.
- `find_all(name)` and `ResourceRef` give callers a way to inspect shadowed
  resources across multiple archives.
- The resolver tests now cover empty resolvers, PK3 lookup, priority order,
  Doom load order, cross-source `find_all()`, `ResourceRef`, and real WAD plus
  PK3 cases.

### Tests

- The non-slow suite is now practical for routine local use.
- Fuzz/property coverage has expanded and now includes picture decoding too,
  which directly covers a bug class found in the earlier review.
- The important hardening regressions are now represented in tests.

### Roadmap

`TODO.md` is now much more honest about what is core-done versus what is still
future work. It correctly keeps resource-stack collision APIs, richer
`ResourceRef` metadata, generic map assembly, diagnostics, and modern
source-port parser maturity as future work.

## Current Major Findings

### 1. `find_all()` Is Not Yet Truly "All"

`ResourceResolver.find_all()` currently returns at most one hit per archive. It
delegates to `WadFile.find_lump()` for WADs and `Pk3Archive.find_resource()` for
PK3s.

That preserves normal "winner" lookup, but it does not expose every matching
resource inside a single source:

- duplicate WAD lumps with the same name collapse to the last winner;
- PK3 files that collide after uppercase/8-character lump-name truncation
  collapse to the first matching ZIP entry;
- callers cannot inspect all same-name entries inside one WAD or one PK3.

This is the main remaining resolver gap. The API name says "all", but the
current behavior is closer to "all winning per-source hits".

Recommended fix:

1. Add `WadFile.find_lumps(name)` or reuse `get_lumps(name)` at the resolver
   layer, preserving correct priority order.
2. Add `Pk3Archive.find_resources(name) -> list[Pk3Entry]`.
3. Change resolver internals so `find_all()` can yield every matching entry,
   not just each archive's winner.
4. Add tests for duplicate WAD lumps and PK3 8-character name collisions.

Priority: **medium-high**. Normal reads are fine, but diagnostics and
shadow/collision tooling need this.

### 2. `ResourceRef` Metadata Is Still Too Thin

`ResourceRef` currently exposes only:

- `name`
- `archive`
- `source`
- `read_bytes()`

That is enough for basic lookup, but not enough for the diagnostic tooling
outlined in `TODO.md`.

Useful missing fields:

- source/load-order index;
- WAD directory index or PK3 path;
- PK3 category/namespace;
- original lookup kind: WAD lump name, PK3 path, PK3 lossy lump-name lookup;
- size;
- whether the entry is the active winner, shadowed, or involved in a collision.

Recommended fix:

1. Extend `ResourceRef` while it is still new and easy to change.
2. Preserve path-level PK3 identity rather than exposing only WAD-style
   8-character names.
3. Use the metadata as the foundation for `shadowed(name)` and `collisions()`.

Priority: **medium**.

### 3. PK3 Lookup Is Still Convenience-Level, Not Source-Port Complete

The PK3 API is useful, but it is still lossy when viewed through WAD lump-name
semantics.

Current limitations:

- category dictionaries are keyed by 8-character lump names, so collisions
  silently overwrite;
- `find_resource()` returns only the first entry matching the truncated lump
  name;
- path lookup is canonical, but WAD-style lookup does not advertise its
  collision risk strongly enough;
- embedded WAD maps such as `maps/MAP01.wad` are not integrated into the common
  map model.

Recommended fix:

1. Keep path-based PK3 APIs as canonical.
2. Add multi-match/collision-aware APIs for WAD-style lookup.
3. Document lossy lump-name lookup explicitly.
4. Feed PK3 resources into the future generic map/resource assembler.

Priority: **medium**.

### 4. Generic Resource And Map Assembly Is Still The Next Architecture Step

`WadFile` is much healthier than before, but it is still the classic-WAD facade
where most convenience APIs live. The next feature wave should avoid putting
PK3/decomposed-map/embedded-map logic back into `WadFile`.

Recommended direction:

1. Keep `WadFile` as the classic WAD convenience facade.
2. Let `ResourceResolver` own cross-archive resource-stack behavior.
3. Make map assembly consume ordered `ResourceRef` / `LumpSource` objects rather
   than only WAD directory entries.
4. Support classic WAD maps, UDMF maps, decomposed PK3 maps, and embedded WAD
   maps through one map-facing API.

Priority: **medium**. This is not a bug, but it will decide whether modern PK3
support stays maintainable.

### 5. Fuzzing Is In Progress, But Should Keep Expanding

The fuzzing direction is good, and picture fuzzing now covers the previous
out-of-bounds post bug class. The next useful targets are:

- BLOCKMAP;
- ZNODES;
- UDMF text parsing;
- ZMAPINFO / MAPINFO;
- TEXTURES;
- DECORATE;
- PK3 resource-name collision behavior.

Priority: **medium** until the current fuzz work lands, then **low-medium** as
maintenance.

### 6. Public Docs Should Catch Up To Resolver v2

`TODO.md` is current enough, but README-facing documentation should explain the
resolver now that it is a meaningful public API.

Recommended docs:

- priority-order constructor example;
- `doom_load_order()` example;
- `find_all()` example;
- warning that current PK3 lump-name lookup is 8-character and collision-prone;
- short note that full collision APIs are future work.

Priority: **low-medium**. This is not blocking code correctness, but it reduces
the chance that users build on the wrong mental model.

### 7. Complexity Warnings Are Still Useful Smoke Signals

Pylint still reports complexity/design warnings in parser and export modules,
including `export3d.py`, `compat.py`, `fuse.py`, `blockmap.py`, `texturex.py`,
`decorate.py`, `mid2mus.py`, and `colormap.py`.

These are not urgent failures. Parser-heavy code often has real branching. But
when bugs appear in these modules, prefer extracting named parsing stages rather
than adding more nested conditions.

Priority: **low**.

## Current Backlog

Medium / medium-high priority:

1. Make resolver `find_all()` collision-complete within a single WAD or PK3.
2. Enrich `ResourceRef` metadata before the API hardens.
3. Add explicit `shadowed(name)` and `collisions()` APIs.
4. Add collision-safe PK3 lookup APIs such as `find_resources(name)`.
5. Document resolver v2 in README.
6. Continue fuzz work for BLOCKMAP, ZNODES, text parsers, and PK3 collisions.
7. Move map assembly toward generic resource inputs.

Low priority:

1. Refactor high-complexity parser/export functions when touching them for
   functional work.
2. Decide whether FUSE is supported or experimental; document accordingly.
3. Consider lazy/larger-lump strategies for very large resources.
4. Add stricter semantic validation modes for maps, textures, PNAMES indices,
   and UDMF required fields.
5. Expand release docs around "stable for classic WAD, beta for modern
   source-port formats".

## Recommended Order Of Operations

1. **Finish resolver collision semantics.**
   Add WAD duplicate and PK3 collision multi-match APIs, then make
   `ResourceResolver.find_all()` actually return all hits.

2. **Expand `ResourceRef` metadata.**
   Do this before external users depend on the smaller shape.

3. **Add resolver README examples.**
   Document priority order, Doom load order, `find_all()`, and the current PK3
   collision caveat.

4. **Land the current fuzz work.**
   Keep fuzz tests bounded so the normal non-slow suite stays fast.

5. **Build explicit diagnostics.**
   `shadowed(name)`, `collisions()`, and later `analyze()` should sit on top of
   the richer resolver metadata.

6. **Only then tackle generic map assembly.**
   Use the resolver/resource metadata as the substrate for WAD maps, UDMF maps,
   decomposed PK3 maps, and embedded PK3 WAD maps.

## Final Verdict

The project is in good shape. The earlier high-priority correctness findings
have been addressed, the resolver is materially better, and the non-slow suite
is now usable for normal development.

The remaining concerns are mostly the next maturity layer: collision-complete
resource resolution, richer origin metadata, public resolver documentation,
continued fuzzing, and a cleaner architecture for modern PK3/map workflows.

My current recommendation: treat `wadlib` as **near release quality for classic
WAD workflows**, and still **beta for modern GZDoom/UDMF/PK3 workflows**.
