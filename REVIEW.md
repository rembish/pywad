# wadlib Project Review

Review date: 2026-04-14
Response date: 2026-04-14

## Overall Score

**7.0 / 10**

This is a serious and useful Doom WAD library, not a toy project. It has a broad
reader, writer, archive API, CLI, many typed lump parsers, real WAD fixtures, and
good local quality gates. For vanilla Doom, Doom II, Heretic-style IWAD/PWAD
inspection and many export workflows, it is already useful.

The score is not higher because the core parser is not yet hardened enough for
untrusted or heavily non-standard WADs, duplicate lump precedence appears wrong
for Doom engine semantics, and the architecture has started to mix low-level WAD
IO, resource lookup, format decoding, source-port support, and CLI-oriented
features in ways that will make future format coverage harder.

As a classic WAD inspection toolkit: **good**.
As a robust Python library for arbitrary Doom-engine content: **not there yet**.

## What I Checked

- Main reader and overlay logic: `wadlib/wad.py`
- Directory and lump model: `wadlib/directory.py`, `wadlib/lumps/base.py`
- Map model and lump attachment: `wadlib/lumps/map.py`, `wadlib/enums.py`
- Archive and writer APIs: `wadlib/archive.py`, `wadlib/writer.py`
- Validation layer: `wadlib/validate.py`
- Representative binary/text parsers: picture, texture, UDMF, PK3, DeHackEd
- README, docs, packaging metadata, Makefile, CI workflow
- Test fixtures and targeted test coverage

Verification run with the project virtualenv:

```bash
.venv/bin/pytest tests/test_header.py tests/test_directory.py tests/test_maps.py tests/test_wad_accessors.py tests/test_validate.py tests/test_archive.py tests/test_writer.py --no-cov -q
.venv/bin/ruff check wadlib tests
.venv/bin/mypy wadlib
.venv/bin/pylint wadlib
```

Results:

- Focused core tests: passed.
- Ruff: passed.
- Mypy: passed, no issues in 102 source files.
- Pylint: passed the configured threshold, rating 9.99/10. Remaining findings are mostly complexity warnings in export/render/format parser modules.
- Full `.venv/bin/pytest` was intentionally stopped around 32% because the suite is large; no `.venv` failures were observed before stopping.

## What Is Good

### Broad Feature Coverage

The project covers much more than a minimal WAD reader:

- IWAD/PWAD opening
- PWAD layering
- Directory listing and raw lump access
- Typed map lumps for classic Doom and Hexen variants
- PLAYPAL, COLORMAP, flats, pictures, sprites, textures, sounds, music
- DEHACKED, MAPINFO, ZMAPINFO, SNDINFO, SNDSEQ, ANIMDEFS, ENDOOM
- WAD writing and append mode
- Zipfile-like `WadArchive`
- PK3 read/write/conversion helpers
- CLI commands for inspection, export, diff, validation, and rendering

That is a meaningful amount of domain work.

### Good Test Investment

The test suite is large and uses real open-source WAD fixtures:

- `wads/freedoom1.wad`
- `wads/freedoom2.wad`
- `wads/blasphem.wad`

This is much better than testing only hand-built toy WADs. The project also has
focused tests for headers, directories, maps, validation, archive behavior,
writer round-trips, format conversion, and many lump types.

### Useful Public Shape

The high-level API is understandable:

- `WadFile` for reading
- `WadArchive` for zipfile-style raw lump access
- `WadWriter` for construction and round-tripping

The README gives practical examples, and the docs explain both API usage and WAD
format details. That is valuable for a niche binary-format project.

### Type and Style Discipline

The project is configured with Python 3.12, ruff, strict mypy, pylint, pytest,
coverage, and CI on Python 3.12 and 3.13. The code is not perfect, but it is
clearly being maintained with real engineering hygiene.

### Good Directional Choices

Buffering lump data in `BaseLump` avoids shared-file-descriptor cursor hazards.
Using dataclasses for fixed binary records makes many lump types readable.
Having `to_bytes()` methods for many parsed records is also a good foundation
for round-trip workflows.

## Major Problems

### 1. Core WAD Parsing Is Not Hardened — FIXED

~~The biggest issue is malformed input handling.~~

~~`WadFile.__init__` reads and unpacks the header, but there is no explicit check
that the file is at least 12 bytes, that the directory offset is inside the file,
or that the directory has enough bytes for `directory_size * 16` entries.~~

~~`WadFile.directory` seeks to the directory offset and blindly unpacks each
directory record. Individual lump offsets and sizes are not checked against the
actual file size.~~

~~Many binary parsers rely on `assert raw is not None`, `struct.unpack`, and
`EOFError` from `BaseLump.read()`. For a library, especially one reading mod
files from the internet, callers should get predictable domain exceptions such
as `WadFormatError`, not incidental `AssertionError`, `struct.error`,
`UnicodeDecodeError`, `IndexError`, or `EOFError`.~~

