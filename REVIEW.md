# wadlib Project Review

Review date: 2026-04-16

Repository state reviewed: current v0.3.7-era tree after resolver hardening,
Strife conversation serialization, parser maturity work, real-IWAD smoke-test
work, and the latest mypy cleanup.

Important caveat: this review was made while the worktree was dirty. At the
time of review, these user-owned changes were present and not touched here:
`tests/conftest.py`, `tests/test_hexen.py`, `wadlib/lumps/sidedefs.py`, and
untracked `tests/test_iwad_smoke.py`.

## Overall Score

**8.4 / 10**

The project is substantially stronger than the earlier review. The resolver
work is no longer superficial, the old map-local collision problem is fixed,
PK3 category aliases are canonical, BLOCKMAP parsing is hardened, Strife
conversation records round-trip in synthetic tests, and parser coverage for
UDMF/TEXTURES/DEHACKED has improved.

I would not call the library "classic Doom complete" yet. Doom, Doom II,
Heretic, Hexen, and most classic WAD workflows are in good shape, but real
Strife support is still not complete at the public API level: the provided
`STRIFE1.WAD` uses `SCRIPTxx` conversation lumps, while the current high-level
API and registry only expose `DIALOGUE`.

For modern source-port content - PK3s, UDMF, ZDoom TEXTURES, DECORATE,
ZMAPINFO, compatibility diagnostics - the project is useful, but still beta.
That is the right label. The remaining gaps are semantic, not just missing
syntax.

## Verification Run

All checks below were run from the project `.venv`.

```bash
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
.venv/bin/pytest tests/test_blockmap.py tests/test_resolver.py tests/test_phase2_maps.py tests/test_phase3_analysis.py tests/test_strife_conversation.py tests/test_phase4_parsers.py --no-cov -q
.venv/bin/pytest -m 'not slow' --no-cov -q
.venv/bin/pytest tests/test_iwad_smoke.py -m slow -k 'Strife or Voices' --no-cov -q
```

Results:

- Ruff: passed.
- Mypy: passed, no issues in 112 source files.
- Pylint: exited successfully, rating **9.98 / 10**. Remaining messages are
  design/complexity warnings, mainly in parser/export/FUSE modules.
- Targeted resolver/map/analysis/Strife/parser tests: passed.
- Full non-slow suite: **failed** against the provided `wads/HEXEN.WAD` fixture:
  `tests/test_hexen.py::test_hexen_map_count`,
  `test_hexen_thing_count_is_sane`, and `test_hexen_linedef_count_is_sane`.
- Slow Strife/Voices smoke subset: **failed** for real `STRIFE1.WAD`
  assumptions around `is_iwad`, `get_map`, and global `DIALOGUE`.

Manual probes:

- Two-map WAD collision report now correctly excludes map-local `THINGS` and
  `LINEDEFS`.
- PK3 `sfx/DSPISTOL.lmp` now canonicalizes to namespace `sounds`, and
  `iter_resources(category="sounds")` finds it.
- `ResourceResolver.find_all()` includes `origin_path` for PK3 refs and
  `directory_index` for WAD refs.
- `ResourceResolver.iter_resources()` does **not** include those origin fields.
- `parse_textures()` mishandles inline patch property blocks like
  `Patch "P1", 0, 0 { FlipX }`.
- The provided `STRIFE1.WAD` contains `SCRIPT00`, `SCRIPT01`, ... conversation
  lumps. These are parseable by the current conversation parser, but are not
  exposed through a clean Strife API.

## What Is Good

### Resolver

- `find_all()` is collision-complete for duplicate WAD lumps and PK3 names that
  collide after 8-character truncation.
- `shadowed()`, `collisions()`, and `iter_resources()` are real public APIs.
- Map-local sub-lumps are no longer reported as global collisions.
- PK3 aliases such as `sfx/` and `flat/` normalize to canonical categories.
- `ResourceRef` now has exact origin identity for `find_all()` results.

This is a good architecture direction. Cross-archive behavior belongs in the
resolver, not in `WadFile`.

### Classic WAD Parsing

- Classic WAD map parsing remains broad and practical.
- Hexen-format structures are typed and covered by synthetic fixtures.
- Real commercial WAD smoke testing has started, which is the right move for a
  project claiming engine-format compatibility.

The current HEXEN failures look more like fixture/version expectation problems
than obvious parser corruption, but they still matter because the advertised
test command is red with the provided fixture.

### Strife Parser Core

- The `ConversationPage` / `ConversationChoice` model is useful.
- Synthetic parser tests are focused and cover malformed sizes.
- Serialization now round-trips synthetic conversation records.
- Real `SCRIPTxx` lumps from `STRIFE1.WAD` appear to be structurally compatible
  with the parser.

The parser core is good. The public API is the weak part.

### Diagnostics And Modern Parsers

- `analyze()` now reports explicit diagnostic failures instead of silently
  swallowing broad exceptions.
- UDMF parsing now records basic warnings.
- ZDoom `TEXTURES` preserves more unknown properties.
- DEHACKED now stores pointer blocks and BEX `[CHEATS]`.

These are meaningful maturity improvements. They should still be described as
metadata extraction, not source-port behavior emulation.

## Current Major Findings

### 1. Real Strife Support Is Still Incomplete

Priority: **high**

The library can parse Strife conversation records, but the real IWAD path is
not wired correctly. The provided `STRIFE1.WAD` has `SCRIPT00`, `SCRIPT01`,
..., not a global `DIALOGUE` lump. Current public API:

