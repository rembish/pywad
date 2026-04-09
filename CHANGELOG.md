# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.13] - 2026-04-09

### Fixed

- Shared file-descriptor hazard: `BaseLump` now buffers its entire lump into a private `io.BytesIO` on construction instead of seeking the WAD `fd` on every read — concurrent iteration (e.g. `zip(map.things, map.vertices)`) no longer interleaves seeks and corrupts both streams
- `Reject` and `BlockMap` updated the same way: data is read from the `fd` once during `__init__`; `BlockMap._parse()` lazy-loading removed
- Added `BaseLump.raw() -> bytes` helper
- Two regression tests: `test_zip_things_vertices_gives_correct_counts` and `test_parallel_iteration_values_unchanged`

## [0.0.12] - 2026-04-09

### Changed

- `MapExporter` rewritten: draws linedefs (white = one-sided/solid, grey = two-sided/passable) and things (red outlines); Y-axis is now correctly flipped (WAD uses math coords, PIL uses screen coords); auto-scales to fit in 4096px; `save(path)` method added

## [0.0.11] - 2026-04-09

### Added

- Hexen format support: `HexenThing` (20 bytes — adds `tid`, `z`, `action`, `arg0`-`arg4`) and `HexenLineDef` (16 bytes — replaces `special_type`/`sector_tag` with `special_type` + 5 args)
- Automatic format detection in `WadFile.maps`: lumps are now grouped per map first; if a `BEHAVIOR` lump is present the Hexen parsers are used for `THINGS` and `LINEDEFS`, otherwise Doom parsers are used
- Heretic works out of the box (Doom-compatible format, no detection needed)
- `heretic_wad` and `hexen_wad` session fixtures; `minimal_hexen_wad` unit fixture
- 21 new tests covering Heretic and Hexen WADs (127 total)

## [0.0.10] - 2026-04-09

### Added

- `REJECT` lump reader — lazy-loaded bitfield; `can_see(from, to, num_sectors)` query
- `BLOCKMAP` lump reader — lazy-loaded spatial index; exposes `origin_x/y`, `columns`, `rows`, `offsets`, `block_count`
- Refactored `WadFile.maps` to use a dispatch table instead of an `if/elif` chain — adding new lump types now requires a single dict entry

## [0.0.9] - 2026-04-09

### Added

- `NODES` lump parser — `Node` (28 bytes): partition line (x/y/dx/dy), right and left bounding boxes, right and left child indices. `BBox` helper dataclass. `SSECTOR_FLAG` (0x8000) and `right_is_subsector`/`left_is_subsector` properties for BSP traversal. 9 tests.

## [0.0.8] - 2026-04-09

### Added

- `SEGS` lump parser — `Seg(start_vertex, end_vertex, angle, linedef, direction, offset)` (12 bytes)
- `SSECTORS` lump parser — `SubSector(seg_count, first_seg)` (4 bytes)

## [0.0.7] - 2026-04-09

### Added

- `SECTORS` lump parser — `Sector(floor_height, ceiling_height, floor_texture, ceiling_texture, light_level, special, tag)` (26 bytes)

## [0.0.6] - 2026-04-09

### Added

- `SIDEDEFS` lump parser — `SideDef(x_offset, y_offset, upper_texture, lower_texture, middle_texture, sector)` with automatic bytes-to-str texture name decoding

## [0.0.5] - 2026-04-09

### Added

- pytest test suite: 60 tests covering header parsing, directory entries, map detection, lump attachment, Things/Vertices/LineDefs data, `BaseLump` seek/tell, and map boundaries; 88% branch coverage

### Fixed

- `BaseLump.__next__`: off-by-one — iterator stopped at `> _size` allowing one spurious read past EOF; corrected to `>= _size`
- `Thing.__post_init__`: struct unpacking produced a raw `int` for `flags`; coerce to `Flags` enum on construction

## [0.0.4] - 2026-04-09

### Added

- Modern project scaffolding: PEP 621 `pyproject.toml`, `Makefile` (`install`/`format`/`lint`/`typecheck`/`pylint`/`test`/`check`)
- ruff 0.4+ for linting and formatting
- mypy strict — passes with zero errors across all source files
- pylint 3.2+ — 10.00/10
- Full type annotations on all source files
- `.python-version` pinned to 3.12

## [0.0.3] - 2026-04-09

### Added

- `CHANGELOG.md`

## [0.0.2] - 2026-04-09

### Fixed

- `BaseLump.seek()`: `SEEK_CUR` branch compared `_rposition + offset` against `offset` instead of `_size`, and never updated `_rposition` on the happy path — relative seeking was broken whenever `_rposition > 0`
- `BaseMapEntry.boundaries`: crashed with `IndexError`/`TypeError` when `things` or `vertices` were `None` or empty; now falls back to `(Point(0,0), Point(0,0))`
- `MapEntry.__new__`: silently returned `None` for unrecognised map name formats; now raises `ValueError`

## [0.0.1] - 2023

### Added

- WAD header parsing: magic (`IWAD`/`PWAD`), lump count, directory offset
- Directory reading: 16-byte entries (offset, size, 8-char name)
- `WadFile` context manager with lazy-loaded `directory` and `maps` properties
- Map marker detection for Doom 1 (`E#M#`) and Doom 2 (`MAP##`) formats
- `THINGS` lump parser — `Thing(x, y, direction, type, flags)` with Doom/Boom/MBF flag enum
- `VERTEXES` lump parser — `Vertex(x, y)`
- `LINEDEFS` lump parser — `LineDefinition(start_vertex, finish_vertex, flags, special_type, sector_tag, right_sidedef, left_sidedef)`
- `BaseLump` abstraction with `seek`, `tell`, `read`, `read_row`, `read_item`, `__iter__`, `__len__`, `__getitem__`
- `MapExporter` — renders map Things as ellipses onto a PIL `Image`
- `MapData` enum covering all standard map lumps: `THINGS`, `LINEDEFS`, `SIDEDEFS`, `VERTEXES`, `SEGS`, `SSECTORS`, `NODES`, `SECTORS`, `REJECT`, `BLOCKMAP`, `BEHAVIOR`
- BSD 2-Clause licence