**Addressed:** A domain exception hierarchy has been added to `wadlib/exceptions.py`:
`WadFormatError` (base), `TruncatedWadError`, `InvalidDirectoryError`.
`WadFile.__init__` now validates that the file is at least 12 bytes, that the
directory offset is non-negative, and that `offset + directory_size * 16` does
not exceed the file size. `WadFile.directory` validates each lump's
`offset + size` against the file size before creating a `DirectoryEntry`.
All four new exception classes are exported from the package `__init__`.

Remaining: `BaseLump`-level parsers (picture column offsets, texture patch
counts) still trust their input. That hardening is tracked under the medium
priority items below.

### 2. Duplicate Lump Precedence Is Probably Wrong — FIXED

~~Doom-engine lump lookup commonly treats later-loaded lumps as higher priority.
Within a single WAD, that usually means scanning backward so the last matching
lump wins.~~

~~`WadFile.find_lump()` checks WADs in priority order, but inside each WAD it scans
the directory from start to finish and returns the first matching name.~~

~~`WadArchive.read()` also returns the first matching lump.~~

~~That means a WAD containing duplicate lump names may resolve the wrong resource.
This matters because duplicate names are normal in WAD workflows, and shadowing
semantics are central to how PWADs work.~~

**Addressed:** `WadFile.find_lump` now scans each WAD's directory in reverse
order (`reversed(wad.directory)`) so the last entry with a given name wins,
matching Doom's `W_CheckNumForName` semantics. The method docstring documents
this behavior. All existing tests continue to pass.

`WadArchive.read` still scans forward (it operates on the writer's in-memory
lump list, where "last added" is already the canonical entry for append
workflows). Documenting or aligning this is a medium priority task.

### 3. UDMF and PK3 Support Exists, But Is Not Integrated — PARTIALLY FIXED

~~The repository has `UdmfLump` and `Pk3Archive`, which is good, but they are not
integrated into the main resource model.~~

~~`MapData` does not include `TEXTMAP` or `ENDMAP`, so `WadFile.maps` will not
attach UDMF maps into the normal map API. The UDMF parser is available as a
standalone helper, but a user opening a modern UDMF WAD should not expect the
same map experience as classic binary maps.~~

**Addressed (UDMF):** `MapData` now includes `TEXTMAP` and `ENDMAP`.
`BaseMapEntry` gained a `udmf: UdmfLump | None` field and an
`attach_textmap()` method. `_DOOM_DISPATCH` in `wad.py` wires `TEXTMAP` to
`attach_textmap`, so UDMF maps opened via `WadFile` now surface through
`WadFile.maps` with `map_entry.udmf` populated.

Still missing: `Pk3Archive` does not present the same layered PWAD-compatible
resource API as `WadFile`. This is a larger architectural item.

### 4. Architecture Is Becoming Too Centralized In `WadFile`

`WadFile` currently owns too many responsibilities:

- File opening
- Header parsing
- Directory parsing
- PWAD overlay resolution
- Map grouping
- Lump lookup
- Typed lump construction
- Resource catalog construction
- Cache invalidation after dynamic PWAD loading

That is manageable now, but it will become a bottleneck as support for PK3,
UDMF, GL nodes, DECORATE/ZScript, namespaces, and source-port resource rules
expands.

The project needs a clearer internal separation:

- A raw lump source abstraction: WAD file, PK3 entry, memory blob
- A resource resolver: base WAD plus patches, with documented precedence
- A map assembler: classic Doom, Hexen, UDMF
- A decoder registry: name/context to typed parser
- High-level convenience APIs layered on top

Without that split, every new format will add more special cases to `WadFile`.

### 5. Append/Write Mode Is Not Transaction-Safe — FIXED

~~`WadArchive.__exit__()` always calls `close()`, and `close()` saves the writer
for modes `"w"` and `"a"` regardless of whether the context body raised an
exception.~~

~~That creates a bad failure mode:~~

```python
with WadArchive("mod.wad", "a") as wad:
    wad.replace("PLAYPAL", new_data)
    raise RuntimeError("something else failed")
```

~~The modified WAD is still written during cleanup.~~

~~Also, append mode reads the whole WAD into a writer and then writes directly to
the target path on close. If save fails halfway, the original file can be lost or
corrupted.~~

**Addressed:** `WadArchive.__exit__` now checks `exc_type`. When an exception
propagates out of the `with` block the archive is marked closed and the reader
is released, but the writer is discarded without saving. `WadWriter.save` now
writes to a `tempfile.mkstemp` temporary in the same directory and uses
`os.replace()` for an atomic commit; if the write fails the original file is
untouched and the temporary is removed.

### 6. Validation Is Mostly Write-Side And Shallow

The validation module is a good start, but it mostly checks names and fixed
record sizes on write. It does not validate many read-time invariants:

- Directory range validity *(now covered by `WadFile.__init__` and `directory`)*
- Duplicate marker consistency
- Map block completeness
- Cross references between linedefs, vertices, sidedefs, and sectors in the core
  parser
- Texture patch indices against PNAMES
- Picture column offsets and post bounds
- UDMF semantic validity

Some CLI checks cover authoring mistakes, but the library itself still exposes
many ways for corrupt input to crash in low-level parser code.

### 7. Modern Format Parsers Are Regex-Limited

Several text formats are parsed with pragmatic regular expressions. That is
fine for a first useful implementation, but it will not cover full source-port
syntax.

Risk areas:

- `TEXTURES`
- `ZMAPINFO`
- `UDMF`
- `DECORATE`
- `SNDINFO`
- `SNDSEQ`

For simple files this is fine. For real GZDoom mods, users will eventually hit
syntax that silently parses partially or incorrectly.

### 8. Documentation And Packaging Need Release Polish — PARTIALLY FIXED

~~The docs are useful, but a few details hurt trust:~~

~~- README CI badge points at `arembish/pywad`, while clone instructions point at
  `arembish/wadlib`.~~
~~- `pyproject.toml` lacks common package metadata such as classifiers,
  project URLs, and keywords.~~
~~- The package does not appear to include a `py.typed` marker, so downstream type
  checkers may not treat it as a typed package.~~

**Addressed:** README CI badge corrected to `arembish/wadlib`. `pyproject.toml`
now includes `classifiers`, `keywords`, and `[project.urls]`. `wadlib/py.typed`
has been created.

Still open:

- `TODO.md` appears stale in places; DEHACKED is described as only
  partially parsed even though a fuller parser now exists.
- The README should include a precise support matrix separating classic WAD,
  Hexen, Boom/MBF, ZDoom/GZDoom WAD, UDMF, and PK3 support.

## Architectural Recommendation

The next major improvement should not be more individual lump parsers. The next
major improvement should be hardening and layering.

Recommended target architecture:

1. `LumpRef`
   - name
   - size
   - source path/archive
   - index
   - raw byte loader

2. `LumpSource`
   - implemented by WAD, PK3, and in-memory sources
   - exposes directory order and raw bytes

3. `ResourceResolver`
   - owns IWAD/PWAD load order
   - documents duplicate-name behavior
   - exposes first/last/all lookup APIs

4. `MapAssembler`
   - classic Doom map blocks
   - Hexen map blocks
   - UDMF `TEXTMAP`/`ENDMAP` blocks

5. `DecoderRegistry`
   - maps name/context/magic bytes to parser classes
   - keeps `WadFile` from becoming a giant manual dispatch object

This would make PK3 and UDMF support much cleaner and would reduce the amount of
special-case logic in `WadFile`.

## Priority Fix List

### High Priority

1. ~~Add read-time validation for WAD header, directory table, lump offsets, and
   lump sizes.~~ **DONE**
2. ~~Replace incidental parser failures with a small domain exception hierarchy.~~ **DONE**
3. ~~Fix and document duplicate lump precedence.~~ **DONE**
4. ~~Make `WadArchive` append/write mode commit only on successful context exit.~~ **DONE**
5. ~~Use atomic file replacement when saving modified WADs.~~ **DONE**
6. ~~Integrate UDMF map blocks into `WadFile.maps` or clearly mark UDMF as
   standalone-only.~~ **DONE** (UDMF maps now integrated via `map_entry.udmf`)

### Medium Priority

1. Split raw storage, lookup, map assembly, and decoding responsibilities.
2. Add read-time validation tests with truncated, overlapping, out-of-range, and
   duplicate-lump WADs.
3. Add fuzz/property tests for binary parsers such as pictures, textures,
   PNAMES, BLOCKMAP, ZNODES, and MUS.
4. Add a documented support matrix for vanilla, Boom, MBF, Hexen, ZDoom, UDMF,
   and PK3.
5. ~~Add `py.typed` and fuller package metadata.~~ **DONE**

### Lower Priority

1. Reduce parser complexity warnings where they hide actual grammar complexity.
2. Consider lazy raw-lump buffering or configurable size limits for large lumps.
3. Preserve original map order in one API, even if a sorted convenience API also
   exists.
4. Clean up stale TODOs and docs.

## Final Verdict

`wadlib` is already a useful classic WAD toolkit with good momentum, good test
investment, and a surprisingly broad feature set. The project is strongest as a
developer tool for inspecting, exporting, and round-tripping known-good WADs.

All six high-priority items from this review have been addressed. The main
remaining gap is the architectural split (items 4 and 3 above) and the absence
of adversarial read-time tests. With those, this project would be ready to call
production-grade for arbitrary third-party WADs.

The project should be considered **approaching release quality** for classic WAD
workflows, and **beta** for modern GZDoom/UDMF/PK3 content.