- registers only `DIALOGUE` as `ConversationLump`;
- exposes `wad.dialogue` by looking for `DIALOGUE`;
- has no `wad.strife_dialogues`, `wad.conversations`, or map-aware `SCRIPTxx`
  access;
- has slow smoke tests that currently expect unavailable/stale APIs.

This blocks any "classic Doom complete" claim. The right fix is not to rename
the parser; it is to support both names/shapes:

- `DIALOGUE` / `CONVERSATION` for loose lumps and source-port material;
- `SCRIPTxx` for real Strife IWAD conversation pages;
- a public API that returns a mapping like `{ "SCRIPT00": ConversationLump }`
  or `{ map_name: ConversationLump }`, depending on how the project wants to
  model Strife.

### 2. Full Non-Slow Suite Is Red With Provided HEXEN.WAD

Priority: **high until classified**

`.venv/bin/pytest -m 'not slow' --no-cov -q` currently fails:

- expected 31 maps, observed 32;
- expected MAP01 things 350, observed 346;
- expected MAP01 linedefs 1770, observed 1769.

The local fixture SHA1 observed during review:
`ac129c4331bf26f0f080c4a56aaa40d64969c98a`.

This may be stale test data for a different Hexen release rather than a parser
bug. Still, the practical outcome is the same: the default non-slow suite is
not a reliable green signal when commercial WAD fixtures are present.

Fix direction:

- either mark commercial-WAD checks as `slow`;
- or make them tolerate known version differences;
- or assert against the actual fixture hash/version before checking exact
  counts.

### 3. `TEXTURES` Inline Patch Blocks Are Parsed Incorrectly

Priority: **high**

`parse_textures()` supports multi-line patch property blocks, but not inline
blocks:

```text
Patch "P1", 0, 0 { FlipX }
```

The module docstring shows this syntax, but a manual probe produced the wrong
result: `FlipX` was not set, the next patch was dropped, and the following
texture definition was consumed into the first texture.

This is a real parser correctness bug, not just missing coverage. It can
silently corrupt metadata extraction for common ZDoom `TEXTURES` files.

Fix direction:

- parse `{ ... }` content already present on the patch line before consuming
  later lines;
- detect an inline closing brace;
- add regression tests for one-line patch props and mixed inline/multi-line
  definitions.

### 4. `iter_resources()` Drops Origin Metadata

Priority: **medium**

`ResourceRef.origin_path`, `directory_index`, and `origin` are populated by
`find_all()`, but not by `iter_resources()`.

Observed:

- `find_all("DSPISTOL")[0].origin == "sfx/DSPISTOL.lmp"`;
- `next(iter_resources(category="sounds")).origin == ""`;
- WAD refs yielded by `iter_resources()` also have `directory_index is None`.

That weakens diagnostics and CLI output exactly where iteration is likely to be
used. This is probably a small implementation fix: reuse `_iter_source()` for
the winning ref or mirror the origin-population logic inside `iter_resources()`.

### 5. Slow Smoke Tests Need API Reality Cleanup

Priority: **medium**

`tests/test_iwad_smoke.py` is the right idea, but it currently assumes APIs
that do not exist on `WadFile`:

- `is_iwad`;
- `get_map`.

The same file also assumes global Strife `DIALOGUE`, which does not match the
provided real IWAD. Fixing the tests is part of fixing the claim. Smoke tests
should document actual public API, not desired future API.

### 6. `analyze()` Is Useful But Still Beta

Priority: **medium**

The diagnostics layer is much better than before, but it is still not an
authoritative source-port validator:

- UDMF texture/flat validation is still skipped with a warning.
- UDMF checks are structural and basic, not namespace-specific semantic checks.
- ZDoom texture resolution is best-effort metadata extraction.
- DECORATE/ZScript runtime behavior remains out of scope, correctly.

This is fine if documented as beta. It would be a problem only if marketed as
full GZDoom validation.

## Lower-Priority Backlog

- ANIMDEFS is parsed, but not connected to texture/flat lookup or compositing.
- DMX format-0 PC speaker sound is still missing.
- High-complexity parser functions should be refactored opportunistically, not
  as a standalone churn project.
- Packaging/PyPI/versioned docs remain a release-readiness task.
- Real-WAD smoke coverage should be split cleanly between default quick tests
  and opt-in licensed/slow tests.

## Recommended Order Of Operations

1. Get the default non-slow suite green again. Classify the HEXEN failures as
   fixture-version mismatch or parser regression, then make the tests reflect
   that decision.
2. Fix real Strife conversation integration: support `SCRIPTxx`, update the
   public API, and make the slow Strife smoke tests pass against
   `STRIFE1.WAD`.
3. Fix the `TEXTURES` inline patch block parser bug and add regression tests.
4. Populate `ResourceRef` origin metadata consistently from `iter_resources()`.
5. Re-run `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/pylint`, targeted
   parser/resolver tests, the non-slow suite, and the opt-in slow Strife smoke
   subset.
6. Only after that, continue with UDMF semantic checks, ANIMDEFS integration,
   and packaging polish.

## Final Verdict

The addressed review items are mostly genuinely addressed. The resolver is much
better, the API is more honest, and the parser surface has matured. However,
the current tree still has enough red flags that I would not raise the score
above 8.4 yet.

The biggest strategic issue is Strife. With the provided real IWADs, it is now
clear that synthetic `DIALOGUE` support is not enough. Finish `SCRIPTxx`
conversation support and get the smoke tests green, then the library can make a
much stronger "classic Doom-family complete" claim.
